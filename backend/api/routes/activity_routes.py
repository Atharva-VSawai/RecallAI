from fastapi import APIRouter, Depends, Query
from application.services.auth_service import AuthenticatedUser
from api.dependencies import get_current_user

router = APIRouter(prefix="/activity", tags=["activity"])

@router.get("")
def get_activity(limit: int = Query(default=50, ge=1, le=100), user: AuthenticatedUser = Depends(get_current_user)):
    from activity_store import activity_store
    return activity_store.get_events(limit=limit, user_id=user.user_id)
