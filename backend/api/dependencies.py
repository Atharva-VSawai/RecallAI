from fastapi import Header
from application.services.auth_service import AuthService, AuthenticatedUser
from domain.exceptions import AuthenticationError, AuthorizationError


def get_current_user(authorization: str | None = Header(default=None)) -> AuthenticatedUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthenticationError("A bearer access token is required")
    return AuthService().authenticate(authorization.split(" ", 1)[1])


def require_roles(*roles: str):
    def dependency(user: AuthenticatedUser = get_current_user) -> AuthenticatedUser:
        if user.role not in roles:
            raise AuthorizationError("You do not have permission to perform this action")
        return user
    return dependency
