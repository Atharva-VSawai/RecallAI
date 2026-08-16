from fastapi import APIRouter, Depends

from api.dependencies import get_current_user, require_project_permission
from application.services.auth_service import AuthenticatedUser
from application.services.observability_service import breakers, store
from application.services.project_service import ProjectContext
from core.config import settings
from core.llm import is_ollama_reachable
from schemas.requests import BudgetRequest

router = APIRouter(prefix="/observability", tags=["observability"])


@router.get("/dashboard")
def dashboard(project: ProjectContext = Depends(require_project_permission("project:read"))):
    return {"status": "success", "project_id": project.project_id, **store.snapshot(project.project_id)}


@router.get("/alerts")
def alerts(project: ProjectContext = Depends(require_project_permission("project:read"))):
    snapshot = store.snapshot(project.project_id)
    total = snapshot["metrics"].get("query_started", 0)
    failed = snapshot["metrics"].get("query_failed", 0)
    error_rate = failed / total if total else 0.0
    active_breakers = [name for name, breaker in breakers.items() if not breaker.allow()]
    alerts = []
    if error_rate >= settings.observability_alert_error_rate:
        alerts.append({"type": "error_rate", "value": error_rate, "threshold": settings.observability_alert_error_rate})
    if active_breakers:
        alerts.append({"type": "provider_circuit_open", "providers": active_breakers})
    return {"status": "alert" if alerts else "ok", "alerts": alerts}


@router.get("/providers")
def providers(project: ProjectContext = Depends(require_project_permission("project:read"))):
    return {"groq": {"configured": bool(settings.groq_api_key), "circuit_open": not breakers["groq"].allow()}, "ollama": {"configured": bool(settings.ollama_base_url), "reachable": is_ollama_reachable(), "circuit_open": not breakers["ollama"].allow()}, "cohere": {"configured": bool(settings.cohere_api_key), "circuit_open": not breakers["cohere"].allow()}, "chroma": {"circuit_open": not breakers["chroma"].allow()}}


@router.put("/budget")
def set_budget(request: BudgetRequest, user: AuthenticatedUser = Depends(get_current_user), project: ProjectContext = Depends(require_project_permission("project:manage"))):
    return {"status": "success", "budget": store.set_budget(project.project_id, request.user_id, {"cost": request.cost})}
