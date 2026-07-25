from fastapi import APIRouter, Depends, Query
from application.services.auth_service import AuthenticatedUser
from application.services.project_service import ProjectContext
from api.dependencies import get_current_user, require_project_permission

router = APIRouter(prefix="/activity", tags=["activity"])

@router.get("")
def get_activity(limit: int = Query(default=50, ge=1, le=100), user: AuthenticatedUser = Depends(get_current_user), project: ProjectContext = Depends(require_project_permission("project:read"))):
    from activity_store import activity_store
    return activity_store.get_events(limit=limit, user_id=user.user_id, project_id=project.project_id)
