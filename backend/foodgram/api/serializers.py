from django.contrib.auth import get_user_model
from drf_base64.fields import Base64ImageField
from rest_framework import serializers

from .models import Ingredient, Recipe, RecipeIngredient, Tag
from .constants import MIN_PASSWORD_LENGTH

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
    ingredients = serializers.ListField(child=serializers.DictField())
    tags = serializers.ListField(child=serializers.IntegerField())
    image = Base64ImageField(required=False)

    class Meta:
        model = Recipe
        fields = (
            'id', 'ingredients', 'tags',
            'image', 'name', 'text', 'cooking_time'
        )
        read_only_fields = ('id',)

    def validate(self, data):
        ingredients = data.get('ingredients')
        tags = data.get('tags')
        if ingredients:
            self.validate_items(ingredients, 'ingredient')
        if tags:
            self.validate_items(tags, 'tag')
        return data

    def validate_items(self, items, item_type):
        model = Ingredient if item_type == 'ingredient' else Tag
        expected_type = dict if item_type == 'ingredient' else int
        id_field = 'id' if item_type == 'ingredient' else None
        amount_field = 'amount' if item_type == 'ingredient' else None
        for item in items:
            if not isinstance(item, expected_type):
                raise serializers.ValidationError(
                    f'Each {item_type} must be a {expected_type.__name__}.'
                )
            if id_field and id_field not in item:
                raise serializers.ValidationError(
                    f'Each {item_type} must have {id_field}.'
                )
            if amount_field and amount_field not in item:
                raise serializers.ValidationError(
                    f'Each {item_type} must have {amount_field}.'
                )
            if id_field:
                try:
                    item_id = int(item[id_field])
                    amount = int(item[amount_field])
                except ValueError:
                    raise serializers.ValidationError(
                        f'{item_type} {id_field} and '
                        f'{amount_field} must be integers.'
                    )
                if not model.objects.filter(id=item_id).exists():
                    raise serializers.ValidationError(
                        f'{item_type} with id {item_id} does not exist.'
                    )
                if amount <= 0:
                    raise serializers.ValidationError(
                        'Amount must be a positive integer.'
                    )
            else:
                try:
                    item_id = int(item)
                except ValueError:
                    raise serializers.ValidationError(
                        f'{item_type} ID must be an integer.'
                    )
                if not model.objects.filter(id=item_id).exists():
                    raise serializers.ValidationError(
                        f'{item_type} with id {item_id} does not exist.'
                    )

    def create_or_update(self, instance=None, validated_data=None):
        ingredients_data = validated_data.pop('ingredients', None)
        tags_data = validated_data.pop('tags', None)
        if instance:
            instance.recipeingredient_set.all().delete()
        if ingredients_data is not None:
            recipe_ingredients = [
                RecipeIngredient(
                    recipe=instance if instance else None,
                    ingredient_id=ingredient_data['id'],
                    amount=ingredient_data['amount']
                )
                for ingredient_data in ingredients_data
            ]
            if instance is None:
                recipe = Recipe.objects.create(
                    author=self.context['request'].user,
                    **validated_data
                )
                for recipe_ingredient in recipe_ingredients:
                    recipe_ingredient.recipe = recipe
                RecipeIngredient.objects.bulk_create(recipe_ingredients)
            else:
                RecipeIngredient.objects.bulk_create(recipe_ingredients)
        if tags_data is not None:
            if instance:
                instance.tags.set(tags_data)
            else:
                recipe.tags.set(tags_data)
        if instance:
            super().update(instance, validated_data)
            return instance
        else:
            return recipe

    def create(self, validated_data):
        return self.create_or_update(
            validated_data=validated_data
        )

    def update(self, instance, validated_data):
        return self.create_or_update(
            instance=instance, validated_data=validated_data
        )
