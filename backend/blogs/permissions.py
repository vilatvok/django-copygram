from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        if view.action in [
            'destroy',
            'update',
            'partial_update',
            'archive',
        ]:
            return request.user == obj.owner
        return True


class PostAuthenticated(BasePermission):
    def has_permission(self, request, view):
        safe_views = ['list']
        return bool(
            view.action in safe_views or
            request.user and
            request.user.is_authenticated
        )
