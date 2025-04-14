import base64
import hashlib

from django.conf import settings
from django.db.models import Sum
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from .paginators import RecipePagination, SubscriptionPagination
from .filters import RecipeFilter, IngredientFilter
from .mixins import AddDeleteRecipeMixin
from .models import (
    Ingredient, Recipe, Tag, Subscription,
    FavoriteRecipe, ShoppingCart, RecipeIngredient
)
from .permissions import IsAuthorOrReadOnly
from .serializers import (
    IngredientSerializer, RecipeListSerializer, TagSerializer,
    CustomUserSerializer, SetAvatarResponseSerializer,
    SetAvatarSerializer, CustomUserUpdateSerializer,
    SubscriptionSerializer, RecipeSerializer
)

CustomUser = get_user_model()


class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    pagination_class = PageNumberPagination

    def get_permissions(self):
        if self.action in ('create',):
            return []
        if self.action in (
            'me', 'avatar', 'subscribe', 'subscriptions'
        ):
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == 'subscriptions':
            return SubscriptionSerializer
        return CustomUserSerializer

    @action(
        detail=False,
        methods=['GET'],
        url_path='subscriptions',
    )
    def subscriptions(self, request):
        subscriptions = Subscription.objects.filter(
            user=request.user
        ).select_related('author')
        paginator = SubscriptionPagination()
        page = paginator.paginate_queryset(subscriptions, request)
        recipes_limit = request.query_params.get('recipes_limit')
        serializer = SubscriptionSerializer(
            page,
            many=True,
            context={
                'request': request,
                'recipes_limit': recipes_limit
            }
        )
        return paginator.get_paginated_response(serializer.data)

    @action(
        detail=False, methods=['get', 'put', 'patch'],
        url_path='me',
    )
    def me(self, request):
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
            user.avatar = serializer.validated_data['avatar']
            user.save()
            return Response(
                SetAvatarResponseSerializer(
                    {'avatar': user.avatar.url}
                ).data,
                status=status.HTTP_200_OK
            )
        user.avatar.delete() if user.avatar else None
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True, methods=['POST', 'DELETE'],
        permission_classes=[permissions.IsAuthenticated],
        url_path='subscribe',
        url_name='subscribe',
    )
    def subscribe(self, request, pk=None):
        author = self.get_object()
        if request.method == 'POST' and request.user == author:
            return Response(
                {'detail': 'You cannot subscribe to yourself.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        subscription_exists = Subscription.objects.filter(
            user=request.user,
            author=author,
        ).exists()
        if request.method == 'DELETE':
            if not subscription_exists:
                return Response(
                    {'detail': 'You are not subscribed on this user.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            Subscription.objects.filter(
                user=request.user,
                author=author
            ).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        if subscription_exists:
            return Response(
                {'detail': 'You are already subscribed to this user.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        subscription = Subscription.objects.create(
            user=request.user,
            author=author
        )
        serializer = SubscriptionSerializer(
            subscription,
            context={
                'request': request,
                'recipes_limit': request.query_params.get('recipes_limit')
            }
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


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
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly,
        IsAuthorOrReadOnly
    ]
    pagination_class = RecipePagination
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    filterset_class = RecipeFilter
    search_fields = ['name', 'text']
    ordering_fields = ['name', 'cooking_time']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return RecipeSerializer
        return RecipeListSerializer

    @action(
        detail=True, methods=['post', 'delete'],
        permission_classes=[permissions.IsAuthenticated]
    )
    def favorite(self, request, pk=None):
        return self._add_delete_recipe(
            request,
            pk,
            FavoriteRecipe,
            {
                'exists': 'Recipe is already in favorites.',
                'not_found': 'Recipe was not in favorite.'
            }
        )

    @action(
        detail=True, methods=['post', 'delete'],
        permission_classes=[permissions.IsAuthenticated]
    )
    def shopping_cart(self, request, pk=None):
        return self._add_delete_recipe(
            request,
            pk,
            ShoppingCart,
            {
                'exists': 'Recipe is already in shopping list.',
                'not_found': 'Recipe was not in shopping cart.'
            }
        )

    @action(
        detail=False, methods=['get'],
        permission_classes=[permissions.IsAuthenticated]
    )
    def favorites(self, request):
        recipes = Recipe.objects.filter(
            favorited_by__user=request.user
        ).select_related('author').prefetch_related(
            'tags', 'recipeingredient_set'
        )
        page = self.paginate_queryset(recipes)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(
        detail=False, methods=['get'],
        permission_classes=[permissions.IsAuthenticated]
    )
    def shopping_list(self, request):
        recipes = Recipe.objects.filter(
            shopping_carts__user=request.user
        ).select_related('author').prefetch_related(
            'tags', 'recipeingredient_set__ingredient'
        )
        page = self.paginate_queryset(recipes)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[permissions.IsAuthenticated],
        url_path='download_shopping_cart',
        url_name='download_shopping_cart'
    )
    def download_shopping_list(self, request):
        ingredients = (
            RecipeIngredient.objects
            .filter(
                recipe__in_shopping_cart__user=request.user
            )
            .values(
                'ingredient__name',
                'ingredient__measurement_unit'
            )
            .annotate(total_amount=Sum('amount'))
            .order_by('ingredient__name')
        )
        content = "Список покупок:\n\n"
        for item in ingredients:
            name = item['ingredient__name']
            unit = item['ingredient__measurement_unit']
            amount = item['total_amount']
            content += f"{name} ({unit}) — {amount}\n"
        response = HttpResponse(
            content, content_type='text/plain'
        )
        response[
            'Content-Disposition'
        ] = 'attachment; filename="shopping_list.txt"'
        return response

    @action(
        detail=True, methods=['get'],
        permission_classes=[permissions.AllowAny],
        url_path='get-link', url_name='get-link',
    )
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        salt = settings.SECRET_KEY
        unique_str = f"{recipe.id}-{salt}"
        hash_bytes = hashlib.sha256(unique_str.encode()).digest()
        short_code = base64.urlsafe_b64encode(hash_bytes).decode()[:8]
        full_url = request.build_absolute_uri('/')[:-1]
        short_url = f"{full_url}/s/{short_code}"
        return Response(
            {'short-link': short_url}, status=status.HTTP_200_OK
        )
