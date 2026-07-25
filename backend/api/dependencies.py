from fastapi import Depends, Header
from application.services.auth_service import AuthService, AuthenticatedUser
from application.services.project_service import ProjectContext, ProjectService
from domain.exceptions import AuthenticationError, AuthorizationError


def get_current_user(authorization: str | None = Header(default=None)) -> AuthenticatedUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthenticationError("A bearer access token is required")
    return AuthService().authenticate(authorization.split(" ", 1)[1])


def require_roles(*roles: str):
    def dependency(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if user.role not in roles:
            raise AuthorizationError("You do not have permission to perform this action")
        return user
    return dependency


def get_project_context(
    x_project_id: str | None = Header(default=None),
    user: AuthenticatedUser = Depends(get_current_user),
) -> ProjectContext:
    return ProjectService().get_project_context(user, x_project_id)


def require_project_permission(permission: str):
    def dependency(project: ProjectContext = Depends(get_project_context)) -> ProjectContext:
        return ProjectService().require_permission(project, permission)
    return dependency
