from http import HTTPStatus

from drf_base64.fields import Base64ImageField
import django_filters
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, viewsets
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated

from .serializers import (
    CustomUserSerializer, UserRegistrationSerializer, AdminUserSerializer,
    TagSerializer, SetAvatarSerializer, SetAvatarResponseSerializer
)
from .models import (
    Tag, Ingredient, Recipe, RecipeIngredient,
    Subscription, FavoriteRecipe, ShoppingCart, 
)
from api.permissions import IsAdmin
from api.filters import CustomUserFilter


CustomUser = get_user_model()


# class CustomUserViewSet(viewsets.ModelViewSet):
#     queryset = CustomUser.objects.all()
#     serializer_class = CustomUserSerializer
#     pagination_class = PageNumberPagination
#     permission_classes = (IsAdmin,)
#     lookup_field = 'username'
#     filter_backends = (
#         django_filters.rest_framework.DjangoFilterBackend,
#         filters.SearchFilter
#     )
#     search_fields = ('username',)
#     filterset_class = CustomUserFilter
#     http_method_names = ('get', 'post', 'patch', 'delete')

#     def get_permissions(self):
#         if self.action in ('token'):
#             return []
#         if self.action == 'me':
#             return [IsAuthenticated()]
#         return [IsAdmin()]

#     def get_serializer_class(self):
#         if self.action == 'users':
#             return UserRegistrationSerializer
#         if self.action in ['create', 'update', 'partial_update']:
#             return AdminUserSerializer
#         return CustomUserSerializer

#     def get_object(self):
#         if self.action == 'me':
#             return self.request.user
#         username = self.kwargs.get('username')
#         return get_object_or_404(CustomUser, username=username)


# class TagViewSet(viewsets.ModelViewSet):
#     queryset = Tag.objects.all()
#     serializer_class = TagSerializer


# class IngredientViewSet(viewsets.ModelViewSet):
#     ...


# class RecipeViewSet(viewsets.ModelViewSet):
#     ...
class CustomUserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @action(
        detail=False, methods=['get'], url_path='me',
        permission_classes=[permissions.IsAuthenticated]
    )
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(
        detail=False, methods=['put', 'delete'], url_path='me/avatar',
        permission_classes=[permissions.IsAuthenticated]
    )
    def avatar(self, request):
        user = request.user
        if request.method == 'PUT':
            serializer = SetAvatarSerializer(data=request.data)
            if serializer.is_valid():
                avatar_data = serializer.validated_data['avatar']
                user.avatar = Base64ImageField().to_internal_value(avatar_data)
                user.save()
                return Response(SetAvatarResponseSerializer({'avatar': user.avatar.url}).data)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        elif request.method == 'DELETE':
            user.avatar.delete()
            user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)


class UserCreate(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = CustomUserCreateSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        response_data = CustomUserResponseOnCreateSerializer(serializer.instance).data
        return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)


class SetPasswordView(generics.GenericAPIView):
    serializer_class = SetPasswordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if user.check_password(serializer.data.get('current_password')):
                user.set_password(serializer.data.get('new_password'))
                user.save()
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response({'current_password': ['Wrong password.']}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [permissions.AllowAny]

class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter]
    search_fields = ['^name']  # '^' Starts-with search

class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeListSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['author', 'tags']

    def get_serializer_class(self):
        if self.action == 'create':
            return RecipeCreateSerializer
        elif self.action == 'update' or self.action == 'partial_update':
            return RecipeUpdateSerializer
        return RecipeListSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user) # Set the author on creation

    @action(detail=True, methods=['post', 'delete'], permission_classes=[permissions.IsAuthenticated])
    def favorite(self, request, pk=None):
        recipe = self.get_object()
        user = request.user
        if request.method == 'POST':
            # Logic to add the recipe to the user's favorites
            if user.favorites.filter(recipe=recipe).exists():  # Assuming a M2M field named 'favorites'
                return Response({'detail': 'Recipe is already in favorites.'}, status=status.HTTP_400_BAD_REQUEST)
            user.favorites.add(recipe)
            return Response(RecipeMinifiedSerializer(recipe).data, status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            # Logic to remove the recipe from the user's favorites
            if not user.favorites.filter(recipe=recipe).exists():
                return Response({'detail': 'Recipe is not in favorites.'}, status=status.HTTP_400_BAD_REQUEST)
            user.favorites.remove(recipe)
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'], permission_classes=[permissions.IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        recipe = self.get_object()
        user = request.user
        if request.method == 'POST':
            # Logic to add the recipe to the user's shopping cart
            if user.shopping_cart.filter(recipe=recipe).exists():  # Assuming a M2M field named 'shopping_cart'
                return Response({'detail': 'Recipe is already in shopping cart.'}, status=status.HTTP_400_BAD_REQUEST)
            user.shopping_cart.add(recipe)
            return Response(RecipeMinifiedSerializer(recipe).data, status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            # Logic to remove the recipe from the user's shopping cart
            if not user.shopping_cart.filter(recipe=recipe).exists():
                return Response({'detail': 'Recipe is not in shopping cart.'}, status=status.HTTP_400_BAD_REQUEST)
            user.shopping_cart.remove(recipe)
            return Response(status=status.HTTP_204_NO_CONTENT)


    @action(detail=True, methods=['get'], permission_classes=[permissions.AllowAny])
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        # Logic to generate short link (example using bit.ly or similar)
        short_link = f"https://foodgram.example.org/s/{recipe.id}"  # Replace with actual short link generation
        return Response({'short_link': short_link}) #RecipeGetShortLinkSerializer


class SubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserSerializer  # Or a dedicated SubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Return users the current user is subscribed to
        return User.objects.filter(subscribers=self.request.user)  # Assuming a M2M field named 'subscribers'

    @action(detail=True, methods=['post', 'delete'], permission_classes=[permissions.IsAuthenticated])
    def subscribe(self, request, pk=None):
        user_to_subscribe = get_object_or_404(User, pk=pk)
        if request.method == 'POST':
            # Logic to subscribe the current user to user_to_subscribe
            if request.user == user_to_subscribe:
                return Response({'detail': 'Cannot subscribe to yourself.'}, status=status.HTTP_400_BAD_REQUEST)
            if request.user.subscriptions.filter(author=user_to_subscribe).exists():  # Assuming a M2M field named 'subscriptions'
                return Response({'detail': 'Already subscribed.'}, status=status.HTTP_400_BAD_REQUEST)
            request.user.subscriptions.add(user_to_subscribe)
            return Response(UserSerializer(user_to_subscribe, context={'request': request}).data, status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            # Logic to unsubscribe the current user from user_to_subscribe
            if not request.user.subscriptions.filter(author=user_to_subscribe).exists():
                return Response({'detail': 'Not subscribed.'}, status=status.HTTP_400_BAD_REQUEST)
            request.user.subscriptions.remove(user_to_subscribe)
            return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def download_shopping_cart(request):
    user = request.user
    recipes = user.shopping_cart.all()  # Assuming a M2M field named 'shopping_cart'

    # Generate the shopping list content
    ingredients = {}
    for recipe in recipes:
        for recipe_ingredient in recipe.recipeingredient_set.all():
            ingredient = recipe_ingredient.ingredient
            amount = recipe_ingredient.amount
            if ingredient.name in ingredients:
                ingredients[ingredient.name]['amount'] += amount
            else:
                ingredients[ingredient.name] = {'amount': amount, 'measurement_unit': ingredient.measurement_unit}

    # Create the shopping list string
    shopping_list = "Shopping List:\n\n"
    for ingredient_name, details in ingredients.items():
        shopping_list += f"- {ingredient_name} - {details['amount']} {details['measurement_unit']}\n"

    # Create the response
    response = HttpResponse(shopping_list, content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename="shopping_list.txt"'
    return response