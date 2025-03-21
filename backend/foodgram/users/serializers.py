from django.contrib.auth import get_user_model
from rest_framework import serializers

from api.constants import (
    MAX_LENGTH_USER_BIO_INFO,
    MAX_STRING_CHAR, ROLE_USER, ROLES
)
from .utils import username_validator

CustomUser = get_user_model()


class CustomUserSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        max_length=MAX_LENGTH_USER_BIO_INFO,
        validators=[username_validator],
    )
    email = serializers.EmailField(
        max_length=MAX_STRING_CHAR,
    )
    first_name = serializers.CharField(
        max_length=MAX_LENGTH_USER_BIO_INFO,
        required=False,
    )
    last_name = serializers.CharField(
        max_length=MAX_LENGTH_USER_BIO_INFO,
        required=False,
    )

    class Meta:
        model = CustomUser
        fields = (
            'username', 'email', 'first_name',
            'last_name', 'bio', 'role', 'id',
        )
        read_only_fields = ('role',)
