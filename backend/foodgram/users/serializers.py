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
        model = CustomUser
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name',
            'is_subscribed', 'avatar'
        )
        read_only_fields = ('id', 'is_subscribed')

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.if_authenticated:
            return request.user.subscriber.filter(author=obj).exists()
        return False


class CustomUserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('email', 'username', 'first_name', 'last_name', 'password')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = CustomUser.objects.create_user(**validated_data)


class CustomUserResponseOnCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'email', 'username', 'first_name', 'last_name')


class SetAvatarSerializer(serializers.Serializer):
    avatar = serializers.CharField()


class SetAvatarResponseSerializer(serializers.Serializer):
    avatar = serializers.URLField()


class SetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True)
    current_password = serializers.CharField(write_only=True)
