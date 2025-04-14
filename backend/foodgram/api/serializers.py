import re

from django.contrib.auth import get_user_model
from drf_base64.fields import Base64ImageField
from rest_framework import serializers

from .models import (
    Ingredient, Recipe, RecipeIngredient, Tag,
    Subscription, ShoppingCart, FavoriteRecipe
)
from .mixins import SubscriptionMixin

CustomUser = get_user_model()


class CustomUserSerializer(SubscriptionMixin, serializers.ModelSerializer):
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

    def get_avatar(self, obj):
        return obj.avatar.url if obj.avatar else None


class CustomUserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = (
            'id', 'username', 'email', 'password',
            'first_name', 'last_name'
        )
        extra_kwargs = {
            'password': {'write_only': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    def create(self, validated_data):
        return CustomUser.objects.create_user(**validated_data)

    def validate_username(self, name):
        if not re.match(r'^[\w.@+-]+$', name):
            raise serializers.ValidationError(
                'Invalid username. Use letters, numbers or [.@+-]'
            )
        return name

    def validate(self, data):
        username = data.get('username')
        email = data.get('email')
        if CustomUser.objects.filter(
            username=username, email=email
        ).exists():
            return data
        if CustomUser.objects.filter(email=email).exists():
            raise serializers.ValidationError(
                {
                    'email':
                    'This email is already in use by another user.'
                }
            )
        if CustomUser.objects.filter(username=username).exists():
            raise serializers.ValidationError(
                {'username': 'This username is already taken.'}
            )
        return data


class CustomUserUpdateSerializer(serializers.ModelSerializer):
    avatar = serializers.ImageField(
        required=False, allow_null=True
    )

    class Meta:
        model = CustomUser
        fields = (
            'email', 'username', 'first_name',
            'last_name', 'avatar',
        )
        extra_kwargs = {
            'email': {'required': False},
            'username': {'required': False},
        }


class SubscriptionSerializer(SubscriptionMixin, serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='author.id')
    email = serializers.ReadOnlyField(source='author.email')
    username = serializers.ReadOnlyField(source='author.username')
    first_name = serializers.ReadOnlyField(source='author.first_name')
    last_name = serializers.ReadOnlyField(source='author.last_name')
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = (
            'id', 'email', 'username', 'first_name', 'avatar',
            'last_name', 'is_subscribed', 'recipes', 'recipes_count'
        )

    def get_recipes(self, obj):
        recipes = obj.author.recipes.all()
        recipes_limit = self.context.get('recipes_limit')
        if recipes_limit:
            recipes = recipes[:int(recipes_limit)]
        return RecipeMinifiedSerializer(recipes, many=True).data

    def get_recipes_count(self, obj):
        return obj.author.recipes.count()

    def get_avatar(self, obj):
        if obj.author.avatar:
            return self.context['request'].build_absolute_url(
                obj.author.avatar.url
            )
        return None


class SetAvatarSerializer(serializers.Serializer):
    avatar = Base64ImageField(required=True)

    class Meta:
        fields = ('avatar',)

    def validate_avatar(self, value):
        if not value.name.lower().endswith(('.jpg', '.jpeg', '.png')):
            raise serializers.ValidationError(
                'Only JPG, JPEG and PNG images are allowed'
            )
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
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source='ingredient'
    )
    name = serializers.CharField(
        source='ingredient.name', read_only=True
    )
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit',
        read_only=True
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeMinifiedSerializer(serializers.ModelSerializer):
    image = Base64ImageField(read_only=True)

    class Meta:
        model = Recipe
        fields = (
            'id', 'name', 'image', 'cooking_time'
        )
        read_only_fields = (
            'id', 'name', 'image', 'cooking_time'
        )


class RecipeListSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    author = CustomUserSerializer(read_only=True)
    ingredients = IngredientInRecipeSerializer(
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
            if list_name == 'favorites':
                return obj.favorited_by.filter(
                    user=request.user
                ).exists()
            if list_name == 'shopping_cart':
                return ShoppingCart.objects.filter(
                    recipe=obj, user=request.user
                ).exists()
        return False

    def get_is_favorited(self, obj):
        return self.is_in_list(obj, 'favorites')

    def get_is_in_shopping_cart(self, obj):
        return self.is_in_list(obj, 'shopping_cart')


class RecipeSerializer(serializers.ModelSerializer):
    tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all()
    )
    ingredients = serializers.ListField(
        child=serializers.DictField(),
        write_only=True
    )
    image = Base64ImageField()
    author = CustomUserSerializer(read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'ingredients', 'tags', 'author',
            'image', 'name', 'text', 'cooking_time',
            'is_favorited', 'is_in_shopping_cart'
        )
        read_only_fields = (
            'id', 'author', 'is_favorited', 'is_in_shopping_cart'
        )

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.favorited_by.filter(
                user=request.user
            ).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return ShoppingCart.objects.filter(
                recipe=obj, user=request.user
            ).exists()
        return False

    def to_representation(self, instance):
        return RecipeListSerializer(
            instance, context=self.context
        ).data

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError(
                'There must be at least one ingredient.'
            )
        validated_ingredients = []
        seen_ids = set()
        for item in value:
            if not isinstance(item, dict):
                raise serializers.ValidationError(
                    'Each ingredient must be a dict object.'
                )
            if 'id' not in item or 'amount' not in item:
                raise serializers.ValidationError(
                    'Each ingredient must contain "id" и "amount".'
                )
            try:
                ingredient_id = int(item['id'])
                amount = int(item['amount'])
                if ingredient_id in seen_ids:
                    raise serializers.ValidationError(
                        f'These is duplicate ingredient with ID {
                            ingredient_id
                        }'
                    )
                seen_ids.add(ingredient_id)
                if not Ingredient.objects.filter(id=ingredient_id).exists():
                    raise serializers.ValidationError(
                        f'Ingredient with id {ingredient_id} does not exist.'
                    )
                if amount <= 0:
                    raise serializers.ValidationError(
                        'The quantity must be a positive integer.'
                    )
                validated_ingredients.append(
                    {
                        'id': ingredient_id,
                        'amount': amount
                    }
                )
            except ValueError:
                raise serializers.ValidationError(
                    'ID and amount must be positive integers.'
                )
        return validated_ingredients

    def validate_tags(self, value):
        if not value:
            raise serializers.ValidationError(
                'There must be at least one tag.'
            )
        seen_ids = set()
        for tag in value:
            if not isinstance(tag, Tag):
                raise serializers.ValidationError(
                    'Incorrect tag format.'
                )
            if tag.id in seen_ids:
                raise serializers.ValidationError(
                    f'Duplicate tag with id {tag.id}'
                )
            seen_ids.add(tag.id)
        return value

    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)
        RecipeIngredient.objects.bulk_create([
            RecipeIngredient(
                recipe=recipe,
                ingredient_id=ingredient['id'],
                amount=ingredient['amount']
            )
            for ingredient in ingredients_data
        ])
        return recipe

    def update(self, instance, validated_data):
        if 'author' in validated_data:
            validated_data.pop('author')
        if 'ingredients' not in validated_data:
            raise serializers.ValidationError(
                {'ingredients': ['This field is required when updating.']}
            )
        if 'tags' not in validated_data:
            raise serializers.ValidationError(
                {'tags': ['This field is required when updating.']}
            )
        ingredients_data = validated_data.pop('ingredients', None)
        tags_data = validated_data.pop('tags', None)
        instance = super().update(instance, validated_data)
        if tags_data is not None:
            instance.tags.set(tags_data)
        if ingredients_data is not None:
            instance.recipeingredient_set.all().delete()
            RecipeIngredient.objects.bulk_create([
                RecipeIngredient(
                    recipe=instance,
                    ingredient_id=ingredient['id'],
                    amount=ingredient['amount']
                )
                for ingredient in ingredients_data
            ])
        return instance


class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = FavoriteRecipe
        fields = ('user', 'recipe')
        read_only_fields = ('user',)


class ShoppingCartSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingCart
        fields = ('user', 'recipe')
        read_only_fields = ('user',)
