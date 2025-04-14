from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class SubscriptionPagination(PageNumberPagination):
    page_size = 6
    page_size_query_param = 'limit'
    max_page_size = 100

    def get_paginated_response(self, data):
        response = super().get_paginated_response(data)
        if hasattr(self, 'recipes_limit'):
            response.data['recipes_limit'] = self.recipes_limit
        return response


class RecipePagination(PageNumberPagination):
    page_size = 6
    page_size_query_param = 'limit'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })
