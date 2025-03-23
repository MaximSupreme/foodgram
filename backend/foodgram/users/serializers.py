from rest_framework import serializers
from django.contrib.auth import get_user_model

from api.constants import MIN_PASSWORD_LENGTH


CustomUser = get_user_model()


class CustomUserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    password = serializers.CharField(
        write_only=True, required=True, min_length=MIN_PASSWORD_LENGTH
    )

    class Meta:
        ...