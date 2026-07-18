from application.services.auth_service import AuthenticatedUser
from domain.exceptions import ExternalServiceError
from activity_store import activity_store


class QueryService:
    def run(self, question: str, source_filter: str | None, user: AuthenticatedUser, provider: str) -> dict:
        try:
            from agents.router import run
            result = run(question, source_filter=source_filter, provider=provider)
        except Exception as exc:
            raise ExternalServiceError("Knowledge query could not be completed") from exc
        agent_type = result["agent_used"].lower()
        title = f"Query: {question[:50]}{'...' if len(question) > 50 else ''}"
        activity_store.add_event(agent_type, title, f"{result['agent_used']} agent responded", "Neo4j + ChromaDB" if agent_type == "query" else "Neo4j", user_id=user.user_id)
        return result
