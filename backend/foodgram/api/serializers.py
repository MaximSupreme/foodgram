import re

from django.contrib.auth import get_user_model
from drf_base64.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import Ingredient, Recipe, RecipeIngredient, Tag, Subscription
from .constants import MAX_STRING_CHAR

CustomUser = get_user_model()


class CustomUserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name',
            'is_subscribed', 'avatar',
        )
        extra_kwargs = {
            'avatar': {'allow_null': True}
        }
        read_only_fields = ('id', 'is_subscribed',)

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Subscription.objects.filter(
                user=request.user, author=obj
            ).exists()
        return False

    def get_avatar(self, obj):
        return obj.avatar.url if obj.avatar else None


class CustomUserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = (
            'username', 'email', 'password',
            'first_name', 'last_name'
        )
        extra_kwargs = {
            'password': {'write_only': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    def create(self, validated_data):
        user = CustomUser.objects.create_user(**validated_data)
        return user

    def validate_username(self, name):
        if not re.match(r'^[\w.@+-]+$', name):
            raise serializers.ValidationError(
                'Invalid username. Use letters, numbers or [.@+-]'
            )
        return name

    def validate(self, data):
        username = data.get('username')
        email = data.get('email')
        if CustomUser.objects.filter(username=username, email=email).exists():
            return data
        if CustomUser.objects.filter(email=email).exists():
            raise serializers.ValidationError(
                {'email': 'This email is already in use by another user.'}
            )
        if CustomUser.objects.filter(username=username).exists():
            raise serializers.ValidationError(
                {'username': 'This username is already taken.'}
            )
        return data


class SetAvatarSerializer(serializers.Serializer):
    avatar = serializers.CharField()

    def validate_avatar(self, value):
        try:
            Base64ImageField().to_internal_value(value)
        except serializers.ValidationError as e:
            raise e
        except Exception as e:
            raise serializers.ValidationError(f"Invalid image {e}")
        return value


class SetAvatarResponseSerializer(serializers.Serializer):
    avatar = serializers.URLField()


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')
        read_only_fields = ('id',)


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')
        read_only_fields = ('id',)


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )
    amount = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeMinifiedSerializer(serializers.ModelSerializer):
    image = Base64ImageField(read_only=True)

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
        read_only_fields = ('id', 'name', 'image', 'cooking_time')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    ingredient = IngredientSerializer(read_only=True)
    amount = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ('ingredient', 'amount')


class RecipeListSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    author = CustomUserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
        source='recipeingredient_set', many=True, read_only=True
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField(read_only=True)

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients',
            'is_favorited', 'is_in_shopping_cart',
            'name', 'image', 'text', 'cooking_time'
        )
        read_only_fields = (
            'id', 'tags', 'author', 'ingredients',
            'is_favorited', 'is_in_shopping_cart'
        )

    def is_in_list(self, obj, list_name):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return getattr(obj, list_name).filter(user=request.user).exists()
        return False

    def get_is_favorited(self, obj):
        return self.is_in_list(obj, 'favorites')

    def get_is_in_shopping_cart(self, obj):
        return self.is_in_list(obj, 'shopping_cart')


class RecipeSerializer(serializers.ModelSerializer):
    tags = serializers.PrimaryKeyRelatedField(
        many=True, read_only=False,
        queryset=Tag.objects.all()
    )
    image = Base64ImageField(required=False)
    name = serializers.CharField(
        max_length=MAX_STRING_CHAR,
        validators=[UniqueValidator(queryset=Recipe.objects.all())]
    )

    class Meta:
        model = Recipe
        fields = (
            'id', 'ingredients', 'tags', 'author',
            'image', 'name', 'text', 'cooking_time',
        )
        read_only_fields = ('id', 'author',)

    def validate_ingredients(self, ingredients):
        for ingredient_data in ingredients:
            if not isinstance(ingredient_data, dict):
                raise serializers.ValidationError(
                    'Each ingredient must be a dictionary.'
                )
            if 'id' not in ingredient_data or 'amount' not in ingredient_data:
                raise serializers.ValidationError(
                    'Each ingredient must have "id" and "amount".'
                )
            try:
                ingredient_id = int(ingredient_data['id'])
                amount = int(ingredient_data['amount'])
            except ValueError:
                raise serializers.ValidationError(
                    'Ingredient "id" and "amount" must be integers.'
                )
            if not Ingredient.objects.filter(id=ingredient_id).exists():
                raise serializers.ValidationError(
                    f'Ingredient with id {ingredient_id} does not exist.'
                )
            if amount <= 0:
                raise serializers.ValidationError(
                    'Amount must be a positive integer.'
                )
        return ingredients

    def validate_tags(self, tags):
        for tag_id in tags:
            if not isinstance(tag_id, int):
                raise serializers.ValidationError(
                    'Each tag ID must be an integer.'
                )
            if not Tag.objects.filter(id=tag_id).exists():
                raise serializers.ValidationError(
                    f'Tag with id {tag_id} does not exist.'
                )
        return tags

    def create_or_update(self, instance=None, validated_data=None):
        ingredients_data = validated_data.pop('ingredients', None)
        tags_data = validated_data.pop('tags', None)
        if instance is None:
            instance = Recipe.objects.create(
                **validated_data
            )
        else:
            instance.recipeingredient_set.all().delete()
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
        if ingredients_data is not None:
            recipe_ingredients = [
                RecipeIngredient(
                    recipe=instance,
                    ingredient_id=ingredient_data['id'],
                    amount=ingredient_data['amount']
                )
                for ingredient_data in ingredients_data
            ]
            RecipeIngredient.objects.bulk_create(recipe_ingredients)
        if tags_data is not None:
            instance.tags.set(tags_data)
        return instance

    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        return self.create_or_update(
            validated_data=validated_data
        )

    def update(self, instance, validated_data):
        return self.create_or_update(
            instance=instance, validated_data=validated_data
        )
