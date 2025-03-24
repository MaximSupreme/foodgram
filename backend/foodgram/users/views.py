from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from drf_base64.fields import Base64ImageField
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from users.serializers import (CustomUserCreateSerializer,
                               CustomUserResponseOnCreateSerializer,
                               CustomUserSerializer,
                               SetAvatarResponseSerializer,
                               SetAvatarSerializer, SetPasswordSerializer)

CustomUser = get_user_model()


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
                try:
                    user.avatar = Base64ImageField().to_internal_value(
                        avatar_data
                    )
                    user.save()
                except Exception as e:
                    return Response(
                        {'avatar': [str(e)]},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                return Response(SetAvatarResponseSerializer(
                    {'avatar': user.avatar.url}).data
                )
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )
        elif request.method == 'DELETE':
            if user.avatar:
                user.avatar.delete()
                user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)


class UserCreate(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserCreateSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        response_data = CustomUserResponseOnCreateSerializer(
            serializer.instance
        ).data
        return Response(
            response_data, status=status.HTTP_201_CREATED, headers=headers
        )


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
            return Response(
                {'current_password': ['Wrong password.']},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SubscriptionPagination(PageNumberPagination):
    page_size = 6
    page_size_query_param = 'recipes_limit'


class SubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = SubscriptionPagination

    def get_queryset(self):
        return CustomUser.objects.filter(subscriber=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(
                page, many=True, context={'request': request}
            )
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(
            queryset, many=True, context={'request': request}
        )
        return Response(serializer.data)

    @action(
        detail=True, methods=['post', 'delete'],
        permission_classes=[permissions.IsAuthenticated]
    )
    def subscribe(self, request, pk=None):
        user_to_subscribe = get_object_or_404(CustomUser, pk=pk)
        if request.method == 'POST':
            if request.user == user_to_subscribe:
                return Response(
                    {'detail': 'Cannot subscribe to yourself.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if request.user.subscriber.filter(
                author=user_to_subscribe
            ).exists():
                return Response(
                    {'detail': 'Already subscribed.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            request.user.subscriber.add(user_to_subscribe)
            serializer = CustomUserSerializer(
                user_to_subscribe, context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            if not request.user.subscriber.filter(
                author=user_to_subscribe
            ).exists():
                return Response(
                    {'detail': 'Not subscribed.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            request.user.subscriber.remove(user_to_subscribe)
            return Response(status=status.HTTP_204_NO_CONTENT)
