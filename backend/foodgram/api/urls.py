from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    IngredientViewSet, RecipeViewSet,
    TagViewSet, download_shopping_cart,
    CustomUserViewSet, SubscriptionViewSet,
    UserCreate, SetPasswordView
)

router = DefaultRouter()
# router.register(
#     r'users', CustomUserViewSet, basename='users',
# )
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
    # path(
    #     'users/', UserCreate.as_view(),
    #     name='user-create'
    # ),
    path(
        '', include('djoser.urls')
    ),
    # path(
    #     '', include('djoser.urls.authtoken')
    # ),
    # path(
    #     'users/set_password/', SetPasswordView.as_view(),
    #     name='set-password'
    # ),
]
# url_patterns = [
#     path('', include(router.urls)),
#     path('auth/', include('djoser.urls.authtoken')),
#     path('recipes/download_shopping_cart/', download_shopping_cart, name='download_shopping_cart'),
# ]
