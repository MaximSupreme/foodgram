import django_filters
from django_filters.rest_framework import CharFilter, FilterSet

from .models import CustomUser, Recipe, Tag, FavoriteRecipe, Ingredient


class CustomUserFilter(FilterSet):
    username = CharFilter(
        field_name='username', lookup_expr='icontains',
    )

    class Meta:
        model = CustomUser
        fields = ('username',)


class RecipeFilter(django_filters.FilterSet):
    is_favorited = django_filters.NumberFilter(method='filter_is_favorited')
    is_in_shopping_cart = django_filters.NumberFilter(
        method='filter_is_in_shopping_cart'
    )
    author = django_filters.NumberFilter(field_name='author')
    tags = django_filters.ModelMultipleChoiceFilter(
        field_name='tags', queryset=Tag.objects.all()
    )

    class Meta:
        model = Recipe
        fields = ['author', 'tags', 'is_favorited', 'is_in_shopping_cart']

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
            return queryset.filter(recipe_for_shopping_cart__user=user)
        return queryset


class IngredientFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='startswith')

    class Meta:
        model = Ingredient
        fields = ['name']
