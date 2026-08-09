from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Header
from application.services.auth_service import AuthenticatedUser
from application.services.project_service import ProjectContext
from application.services.query_service import QueryService
from api.dependencies import get_current_user, require_project_permission
from api.rate_limit import QUERY_LIMIT, require_rate_limit
from schemas.requests import QueryRequest

router = APIRouter(prefix="/query", tags=["query"])

@router.post("")
def query(request: QueryRequest, user: AuthenticatedUser = Depends(get_current_user), project: ProjectContext = Depends(require_project_permission("knowledge:read")), _: None = Depends(require_rate_limit("query", QUERY_LIMIT)), x_llm_provider: str = Header(default="groq")):
    result = QueryService().run(request.question, request.source_filter, user, x_llm_provider, project)
    return {"question": request.question, **result, "timestamp": datetime.now(timezone.utc).isoformat()}
