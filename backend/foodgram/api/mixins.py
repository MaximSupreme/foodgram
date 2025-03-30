from rest_framework import status
from rest_framework.response import Response

from .serializers import RecipeMinifiedSerializer


class AddDeleteRecipeMixin:
    def _get_list_queryset(self, user, list_name):
        return getattr(user, list_name)

    def add_or_remove_recipe(self, request, pk=None, list_name=None):
        recipe = self.get_object()
        user = request.user()
        list_queryset = self._get_list_queryset(user, list_name)
        item_exists = list_queryset.filter(recipe=recipe).exists()
        if request.method == 'POST':
            if item_exists:
                return Response(
                    {'detail': 'Recipe is already in the list.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            list_queryset.add(recipe)
            return Response(
                RecipeMinifiedSerializer(recipe).data,
                status=status.HTTP_201_CREATED
            )
        if not item_exists: 
            return Response( 
                {'detail': 'Recipe is not in the list.'}, 
                status=status.HTTP_400_BAD_REQUEST 
            ) 
        list_queryset.remove(recipe) 
        return Response(status=status.HTTP_204_NO_CONTENT)
