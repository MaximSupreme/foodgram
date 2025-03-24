from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    TagViewSet,IngredientViewSet,
    RecipeViewSet, download_shopping_cart
)
from users.views import CustomUserViewSet, SubscriptionViewSet


router = DefaultRouter()
router.register(
    r'users', CustomUserViewSet, basename='users',
)
router.register(
    r'tags', TagViewSet, basename='tags',
)
router.register(
    r'ingredients', IngredientViewSet, basename='ingredients',
)
router.register(
    r'recipes', RecipeViewSet, basename='recipes',
)
router.register(
    r'subscriptions', SubscriptionViewSet, basename='subscriptions',
)

urlpatterns = [
    path(
        '', include(router.urls)
    ),
    path(
        'recipes/download_shopping_cart/',
        download_shopping_cart, name='download_shopping_cart',
    ),
]
