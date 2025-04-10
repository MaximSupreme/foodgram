from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    IngredientViewSet, RecipeViewSet,
    TagViewSet, SubscriptionViewSet, CustomUserViewSet,
)

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
        '', include('djoser.urls')
    ),
    path(
        'auth/', include('djoser.urls.authtoken'),
    ),
    path(
        '', include(router.urls)
    ),
]
