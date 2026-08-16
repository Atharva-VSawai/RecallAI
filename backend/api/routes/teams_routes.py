from fastapi import APIRouter, BackgroundTasks, Depends, Query
from fastapi.responses import PlainTextResponse, RedirectResponse
from urllib.parse import quote
from application.services.auth_service import AuthenticatedUser
from application.services.project_service import ProjectContext
from application.services.teams_service import TeamsService
from api.dependencies import get_current_user, get_project_context, require_project_permission
from api.rate_limit import TEAMS_SYNC_LIMIT, require_rate_limit
from core.config import settings
from domain.exceptions import ValidationError

router = APIRouter(prefix="/integrations/teams", tags=["microsoft-teams"])

@router.get("/connect")
def connect(user: AuthenticatedUser = Depends(get_current_user), project: ProjectContext = Depends(require_project_permission("project:manage"))):
    return {"url": TeamsService().connect_url(project, user)}

@router.get("/oauth/callback")
def oauth_callback(code: str | None = Query(default=None), state: str | None = Query(default=None), error: str | None = Query(default=None), error_description: str | None = Query(default=None)):
    frontend_url = TeamsService.frontend_url()
    if error:
        detail = error_description or error
        return RedirectResponse(url=f"{frontend_url}/teams?error={quote(detail)}")
    if not code or not state:
        return RedirectResponse(url=f"{frontend_url}/teams?error=missing_oauth_response")
    result = TeamsService().complete_oauth(code, state)
    return RedirectResponse(url=f"{frontend_url}/teams?connected=1&project={result['project_id']}")

@router.get("/status")
def status(project: ProjectContext = Depends(require_project_permission("project:read"))): return TeamsService().status(project)

@router.delete("/connection")
def disconnect(project: ProjectContext = Depends(require_project_permission("project:manage"))): return TeamsService().disconnect(project)

@router.get("/meetings")
def meetings(project: ProjectContext = Depends(require_project_permission("knowledge:read"))): return {"meetings": TeamsService().meetings(project)}

@router.get("/meetings/{meeting_id}")
def meeting(meeting_id: str, project: ProjectContext = Depends(require_project_permission("knowledge:read"))): return TeamsService().meeting(project, meeting_id)

@router.post("/sync")
def sync(background_tasks: BackgroundTasks, user: AuthenticatedUser = Depends(get_current_user), project: ProjectContext = Depends(require_project_permission("knowledge:write")), _: None = Depends(require_rate_limit("teams-sync", TEAMS_SYNC_LIMIT))): 
    return TeamsService().sync(project, user, background_tasks=background_tasks)

@router.post("/notifications")
def notifications(background_tasks: BackgroundTasks, payload: dict | None = None, validationToken: str | None = Query(default=None)):
    # Graph validates a subscription by sending validationToken as a query param;
    # production deployments can enqueue resource notifications here.
    if validationToken:
        return PlainTextResponse(validationToken)
    # Graph validation handshakes are unauthenticated by design. Actual
    # notifications require an explicitly configured clientState; falling
    # back to an encryption key made an unset/misconfigured webhook open to
    # arbitrary sync triggers.
    expected_state = settings.teams_webhook_client_state.strip()
    if not expected_state:
        raise ValidationError("Teams webhook authentication is not configured")
    for notification in (payload or {}).get("value", []):
        if notification.get("clientState") != expected_state:
            continue
        subscription_id = notification.get("subscriptionId")
        if subscription_id:
            background_tasks.add_task(TeamsService().sync_subscription, subscription_id, background_tasks)
    return {"status": "accepted", "received": len((payload or {}).get("value", []))}
