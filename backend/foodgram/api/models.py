from django.contrib.auth import get_user_model
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify


CustomUser = get_user_model()


# class Ingredient(models.Model):
#     """Ingredient model"""
#     name = models.CharField(
#         max_length=64,
#         verbose_name='Название ингридиента'
#     )
#     measure_unit = models.CharField(
#         max_length=64,
#         verbose_name='Единица измерения'
#     )

#     class Meta:
#         verbose_name = 'Ингридиент'
#         verbose_name_plural = 'Ингридиенты'
#         ordering = ('name',)

#     def __str__(self):
#         return f'{self.name} - {self.measure_unit}'


# class Tag(models.Model):
#     """Tag model"""
#     name = models.CharField(
#         max_length=64,
#         unique=True,
#         verbose_name='Название тега'
#     )
#     slug = models.SlugField(
#         max_length=64,
#         unique=True,
#         verbose_name='Слаг',
#         db_index=True
#     )

#     class Meta:
#         verbose_name = 'Тег'
#         verbose_name_plural = 'Теги'
#         ordering = ('name',)

#     def save(self, *args, **kwargs):
#         if not self.slug:
#             self.slug = slugify(self.name)
#         super().save(*args, **kwargs)

#     def __str__(self):
#         return self.name


# class Recipe(models.Model):
#     """Recipe model"""
#     author = models.ForeignKey(
#         CustomUser,
#         on_delete=models.CASCADE,
#         related_name='recipes',
#         verbose_name='Автор публикации'
#     )
#     name = models.CharField(
#         max_length=256,
#         verbose_name='Название рецепта'
#     )
#     image = models.ImageField(
#         upload_to='recipes/',
#         verbose_name='Изображение рецепта'
#     )
#     text = models.TextField(
#         verbose_name='Описание'
#     )
#     ingredients = models.ManyToManyField(
#         Ingredient,
#         through='RecipeIngredient',
#         related_name='recipes',
#         verbose_name='Ингридиенты'
#     )
#     tags = models.ManyToManyField(
#         Tag,
#         related_name='recipes',
#         verbose_name='Теги'
#     )
#     cooking_time = models.PositiveIntegerField(
#         validators=[MinValueValidator(1), MaxValueValidator(1000)],
#         verbose_name='Время приготовления (в минутах)'
#     )

#     class Meta:
#         verbose_name = 'Рецепт'
#         verbose_name_plural = 'Рецепты'
#         ordering = ('-pk',)

#     def __str__(self):
#         return self.name


# class RecipeIngredient(models.Model):
#     """Intermediate model for Ingredient and Recipe bond"""
#     recipe = models.ForeignKey(
#         Recipe,
#         on_delete=models.CASCADE,
#         related_name='recipe_ingredients',
#         verbose_name='Рецепт',
#     )
#     ingredient = models.ForeignKey(
#         Ingredient,
#         on_delete=models.CASCADE,
#         related_name='recipe_ingredients',
#         verbose_name='Ингридиент'
#     )
#     amount = models.IntegerField(
#         validators=[MinValueValidator(1)],
#         verbose_name='Количество',
#     )

#     class Meta:
#         verbose_name = 'Ингридиент в рецепте'
#         verbose_name_plural = 'Ингридиенты в рецептах'
#         constraints = [
#             models.UniqueConstraint(
#                 fields=['recipe', 'ingredient'],
#                 name='unique_recipe_ingredient'
#             )
#         ]

#     def __str__(self):
#         return (f'{self.ingredient.name} - '
#                 f'{self.amount} {self.ingredient.measure_unit}')


#     class Meta:
#         verbose_name = 'Ингридиент в рецепте'
#         verbose_name_plural = 'Ингридиенты в рецепте'
#         constraints = [
#             models.UniqueConstraint(
#                 fields=['recipe', 'ingridient'], name='unique_recipe_ingridient'
#             )
#         ]

#     def __str__(self):
#         return f'{self.ingridient.name} - {self.amount}'


# class Subscription(models.Model):
#     """Subscription model"""
#     user = models.ForeignKey(
#         CustomUser,
#         on_delete=models.CASCADE,
#         related_name='subscriber', 
#         verbose_name='Подписчик'
#     )
#     author = models.ForeignKey(
#         CustomUser,
#         on_delete=models.CASCADE,
#         related_name='subscriptions',
#         verbose_name='Автор'
#     )

#     class Meta:
#         verbose_name = 'Подписка'
#         verbose_name_plural = 'Подписки'
#         constraints = [
#             models.UniqueConstraint(
#                 fields=['user', 'author'],
#                 name='unique_subscription'
#             )
#         ]

#     def __str__(self):
#         return f'{self.user} подписан на {self.author}.'


# class FavoriteRecipe(models.Model):
#     """Favorite recipe model"""
#     user = models.ForeignKey(
#         CustomUser,
#         on_delete=models.CASCADE,
#         related_name='favorited_by',
#         verbose_name='Пользователь'
#     )
#     recipe = models.ForeignKey(
#         Recipe,
#         on_delete=models.CASCADE,
#         related_name='favorite_recipes',
#         verbose_name='Рецепт'
#     )
#     created_at = models.DateTimeField(
#         auto_now_add=True,
#         verbose_name='Дата добавления'
#     )

#     class Meta:
#         verbose_name = 'Избранный рецепт'
#         verbose_name_plural = 'Избранные рецепты'
#         constraints = [
#             models.UniqueConstraint(
#                 fields=['user', 'recipe'],
#                 name = 'unique_favorite_recipe'
#             )
#         ]
#         ordering = ('-created_at',)

#     def __str__(self):
#         return f'{self.user} добавил {self.recipe} в избранное.'


# class ShoppingCart(models.Model):
#     """Shopping cart model"""
#     user = models.ForeignKey(
#         CustomUser,
#         on_delete=models.CASCADE,
#         related_name='shopping_cart',
#         verbose_name='Пользователь'
#     )
#     recipe = models.ForeignKey(
#         Recipe,
#         on_delete=models.CASCADE,
#         related_name='in_shopping_cart',
#         verbose_name='Рецепт'
#     )
#     created_at = models.DateTimeField(
#         auto_now_add=True,
#         verbose_name='Дата добавления'
#     )

#     class Meta:
#         verbose_name = 'Корзина покупок'
#         verbose_name_plural = 'Корзины покупок'
#         constraints = [
#             models.UniqueConstraint(
#                 fields=['user', 'recipe'],
#                 name='unique_shopping_cart_recipe'
#             )
#         ]
#         ordering = ('-created_at')

#     def __str__(self):
#         return f'{self.user} добавил {self.recipe} в корзину.'
class Tag(models.Model):
    name = models.CharField(max_length=32, unique=True, verbose_name='Название')
    slug = models.SlugField(max_length=32, unique=True, verbose_name='Слаг')

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField(max_length=128, verbose_name='Название')
    measurement_unit = models.CharField(max_length=64, verbose_name='Единица измерения')

    def __str__(self):
        return self.name


class Recipe(models.Model):
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='recipes', verbose_name='Автор')
    name = models.CharField(max_length=256, verbose_name='Название')
    image = models.ImageField(upload_to='recipes/', verbose_name='Изображение')
    text = models.TextField(verbose_name='Описание')
    cooking_time = models.PositiveIntegerField(verbose_name='Время приготовления (в минутах)')
        
    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    amount = models.PositiveIntegerField(verbose_name='Количество')

    def __str__(self):
        return f'{self.ingredient.name} ({self.amount} {self.ingredient.measurement_unit})'

    class Meta:
        unique_together = ('recipe', 'ingredient')
