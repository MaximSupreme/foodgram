import base64

import django_filters
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from users.serializers import CustomUserSerializer

from .models import Ingredient, Recipe, Tag
from .permissions import IsAuthorOrReadOnly
from .serializers import (
    IngredientSerializer, RecipeCreateSerializer, RecipeListSerializer,
    RecipeMinifiedSerializer,RecipeUpdateSerializer, TagSerializer
)

CustomUser = get_user_model()


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


class RecipeFilter(django_filters.FilterSet):
    is_favorited = django_filters.NumberFilter(method='filter_is_favorited')
    is_in_shopping_cart = django_filters.NumberFilter(method='filter_is_in_shopping_cart')
    author = django_filters.NumberFilter(field_name='author')
    tags = django_filters.ModelMultipleChoiceFilter(
        field_name='tags', to_field_name='slug', queryset=Tag.objects.all()
    )

    class Meta:
        model = Recipe
        fields = ['author', 'tags', 'is_favorited', 'is_in_shopping_cart']

    def filter_is_favorited(self, queryset, name, value):
        user = self.request.user
        if value == 1 and user.is_authenticated:
            return queryset.filter(favorites__user=user)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        user = self.request.user
        if value == 1 and user.is_authenticated:
            return queryset.filter(shopping_cart__user=user)
        return queryset


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeListSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = RecipeFilter
    search_fields = ['name', 'text']
    ordering_fields = ['name', 'cooking_time']

    def get_serializer_class(self):
        if self.action == 'create':
            return RecipeCreateSerializer
        elif self.action == 'update' or self.action == 'partial_update':
            return RecipeUpdateSerializer
        return RecipeListSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def destroy(self, request, pk=None):
        recipe = self.get_object()
        self.check_object_permissions(request, recipe)
        recipe.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, pk=None):
        recipe = self.get_object()
        self.check_object_permissions(request, recipe)
        serializer = RecipeListSerializer(recipe, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        try:
            recipe = self.queryset.get(pk=pk)
        except Recipe.DoesNotExist:
            raise NotFound(detail="Recipe not found.")
        serializer = RecipeListSerializer(recipe)
        return Response(serializer.data)

    @action(detail=True, methods=['post', 'delete'], permission_classes=[permissions.IsAuthenticated])
    def favorite(self, request, pk=None):
        recipe = self.get_object()
        user = request.user
        if request.method == 'POST':
            if user.favorites.filter(recipe=recipe).exists():
                return Response({'detail': 'Recipe is already in favorites.'}, status=status.HTTP_400_BAD_REQUEST)
            user.favorites.add(recipe)
            return Response(RecipeMinifiedSerializer(recipe).data, status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            if not user.favorites.filter(recipe=recipe).exists():
                return Response({'detail': 'Recipe is not in favorites.'}, status=status.HTTP_400_BAD_REQUEST)
            user.favorites.remove(recipe)
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'], permission_classes=[permissions.IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        recipe = self.get_object()
        user = request.user
        if request.method == 'POST':
            if user.shopping_cart.filter(recipe=recipe).exists():
                return Response({'detail': 'Recipe is already in shopping cart.'}, status=status.HTTP_400_BAD_REQUEST)
            user.shopping_cart.add(recipe)
            return Response(RecipeMinifiedSerializer(recipe).data, status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            if not user.shopping_cart.filter(recipe=recipe).exists():
                return Response({'detail': 'Recipe is not in shopping cart.'}, status=status.HTTP_400_BAD_REQUEST)
            user.shopping_cart.remove(recipe)
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'], permission_classes=[permissions.AllowAny])
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        salt = settings.SECRET_KEY
        text = f'{recipe.id}{salt}'
        hashed_text = haslib.sha256(text.encode('utf-8')).digest()
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

    @action(detail=True, methods=['post', 'delete'], permission_classes=[permissions.IsAuthenticated])
    def subscribe(self, request, pk=None):
        user_to_subscribe = get_object_or_404(CustomUser, pk=pk)
        if request.method == 'POST':
            if request.user == user_to_subscribe:
                return Response({'detail': 'Cannot subscribe to yourself.'}, status=status.HTTP_400_BAD_REQUEST)
            if request.user.subscriptions.filter(author=user_to_subscribe).exists():
                return Response({'detail': 'Already subscribed.'}, status=status.HTTP_400_BAD_REQUEST)
            request.user.subscriptions.add(user_to_subscribe)
            return Response(CustomUserSerializer(user_to_subscribe, context={'request': request}).data, status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            if not request.user.subscriptions.filter(author=user_to_subscribe).exists():
                return Response({'detail': 'Not subscribed.'}, status=status.HTTP_400_BAD_REQUEST)
            request.user.subscriptions.remove(user_to_subscribe)
            return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def download_shopping_cart(request):
    user = request.user
    recipes = user.shopping_cart.all()
    ingredients = {}
    for recipe in recipes:
        for recipe_ingredient in recipe.recipeingredient_set.all():
            ingredient = recipe_ingredient.ingredient
            amount = recipe_ingredient.amount
            if ingredient.name in ingredients:
                ingredients[ingredient.name]['amount'] += amount
            else:
                ingredients[ingredient.name] = {'amount': amount, 'measurement_unit': ingredient.measurement_unit}
    shopping_list = "Shopping List:\n\n"
    for ingredient_name, details in ingredients.items():
        shopping_list += f"- {ingredient_name} - {details['amount']} {details['measurement_unit']}\n"
    response = HttpResponse(shopping_list, content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename="shopping_list.txt"'
    return response
