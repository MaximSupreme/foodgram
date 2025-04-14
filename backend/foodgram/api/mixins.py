from rest_framework import status
from rest_framework.response import Response

from .models import Subscription, ShoppingCart, Recipe


class AddDeleteRecipeMixin:
    def _add_delete_recipe(self, request, pk, model, error_message):
        recipe = self.get_object()
        user = request.user
        obj_exists = model.objects.filter(user=user, recipe=recipe).exists()
        if request.method == 'POST':
            if obj_exists:
                return Response(
                    {'errors': error_message['exists']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            model.objects.create(user=user, recipe=recipe)
            return Response(
                {
                    'id': recipe.id,
                    'name': recipe.name,
                    'image': recipe.image.url,
                    'cooking_time': recipe.cooking_time
                },
                status=status.HTTP_201_CREATED
            )
        if not obj_exists:
            return Response(
                {'errors': error_message['not_found']},
                status=status.HTTP_400_BAD_REQUEST
            )
        model.objects.filter(user=user, recipe=recipe).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FavoriteShoppingCartMixin:
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


class RecipeListActionsMixin:
    def _get_user_recipes(self, request, related_field):
        recipes = Recipe.objects.filter(
            **{f"{related_field}__user": request.user}
        ).select_related('author').prefetch_related(
            'tags', 'recipeingredient_set__ingredient'
        )
        page = self.paginate_queryset(recipes)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class SubscriptionMixin:
    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        author = getattr(obj, 'author', obj)
        return Subscription.objects.filter(
            user=request.user,
            author=author
        ).exists()
