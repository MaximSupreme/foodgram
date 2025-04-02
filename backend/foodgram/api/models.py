from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.text import slugify

from .constants import MAX_STR_AND_SLUG_CHAR, MAX_STRING_CHAR


class CustomUser(AbstractUser):
    email = models.EmailField(
        max_length=MAX_STRING_CHAR,
        unique=True,
        verbose_name='Адрес электронной почты.'
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True,
        blank=True,
        verbose_name='Аватар.'
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('username',)

    def __str__(self):
        return self.username


class Tag(models.Model):
    name = models.CharField(
        max_length=MAX_STR_AND_SLUG_CHAR, unique=True,
        verbose_name='Название'
    )
    slug = models.SlugField(
        max_length=MAX_STR_AND_SLUG_CHAR,
        unique=True, verbose_name='Слаг'
    )

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
        ordering = ('name',)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField(
        max_length=MAX_STRING_CHAR,
        verbose_name='Название',
    )
    measurement_unit = models.CharField(
        max_length=MAX_STR_AND_SLUG_CHAR,
        verbose_name='Единица измерения',
    )

    class Meta:
        verbose_name = 'Ингридиент'
        verbose_name_plural = 'Ингридиенты'
        ordering = ('name',)

    def __str__(self):
        return f'{self.name} - {self.measurement_unit}'


class Recipe(models.Model):
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор публикации'
    )
    name = models.CharField(
        max_length=MAX_STRING_CHAR,
        verbose_name='Название рецепта'
    )
    image = models.ImageField(
        upload_to='recipes/',
        verbose_name='Изображение рецепта'
    )
    text = models.TextField(
        verbose_name='Описание'
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        related_name='recipes',
        verbose_name='Ингридиенты'
    )
    tags = models.ManyToManyField(
        Tag,
        related_name='recipes',
        verbose_name='Теги'
    )
    cooking_time = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1), MaxValueValidator(1000)
        ],
        verbose_name='Время приготовления (в минутах)'
    )
    favorites = models.ManyToManyField(
        CustomUser, related_name='favorites', blank=True
    )

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ('-pk',)

    def __str__(self):
        return self.name

    @property
    def total_favorites(self):
        return self.favorites.count()


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE
    )
    ingredient = models.ForeignKey(
        Ingredient, on_delete=models.CASCADE
    )
    amount = models.IntegerField(
        validators=[
            MinValueValidator(1)
        ],
        verbose_name='Количество',
    )

    class Meta:
        verbose_name = 'Ингридиент в рецепте'
        verbose_name_plural = 'Ингридиенты в рецептах'
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'ingredient'],
                name='unique_recipe_ingredient'
            )
        ]

    def __str__(self):
        return (
            f'({self.ingredient.name}) '
            f'({self.amount} {self.ingredient.measurement_unit})'
        )
