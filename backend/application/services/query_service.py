import logging

from application.services.auth_service import AuthenticatedUser
from application.services.project_service import ProjectContext
from domain.exceptions import ExternalServiceError
from core.config import settings
from activity_store import activity_store
from application.services.observability_service import cache_key, store, usage_scope

logger = logging.getLogger(__name__)


class QueryService:
    def run(self, question: str, source_filter: str | None, user: AuthenticatedUser, provider: str, project: ProjectContext) -> dict:
        provider = provider.strip().lower()
        if provider not in {"groq", "ollama"}:
            raise ExternalServiceError("Unsupported LLM provider")
        key = cache_key(question, project.organization_id, project.project_id, user.user_id, provider, source_filter)
        cached = store.cache_get(key)
        if cached is not None:
            return {**cached, "cache_hit": True}
        store.check_budget(project.project_id, user.user_id, estimated_cost=0.0)
        store.metric("query_started", project_id=project.project_id, user_id=user.user_id)
        try:
            from agents.router import run
            from db.chroma import query_embedding_cache
            with usage_scope(user_id=user.user_id, project_id=project.project_id, organization_id=project.organization_id), query_embedding_cache():
                result = run(question, source_filter=source_filter, provider=provider, project_id=project.project_id, organization_id=project.organization_id)
        except Exception as exc:
            store.metric("query_failed", project_id=project.project_id, user_id=user.user_id)
            logger.exception(
                "[QueryService] Query failed for project=%s org=%s question=%r",
                project.project_id,
                project.organization_id,
                question,
            )
            raise ExternalServiceError("Knowledge query could not be completed") from exc
        store.metric("query_completed", project_id=project.project_id, user_id=user.user_id, agent=result.get("agent_used"))
        store.cache_set(key, result, settings.query_cache_ttl_seconds)
        store.record_usage("query", provider, units=1, project_id=project.project_id, user_id=user.user_id)
        agent_type = result["agent_used"].lower()
        title = f"Query: {question[:50]}{'...' if len(question) > 50 else ''}"
        activity_store.add_event(agent_type, title, f"{result['agent_used']} agent responded", "Neo4j + ChromaDB" if agent_type == "query" else "Neo4j", user_id=user.user_id, project_id=project.project_id, organization_id=project.organization_id)
        return result
