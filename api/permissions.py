from enum import Enum
from functools import wraps
from rest_framework.response import Response
from rest_framework import status

class RoleEnum(str, Enum):
    ADMIN = "ADMIN"
    ORGANISER = "ORGANISER"
    CAPTAIN = "CAPTAIN"
    PLAYER = "PLAYER"

def role_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(self, request, *args, **kwargs):
            user_role = getattr(request.user, "category", None)
            if user_role and user_role.upper() in [role.upper() for role in allowed_roles]:
                return view_func(self, request, *args, **kwargs)
            return Response(
                {"detail": f"Permission denied. Your role '{user_role}' is not in {allowed_roles}."},
                status=status.HTTP_403_FORBIDDEN
            )
        return _wrapped_view
    return decorator
