from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if isinstance(exc, AttributeError) and "'AnonymousUser'" in str(exc):
        return Response(
            {'detail': 'Authentication credentials were not provided.'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    return response
