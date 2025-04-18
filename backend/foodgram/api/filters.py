import django_filters

from .models import (
    CustomUser, Recipe, Tag, FavoriteRecipe, Ingredient
)


class CustomUserFilter(django_filters.FilterSet):
    username = django_filters.CharFilter(
        field_name='username', lookup_expr='icontains',
    )

    class Meta:
        model = CustomUser
        fields = ('username',)


class RecipeFilter(django_filters.FilterSet):
    is_favorited = django_filters.NumberFilter(
        method='filter_is_favorited'
    )
    is_in_shopping_cart = django_filters.NumberFilter(
        method='filter_is_in_shopping_cart'
    )
    author = django_filters.NumberFilter(field_name='author')
    tags = django_filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all()
    )

    class Meta:
        model = Recipe
        fields = [
            'author', 'tags', 'is_favorited', 'is_in_shopping_cart'
        ]

    def filter_is_favorited(self, queryset, name, value):
        user = self.request.user
        if value == 1 and user.is_authenticated:
            favorite_recipes = FavoriteRecipe.objects.filter(
                user=user
            ).values_list('recipe', flat=True)
            return queryset.filter(id__in=favorite_recipes)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        user = self.request.user
        if value == 1 and user.is_authenticated:
            return queryset.filter(shopping_cart=user)
        return queryset


class IngredientFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='startswith')

    class Meta:
        model = Ingredient
        fields = ['name']
