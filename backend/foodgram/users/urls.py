from django.urls import path, include
from users import views

urlpatterns = [
    path(
        'users/', views.UserCreate.as_view(),
        name='user-create'
    ),
    path(
        '', include('djoser.urls')
    ),
    path(
        '', include('djoser.urls.authtoken')
    ),
    path(
        'users/set_password/', views.SetPasswordView.as_view(),
        name='set-password'
    ),
]
