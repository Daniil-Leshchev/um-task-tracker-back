from rest_framework.permissions import BasePermission
from .constants import ADMIN_ROLE_IDS


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        role_id = getattr(getattr(user, 'role', None), 'id_role', None)
        return bool(user and role_id in ADMIN_ROLE_IDS)
