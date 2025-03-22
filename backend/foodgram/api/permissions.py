from rest_framework.permissions import SAFE_METHODS, BasePermission


# class IsAdmin(BasePermission):
#     message = 'Access is allowed only to administrators.'

#     def has_permission(self, request, view):
#         if not request.user.is_authenticated:
#             return False
#         return request.user.is_admin or request.user.is_superuser
class IsAuthorOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.author == request.user