from django_filters.rest_framework import CharFilter, FilterSet
from django.contrib.auth import get_user_model

from users.models import CustomUser


class CustomUserFilter(FilterSet):
    username = CharFilter(
        field_name='username', lookup_expr='icontains',
    )

    class Meta:
        model = CustomUser
        fields = ('username',)