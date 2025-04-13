import re

from django.contrib.auth import get_user_model
from drf_base64.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import (
    Ingredient, Recipe, RecipeIngredient, Tag,
    Subscription, ShoppingCart, FavoriteRecipe
)
from .mixins import SubscriptionMixin
from .constants import MAX_STRING_CHAR

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
        return RecipeMinifiedSerializer(
            recipes,
            many=True,
            context=self.context
        ).data

    def get_recipes_count(self, obj):
        return obj.author.recipes.count()

    def get_avatar(self, obj):
        if obj.author.avatar:
            return self.context['request'].build_absolute_url(
                obj.author.avatar.url
            )
        return None


class SetAvatarSerializer(serializers.Serializer):
    avatar = Base64ImageField()

    class Meta:
        fields = ('avatar',)


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
    id = serializers.IntegerField()
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
    id = serializers.IntegerField(
        source='ingredient.id'
    )
    name = serializers.CharField(
        source='ingredient.name'
    )
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount',)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        return {
            'id': representation['id'],
            'name': representation['name'],
            'measurement_unit': representation['measurement_unit'],
            'amount': representation['amount'],
        }


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
            if list_name == 'favorites':
                return obj.favorited_by.filter(user=request.user).exists()
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
        many=True, queryset=Tag.objects.all()
    )
    image = Base64ImageField(required=False)
    name = serializers.CharField(
        max_length=MAX_STRING_CHAR,
        validators=[UniqueValidator(queryset=Recipe.objects.all())]
    )
    ingredients = IngredientInRecipeSerializer(
        source='ingredient_list', many=True
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
        ingredients_data = validated_data.pop('ingredients', [])
        tags_data = validated_data.pop('tags', [])
        if instance is None:
            instance = super().create(validated_data)
        else:
            instance.recipeingredient_set.all().delete()
            instance = super().update(instance, validated_data)
        RecipeIngredient.objects.bulk_create([
            RecipeIngredient(
                recipe=instance,
                ingredient_id=ingredient['id'],
                amount=ingredient['amount']
            )
            for ingredient in ingredients_data
        ])
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


class RecipeCreateSerializer(serializers.ModelSerializer):
    image = Base64ImageField(required=True)
    ingredients = IngredientInRecipeSerializer(many=True)
    tags = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=True
    )

    class Meta:
        model = Recipe
        fields = [
            'id', 'name', 'text', 'cooking_time',
            'ingredients', 'tags', 'image'
        ]
        read_only_fields = ['id']

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError(
                'At least there must be one ingredient.'
            )
        ingredient_ids = [ingredient['id'] for ingredient in value]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            duplicates = [
                id for id in ingredient_ids if ingredient_ids.count(id) > 1
            ]
            raise serializers.ValidationError(
                f'Duplicate ingredient IDs found: {list(set(duplicates))}'
            )
        for ingredient in value:
            if not Ingredient.objects.filter(id=ingredient['id']).exists():
                raise serializers.ValidationError(
                    f'Ingredient with id {ingredient["id"]} does not exist.'
                )
            if ingredient['amount'] <= 0:
                raise serializers.ValidationError(
                    'Amount must be positive.'
                )
        return value

    def validate_tags(self, tags):
        if not tags:
            raise serializers.ValidationError(
                'At least there must be one tag.'
            )
        try:
            tag_ids = [int(tag_id) for tag_id in tags]
        except (ValueError, TypeError):
            raise serializers.ValidationError('Tag ID must be an integer.')
        if len(tag_ids) != len(set(tag_ids)):
            duplicate_ids = [
                tag_id for tag_id in tag_ids if tag_ids.count(tag_id) > 1
            ]
            raise serializers.ValidationError(
                f'Duplicate tag IDs found: {list(set(duplicate_ids))}'
            )
        existing_tags_count = Tag.objects.filter(id__in=tag_ids).count()
        if existing_tags_count != len(tag_ids):
            raise serializers.ValidationError('Some tags do not exist.')
        return tag_ids

    def create(self, validated_data):
        tags_data = validated_data.pop('tags')
        ingredients_data = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)
        for ingredient_data in ingredients_data:
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient_id=ingredient_data['id'],
                amount=ingredient_data['amount']
            )
        return recipe

    def update(self, instance, validated_data):
        if 'ingredients' not in validated_data:
            raise serializers.ValidationError(
                {'ingredients': ['This field is required when updating.']}
            )
        if 'tags' not in validated_data:
            raise serializers.ValidationError(
                {'tags': ['This field is required when updating.']}
            )
        instance.recipeingredient_set.all().delete()
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        recipe_ingredients = [
            RecipeIngredient(
                recipe=instance,
                ingredient_id=ingredient['id'],
                amount=ingredient['amount']
            )
            for ingredient in ingredients_data
        ]
        RecipeIngredient.objects.bulk_create(recipe_ingredients)
        if tags_data is not None:
            instance.tags.set(tags_data)
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


# class ShoppingCartDownloadSerializer(serializers.Serializer):
#     ingredients = serializers.SerializerMethodField()

#     def get_ingredients(self, obj):
#         ingredients = {}
#         for recipe in obj.recipes.all():
#             for ingredient in recipe.ingredients.all():
#                 key = f"{ingredient.name} ({ingredient.measurement_unit})"
#                 if key in ingredients:
#                     ingredients[key] += ingredient.amount
#                 else:
#                     ingredients[key] = ingredient.amount
#         return [f"{name} — {amount}" for name, amount in ingredients.items()]
