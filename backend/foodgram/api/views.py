import base64
import hashlib

from drf_base64.fields import Base64ImageField
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets, exceptions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import LimitOffsetPagination

from .paginators import RecipePagination
from .filters import RecipeFilter, IngredientFilter
from .mixins import AddDeleteRecipeMixin
from .models import Ingredient, Recipe, Tag
from .permissions import IsAuthorOrReadOnly
from .serializers import (
    IngredientSerializer, RecipeListSerializer, TagSerializer,
    CustomUserSerializer, SetAvatarResponseSerializer,
    SetAvatarSerializer, RecipeSerializer, CustomUserCreateSerializer,
    CustomUserUpdateSerializer, RecipeCreateSerializer
)

CustomUser = get_user_model()


class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.AllowAny,]
    pagination_class = LimitOffsetPagination

    def get_permissions(self):
        if self.action in (
            'me', 'avatar', 'subscribe', 'subscriptions'
        ):
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        serializer = CustomUserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        response_data = {
            'email': user.email,
            'id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_subscribed': False,
            'avatar': user.avatar.url if user.avatar else None,
        }
        return Response(response_data, status=status.HTTP_201_CREATED)

    @action(
        detail=False, methods=['get', 'put', 'patch'],
        url_path='me',
    )
    def me(self, request):
        if request.method == 'GET':
            serializer = self.get_serializer(request.user)
            return Response(serializer.data)
        serializer = CustomUserUpdateSerializer(
            request.user,
            data=request.data,
            partial=request.method == 'PATCH',
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False, methods=['put', 'delete'],
        url_path='me/avatar',
    )
    def avatar(self, request):
        user = request.user
        if request.method == 'PUT':
            serializer = SetAvatarSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            avatar_data = serializer.validated_data['avatar']
            try:
                user.avatar = Base64ImageField().to_internal_value(avatar_data)
                user.save()
            except Exception as e:
                return Response(
                    {'avatar': [str(e)]},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(
                SetAvatarResponseSerializer(
                    {'avatar': user.avatar.url}
                ).data,
                status=status.HTTP_200_OK
            )
        user.avatar.delete() if user.avatar else None
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_class = IngredientFilter
    pagination_class = None


class RecipeViewSet(AddDeleteRecipeMixin, viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeListSerializer
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly
    ]
    pagination_class = RecipePagination
    filter_backends = [
        DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter
    ]
    filterset_class = RecipeFilter
    search_fields = ['name', 'text']
    ordering_fields = ['name', 'cooking_time']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return RecipeCreateSerializer
        return RecipeListSerializer

    def create(self, request, *args, **kwargs):
        if 'image' not in request.data:
            return Response(
                {'image': ['This field is required!']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        recipe = serializer.instance
        list_serializer = RecipeListSerializer(
            recipe, context=self.get_serializer_context()
        )
        return Response(list_serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        recipe = serializer.save(author=self.request.user)
        ingredients = self.request.data.get('ingredients', [])
        for ingredient in ingredients:
            recipe.ingredients.add(
                ingredient['id'],
                through_defaults={'amount': ingredient['amount']}
            )
        tags = self.request.data.get('tags', [])
        recipe.tags.set(tags)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=kwargs.pop('partial', False)
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        recipe = serializer.instance
        list_serializer = RecipeListSerializer(
            recipe, context=self.get_serializer_context()
        )
        return Response(list_serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=True, methods=['post', 'delete'],
        permission_classes=[permissions.IsAuthenticated]
    )
    def favorite(self, request, pk=None):
        return self.add_or_remove_recipe(request, pk=pk, list_name='favorites')

    @action(
        detail=True, methods=['post', 'delete'],
        permission_classes=[permissions.IsAuthenticated]
    )
    def shopping_cart(self, request, pk=None):
        return self.add_or_remove_recipe(
            request, pk=pk, list_name='shopping_cart'
        )

    @action(
        detail=True, methods=['get'],
        permission_classes=[permissions.AllowAny],
        url_path='get_link', url_name='get-link',
    )
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        salt = settings.SECRET_KEY
        unique_str = f"{recipe.id}-{salt}"
        hash_bytes = hashlib.sha256(unique_str.encode()).digest()
        short_code = base64.urlsafe_b64encode(hash_bytes).decode()[:8]
        full_url = request.build_absolute_uri('/')[:-1]
        short_url = f"{full_url}/s/{short_code}"
        return Response({
            'short_link': short_url
        }, status=status.HTTP_200_OK)


class SubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        print(f'User in SubscriptionViewSet: {self.request.user}')
        return CustomUser.objects.filter(subscribers=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is None:
            serializer = self.get_serializer(
                page, many=True, context={'request': request}
            )
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(
            queryset, many=True, context={'request': request}
        )
        return Response(serializer.data)

    @action(
        detail=True, methods=['post', 'delete'],
        permission_classes=[permissions.IsAuthenticated]
    )
    def subscribe(self, request, pk=None):
        user_to_subscribe = get_object_or_404(CustomUser, pk=pk)
        is_subscribed = request.user.subscriptions.filter(
            author=user_to_subscribe
        ).exists()
        if request.method == 'POST':
            if request.user == user_to_subscribe:
                return Response(
                    {'detail': 'Cannot subscribe to yourself.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if is_subscribed:
                return Response(
                    {'detail': 'Already subscribed.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            request.user.subscriptions.add(user_to_subscribe)
            return Response(
                CustomUserSerializer(
                    user_to_subscribe, context={'request': request}
                ).data, status=status.HTTP_201_CREATED
            )
        if not is_subscribed:
            return Response(
                {'detail': 'Not subscribed.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        request.user.subscriptions.remove(user_to_subscribe)
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def download_shopping_cart(request):
    print(f'User in download_cart {request.user}')
    user = request.user
    ingredients = user.shopping_cart.all().values(
        'recipeingredient__ingredient__name',
        'recipeingredient__ingredient__measurement_unit'
    ).annotate(
        total_amount=Sum('recipeingredient__amount')
    ).order_by()
    shopping_list = "Shopping List:\n\n"
    for ingredient in ingredients:
        shopping_list += (
            f'- {ingredient['recipeingredient__ingredient__name']} - '
            f'{ingredient['total_amount']} '
            f'{ingredient['recipeingredient__ingredient__measurement_unit']}\n'
        )
    response = HttpResponse(shopping_list, content_type='text/plain')
    response[
        'Content-Disposition'
    ] = 'attachment; filename="shopping_list.txt"'
    return response
