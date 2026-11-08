from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role == "admin")


class IsContentManager(BasePermission):
    """Admins and content managers may manage academic content."""

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role in ("admin", "content_manager"))


class IsStudent(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.is_active)
