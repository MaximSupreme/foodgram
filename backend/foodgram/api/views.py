import base64
import hashlib

from drf_base64.fields import Base64ImageField
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from .paginators import RecipePagination
from .filters import RecipeFilter, IngredientFilter
from .mixins import AddDeleteRecipeMixin
from .models import (
    Ingredient, Recipe, Tag, Subscription, FavoriteRecipe, ShoppingCart
)
from .permissions import IsAuthorOrReadOnly
from .serializers import (
    IngredientSerializer, RecipeListSerializer, TagSerializer,
    CustomUserSerializer, SetAvatarResponseSerializer,
    SetAvatarSerializer, CustomUserCreateSerializer,
    CustomUserUpdateSerializer, RecipeCreateSerializer, SubscriptionSerializer,
)

CustomUser = get_user_model()


class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PageNumberPagination

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
        if not request.user.is_authenticated:
            return Response(
                {'detail': 'Credentials were not provided.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
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

    @action(
        detail=True, methods=['POST', 'DELETE'],
        permission_classes=[permissions.IsAuthenticated]
    )
    def subscribe(self, request, pk=None):
        author = self.get_object()
        if request.method == 'DELETE':
            subscription = Subscription.objects.filter(
                user=request.user,
                author=author
            ).first()
            if not subscription:
                return Response(
                    {'detail': 'You are not subscribed on this user.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        if Subscription.objects.filter(
            user=request.user, author=author
        ).exists():
            return Response(
                {'detail': 'You are already subscribed to this user.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        subscription = Subscription.objects.create(
            user=request.user, author=author
        )
        serializer = SubscriptionSerializer(
            subscription,
            context={
                'request': request,
                'recipes_limit': request.query_params.get('recipes_limit')
            }
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['GET'],)
    def subscriptions(self, request):
        queryset = CustomUser.objects.filter(subscriber__user=request.user)
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = SubscriptionSerializer(
                page, many=True,
                context={'request': request}
            )
            return paginator.get_paginated_response(serializer.data)
        serializer = SubscriptionSerializer(
            queryset, many=True,
            context={'request', request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


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
        recipe = self.get_object()
        if request.method == 'POST':
            if FavoriteRecipe.objects.filter(
                user=request.user, recipe=recipe
            ).exists():
                return Response(
                    {'errors': 'Recipe is already in favorites.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            FavoriteRecipe.objects.create(user=request.user, recipe=recipe)
            return Response(
                {
                    'id': recipe.id, 'name': recipe.name,
                    'image': recipe.image.url,
                    'cooking_time': recipe.cooking_time
                }, status=status.HTTP_201_CREATED
            )
        if request.method == 'DELETE':
            FavoriteRecipe.objects.filter(
                user=request.user, recipe=recipe
            ).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True, methods=['post', 'delete'],
        permission_classes=[permissions.IsAuthenticated]
    )
    def shopping_cart(self, request, pk=None):
        recipe = self.get_object()
        if request.method == 'POST':
            if ShoppingCart.objects.filter(
                user=request.user, recipe=recipe
            ).exists():
                return Response(
                    {'errors': 'Recipe is already in shopping list.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            ShoppingCart.objects.create(user=request.user, recipe=recipe)
            return Response(
                {
                    'id': recipe.id, 'name': recipe.name,
                    'image': recipe.image.url,
                    'cooking_time': recipe.cooking_time
                }, status=status.HTTP_201_CREATED
            )
        if request.method == 'DELETE':
            ShoppingCart.objects.filter(
                user=request.user, recipe=recipe
            ).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False, methods=['get'],
        permission_classes=[permissions.IsAuthenticated]
    )
    def favorites(self, request):
        favorites = FavoriteRecipe.objects.filter(user=request.user)
        recipes = [fav.recipe for fav in favorites]
        page = self.paginate_queryset(recipes)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(
        detail=False, methods=['get'],
        permission_classes=[permissions.IsAuthenticated]
    )
    def shopping_list(self, request):
        cart_items = ShoppingCart.objects.filter(user=request.user)
        recipes = [item.recipe for item in cart_items]
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
        cart_items = ShoppingCart.objects.filter(user=request.user)
        ingredients = {}
        for item in cart_items:
            for ingredient in item.recipe.ingredients.all():
                key = f"{ingredient.name} ({ingredient.measurement_unit})"
                ingredients[key] = ingredients.get(key, 0) + ingredient.amount
        content = "Список покупок:\n\n"
        for name, amount in sorted(ingredients.items()):
            content += f"{name} — {amount}\n"
        response = HttpResponse(content, content_type='text/plain')
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
