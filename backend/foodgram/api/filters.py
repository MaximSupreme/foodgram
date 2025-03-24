from django_filters.rest_framework import CharFilter, FilterSet

from users.models import CustomUser


class CustomUserFilter(FilterSet):
    username = CharFilter(
        field_name='username', lookup_expr='icontains',
    )

    class Meta:
        model = CustomUser
        fields = ('username',)
