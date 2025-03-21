from rest_framework.routers import DefaultRouter

from django.urls import include, path


router = DefaultRouter()
router.register(
    'users',
    CustomUserViewSet,
    basename='users',
)

auth_patterns = [
    path(
        'signup/', CustomUserViewSet.as_view(
            {'post': 'signup'}, name='signup',
        )
    )
    path(
        'token/', CustomUserViewSet.as_view(
            {'post': 'token'}, name='token',
        )
    )
]

urlpatterns = [
    path('', include(router.urls)),
    path('users/auth/', include(auth_patterns)),
]
