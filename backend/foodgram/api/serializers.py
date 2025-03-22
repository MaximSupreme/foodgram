from django.contrib.auth import get_user_model
from rest_framework import serializers, validators
from drf_base64.fields import Base64ImageField
from .constants import (
    MAX_LENGTH_USER_BIO_INFO,
    MAX_STRING_CHAR, ROLE_USER, ROLES
)
from users.utils import username_and_password_validator
from .models import (
    Ingredient, Recipe, RecipeIngredient,
    FavoriteRecipe, ShoppingCart, Subscription, Tag
)


CustomUser = get_user_model()


# class TagSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Tag
#         fields = '__all__'


# class IngredientSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Ingredient
#         fields = '__all__'


# class SubscriptionSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Subscription
#         fields = ('user', 'author')
#         validators = [
#             serializers.UniqueTogetherValidator(
#                 queryset=Subscription.objects.all(),
#                 fields=('user', 'author'),
#                 message='You are already subscribed to this user.'
#             )
#         ]


# class FavoriteRecipeSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = FavoriteRecipe
#         fields = ('user', 'recipe')
#         validators = [
#             serializers.UniqueTogetherValidator(
#                 queryset=FavoriteRecipe.objects.all(),
#                 queryset=ShoppingCart.objects.all(),
#                 fields=('user', 'recipe'),
#                 message='This recipe is already in shopping cart.'
#             )
#         ]


# class RecipeSerializer(serializers.ModelSerializer):
#     author = CustomUserSerializer(read_only=True)
#     ingredients = RecipeIngredientSerializer(source='recipe_ingredients', many=True)
#     is_favorited = serializers.SerializerMethodField()
#     is_in_shopping_cart = serializers.SerializerMethodField()

#     class Meta:
#         model = Recipe
#         fields = (
#             'id', 'author', 'name', 'image', 'text', 'ingredients',
#             'pub_date', 'cooking_time', 'is_favorited', 'is_in_shopping_cart',
#         )
#         read_only_fields = ('author',)

#         def get_is_favorited(self, obj):
#             user = self.context['request'].user
#             if user.is_authenticated:
#                 return FavoriteRecipe.objects.filter(
#                     user=user, recipe=obj
#                 ).exists()
#             return False

#         def get_is_in_shopping_cart(self, obj):
#             user = self.context['request'].user
#             if user.is_authenticated:
#                 return ShoppingCart.objects.filter(
#                     user=user, recipe=obj
#                 ).exists()
#             return False

#         def create(self, validated_data):
#             ingredients_data = validated_data.pop('ingredients')
#             recipe = Recipe.objects.create(**validated_data)
#             for ingredient_data in ingredients_data:
#                 RecipeIngredient.objects.create(
#                     recipe=recipe, ingredient_id=ingredient_data['id'], amount=ingredient_data['amount']
#                 )
#             return recipe

#         def update(self, instance, validated_data):
#             ingredients_data = validated_data.pop('ingredients')
#             instance.name = validated_data.get('name', instance.name)
#             instance.image = validated_data.get('image', instance.image)
#             instance.text = validated_data.get('text', instance.text)
#             instance.cooking_time = validated_data.get('cooking_time', instance.cooking_time)
#             instance.save()
#             instance.recipe_ingredients.all().delete()
#             for ingredient_data in ingredients_data:
#                 RecipeIngredient.objects.create(
#                     recipe=instance, ingredient_id=ingredient_data['id'], amount=ingredient_data['amount']
#                 )
#             return instance


# class CustomUserSerializer(serializers.ModelSerializer):
#     username = serializers.CharField(
#         max_length=MAX_LENGTH_USER_BIO_INFO,
#         validators=[username_and_password_validator],
#     )
#     email = serializers.EmailField(
#         max_length=MAX_STRING_CHAR,
#     )
#     first_name = serializers.CharField(
#         max_length=MAX_LENGTH_USER_BIO_INFO,
#         required=False,
#     )
#     last_name = serializers.CharField(
#         max_length=MAX_LENGTH_USER_BIO_INFO,
#         required=False,
#     )
#     recipes = RecipeSerializer(many=True, read_only=True)
#     is_subscribed = serializers.SerializerMethodField()

#     class Meta:
#         model = CustomUser
#         fields = (
#             'username', 'email', 'first_name', 'id',
#             'last_name', 'bio', 'role', 'id', 'avatar',
#             'is_subscribed',
#         )
#         read_only_fields = ('role',)

#     def get_is_subscribed(self, obj):
#         user = self.context['request'].user
#         if user.is_authenticated:
#             return obj.following.filter(user=user).exists()
#         return False


# class UserRegistrationSerializer(serializers.ModelSerializer):
#     email = serializers.EmailField(
#         max_length=MAX_STRING_CHAR,
#         required=True,
#     )
#     username = serializers.CharField(
#         max_length=MAX_LENGTH_USER_BIO_INFO,
#         required=True,
#         validators=[username_and_password_validator],
#     )
#     password = serializers.CharField(
#         max_length=MAX_STRING_CHAR,
#         required=True,
#         validators=[username_and_password_validator]
#     )

#     class Meta:
#         model = CustomUser
#         fields = ('email', 'username', 'first_name', 'last_name', 'password')

#     def validate(self, data):
#         username = data.get('username')
#         email = data.get('email')
#         if CustomUser.objects.filter(username=username, email=email).exists():
#             return data
#         if CustomUser.objects.filter(email=email).exists():
#             raise serializers.ValidationError(
#                 {'email': 'This email is already in use by another user!'}
#             )
#         if CustomUser.objects.filter(username=username).exists():
#             raise serializers.ValidationError(
#                 {'username': 'This username is already taken!'}
#             )
#         return data


# class AdminUserSerializer(serializers.ModelSerializer):
#     email = serializers.EmailField(
#         max_length=MAX_STRING_CHAR,
#         required=True,
#         validators=[validators.UniqueValidator(
#             queryset=CustomUser.objects.all(),
#             message='User with that email is already exists!')]
#     )
#     username = serializers.CharField(
#         max_length=MAX_LENGTH_USER_BIO_INFO,
#         required=True,
#         validators=[
#             username_and_password_validator, validators.UniqueValidator(
#                 queryset=CustomUser.objects.all(),
#                 message='User with that username is already exists!'
#             )
#         ]
#     )
#     first_name = serializers.CharField(
#         max_length=MAX_LENGTH_USER_BIO_INFO,
#         required=False
#     )
#     last_name = serializers.CharField(
#         max_length=MAX_LENGTH_USER_BIO_INFO,
#         required=False
#     )
#     bio = serializers.CharField(
#         max_length=MAX_STRING_CHAR,
#         required=False
#     )
#     role = serializers.ChoiceField(
#         choices=ROLES, default=ROLE_USER, required=False
#     )

#     class Meta:
#         model = CustomUser
#         fields = (
#             'username', 'email', 'first_name', 'last_name', 'bio', 'role'
#         )
class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')
        read_only_fields = ('id',)


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = '__all__'


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(source='ingredient.measurement_unit')
    amount = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField()

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

    def get_ingredients(self, obj):
        ingredients = RecipeIngredient.objects.filter(recipe=obj)
        return IngredientInRecipeSerializer(ingredients, many=True).data

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.favorites.filter(user=request.user).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.shopping_cart.filter(user=request.user).exists()
        return False


class RecipeCreateSerializer(serializers.ModelSerializer):
    ingredients = serializers.ListField(child=serializers.DictField())
    tags = serializers.ListField(child=serializers.IntegerField())
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'ingredients', 'tags', 'image', 'name', 'text', 'cooking_time')
        read_only_fields = ('id',)

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        recipe = Recipe.objects.create(author=self.context['request'].user, **validated_data)
        for ingredient_data in ingredients_data:
            ingredient = Ingredient.objects.get(id=ingredient_data['id'])
            RecipeIngredient.objects.create(recipe=recipe, ingredient=ingredient, amount=ingredient_data['amount'])
        recipe.tags.set(tags_data)
        return recipe


class RecipeUpdateSerializer(serializers.ModelSerializer):
    ingredients = serializers.ListField(child=serializers.DictField(), required=False)
    tags = serializers.ListField(child=serializers.IntegerField(), required=False)
    image = Base64ImageField(required=False)

    class Meta:
        model = Recipe
        fields = ('ingredients', 'tags', 'image', 'name', 'text', 'cooking_time')

    def update(self, instance, validated_data):
        if 'ingredients' in validated_data:
            ingredients_data = validated_data.pop('ingredients')
            instance.recipeingredient_set.all().delete()
            for ingredient_data in ingredients_data:
                ingredient = Ingredient.objects.get(id=ingredient_data['id'])
                RecipeIngredient.objects.create(recipe=instance, ingredient=ingredient, amount=ingredient_data['amount'])
        if 'tags' in validated_data:
            tags_data = validated_data.pop('tags')
            instance.tags.set(tags_data)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class RecipeGetShortLinkSerializer(serializers.Serializer):
    short_link = serializers.URLField()


class SetAvatarSerializer(serializers.Serializer):
    avatar = serializers.CharField()


class SetAvatarResponseSerializer(serializers.Serializer):
    avatar = serializers.URLField()