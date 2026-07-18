from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Header
from application.services.auth_service import AuthenticatedUser
from application.services.query_service import QueryService
from api.dependencies import get_current_user
from schemas.requests import QueryRequest

router = APIRouter(prefix="/query", tags=["query"])

@router.post("")
def query(request: QueryRequest, user: AuthenticatedUser = Depends(get_current_user), x_llm_provider: str = Header(default="groq")):
    result = QueryService().run(request.question, request.source_filter, user, x_llm_provider)
    return {"question": request.question, **result, "timestamp": datetime.now(timezone.utc).isoformat()}
