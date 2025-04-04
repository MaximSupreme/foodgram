import base64
import hashlib

from drf_base64.fields import Base64ImageField
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from .filters import RecipeFilter
from .mixins import AddDeleteRecipeMixin
from .models import Ingredient, Recipe, Tag
from .permissions import IsAuthorOrReadOnly
from .serializers import (
    IngredientSerializer, RecipeListSerializer,
    TagSerializer, CustomUserCreateSerializer,
    CustomUserSerializer, SetAvatarResponseSerializer,
    SetAvatarSerializer, SetPasswordSerializer, RecipeSerializer
)

CustomUser = get_user_model()


class CustomUserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @action(
        detail=False, methods=['get'], url_path='me',
        permission_classes=[permissions.IsAuthenticated]
    )
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(
        detail=False, methods=['put', 'delete'], url_path='me/avatar',
        permission_classes=[permissions.IsAuthenticated]
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
                ).data
            )
        user.avatar.delete() if user.avatar else None
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [permissions.AllowAny]


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter]
    search_fields = ['^name']


class RecipeViewSet(AddDeleteRecipeMixin, viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeListSerializer
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly
    ]
    filter_backends = [
        DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter
    ]
    filterset_class = RecipeFilter
    search_fields = ['name', 'text']
    ordering_fields = ['name', 'cooking_time']

    def get_serializer_class(self):
        if self.action == 'create':
            return RecipeSerializer
        elif self.action == 'update' or self.action == 'partial_update':
            return RecipeSerializer
        return RecipeListSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

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
        permission_classes=[permissions.AllowAny]
    )
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        salt = settings.SECRET_KEY
        text = f'{recipe.id}{salt}'
        hashed_text = hashlib.sha256(text.encode('utf-8')).digest()
        base64_encoded = base64.urlsafe_b64encode(hashed_text).decode('utf-8')
        shortened_hash = base64_encoded[:8]
        base_url = request.build_absolute_url('/')
        short_link = f'{base_url}s/{shortened_hash}'
        return Response({'short_link': short_link})


class SubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
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
            f"- {ingredient['recipeingredient__ingredient__name']} - "
            f"{ingredient['total_amount']} "
            f"{ingredient['recipeingredient__ingredient__measurement_unit']}\n"
        )
    response = HttpResponse(shopping_list, content_type='text/plain')
    response[
        'Content-Disposition'
    ] = 'attachment; filename="shopping_list.txt"'
    return response
