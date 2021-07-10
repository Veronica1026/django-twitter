from rest_framework.permissions import BasePermission


class IsObjectOwner(BasePermission):
    """
    responsible for chcking if obj.user == request.user
    - for actions with detail=False, only check has_permission
    - for actions with detail=True, check both has_permission and has_object_permission
    """

    message = "You do not have permission to access this object"

    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):
        return request.user == obj.user





