import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.router import route
from agents.query_agent import _search_query
from api.rate_limit import Limit, UserProjectRateLimiter, rate_limiter
from application.services.auth_service import AuthenticatedUser, _organization_id
from application.services.project_service import ProjectContext, ProjectService
from db import chroma, neo
from domain.exceptions import RateLimitError


def test_router_avoids_llm_for_high_confidence_impact_and_factual_queries():
    with patch("agents.router.get_llm") as get_llm:
        assert route("What happens if we delay the migration?") == "IMPACT"
        assert route("Who decided to migrate the reporting database?") == "QUERY"
    get_llm.assert_not_called()


def test_router_uses_llm_only_for_ambiguous_intent():
    llm = MagicMock()
    llm.invoke.return_value = SimpleNamespace(content="IMPACT")
    with patch("agents.router.get_llm", return_value=llm) as get_llm:
        assert route("Compare the migration alternatives") == "IMPACT"
    get_llm.assert_called_once()


def test_query_agent_replaces_scope_ids_and_generic_placeholders_with_question():
    question = "Why did we choose Supabase?"
    assert _search_query("user:org-a", question, "project-a", "user:org-a") == question
    assert _search_query("project-a", question, "project-a", "user:org-a") == question
    assert _search_query("document content", question, "project-a", "user:org-a") == question
    assert _search_query("Supabase decision", question, "project-a", "user:org-a") == "Supabase decision"


def test_request_embedding_cache_reuses_same_query_vector():
    fake_embeddings = MagicMock()
    fake_embeddings.embed_query.return_value = [0.1, 0.2]
    fake_collection = MagicMock()
    fake_collection.query.return_value = {
        "documents": [["Evidence about the migration"]],
        "metadatas": [[{"project_id": "project-a", "source": "meeting.txt"}]],
    }
    with patch.object(chroma, "_embeddings", fake_embeddings), patch.object(chroma, "_collection", fake_collection):
        with chroma.query_embedding_cache():
            chroma.chroma_search("migration", project_id="project-a")
            chroma.chroma_search("migration", project_id="project-a")
    assert fake_embeddings.embed_query.call_count == 1
    assert fake_collection.query.call_count == 2


def test_fulltext_search_uses_indexes_and_applies_tenant_filters():
    session = MagicMock()
    session.run.side_effect = [
        SimpleNamespace(data=lambda: [{"id": "decision-1", "decision": "Migrate", "topic": "DB", "impact": "Low", "source": "doc", "timestamp": "", "reasons": [], "people": [], "alternatives": []}]),
        SimpleNamespace(data=lambda: []),
    ]
    driver = MagicMock()
    driver.session.return_value.__enter__.return_value = session
    with patch.object(neo, "_driver", driver):
        records = neo.neo_search("database migration", project_id="project-a", organization_id="org-a")

    assert records[0]["id"] == "decision-1"
    statement = session.run.call_args_list[0].args[0]
    parameters = session.run.call_args_list[0].kwargs
    assert "db.index.fulltext.queryNodes('decision_search'" in statement
    assert "MATCH (d:Decision)\n            OPTIONAL" not in statement
    assert parameters["project_id"] == "project-a"
    assert parameters["organization_id"] == "org-a"
    assert '"database" OR "migration"' == parameters["fulltext_query"]


def test_fulltext_index_migration_is_idempotent_and_covers_searchable_nodes():
    session = MagicMock()
    driver = MagicMock()
    driver.session.return_value.__enter__.return_value = session
    with patch("db.neo.get_driver", return_value=driver):
        neo.ensure_search_indexes()

    statements = [call.args[0] for call in session.run.call_args_list]
    assert all("IF NOT EXISTS" in statement for statement in statements)
    assert any("decision_search" in statement for statement in statements)
    assert any("meeting_knowledge_search" in statement for statement in statements)
    assert any("person_search" in statement for statement in statements)
    assert any("reason_search" in statement for statement in statements)


def test_graph_endpoint_bounds_decisions_and_returns_partial_metadata(monkeypatch):
    calls = []

    class Result:
        def __init__(self, data=None, single=None): self._data, self._single = data or [], single
        def data(self): return self._data
        def single(self): return self._single

    class Session:
        def run(self, statement, **params):
            calls.append((statement, params))
            if "count(d)" in statement:
                return Result(single={"total_decisions": 750})
            return Result(data=[{"d": {"id": "d-1", "action": "Migrate", "source": "doc"}, "people": [], "reasons": [], "alternatives": []}])

    from api.routes.graph_routes import graph_data
    monkeypatch.setattr("api.routes.graph_routes.execute_with_retry", lambda operation, **_: operation(Session()))
    project = ProjectContext("project-a", "org-a", "Project A", "project-a", "OWNER", ("knowledge:read",))
    response = graph_data(limit=100, offset=0, project=project)

    assert response["pagination"] == {"limit": 100, "offset": 0, "returned_decisions": 1, "total_decisions": 750, "has_more": True}
    graph_statement, graph_params = calls[1]
    assert "SKIP $offset" in graph_statement and "LIMIT $limit" in graph_statement
    assert graph_params["organization_id"] == "org-a"
    assert graph_params["limit"] == 100
    assert graph_params["relation_limit"] == 2


def test_rate_limits_are_scoped_to_user_and_project():
    limiter = UserProjectRateLimiter()
    limit = Limit(requests=2, window_seconds=60)
    limiter.check("query", "user-a", "project-a", limit, now=10)
    limiter.check("query", "user-a", "project-a", limit, now=11)
    with pytest.raises(RateLimitError):
        limiter.check("query", "user-a", "project-a", limit, now=12)
    limiter.check("query", "user-a", "project-b", limit, now=12)
    limiter.check("query", "user-b", "project-a", limit, now=12)


def test_query_endpoint_returns_generic_429_after_user_project_limit(monkeypatch):
    from api.dependencies import get_current_user, get_project_context
    from application.services.query_service import QueryService
    from main import app
    from fastapi.testclient import TestClient

    user = AuthenticatedUser("user-a", "org-a", "USER", "a@example.test")
    project = ProjectContext("project-a", "org-a", "Project A", "project-a", "OWNER", ("knowledge:read",))
    rate_limiter._hits.clear()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_project_context] = lambda: project
    monkeypatch.setattr(QueryService, "run", lambda *_: {"answer": "ok", "agent_used": "QUERY"})
    try:
        client = TestClient(app)
        responses = [client.post("/query", json={"question": "Who decided this?"}) for _ in range(11)]
    finally:
        app.dependency_overrides.clear()
        rate_limiter._hits.clear()

    assert [response.status_code for response in responses[:10]] == [200] * 10
    assert responses[10].status_code == 429
    assert responses[10].json()["error"]["message"] == "Too many requests. Please try again shortly."


def test_unauthorized_project_is_rejected_before_data_queries(monkeypatch):
    service = ProjectService()
    session = MagicMock()
    session.run.return_value = []
    driver = MagicMock()
    driver.session.return_value.__enter__.return_value = session
    user = AuthenticatedUser("user-a", "org-a", "USER", "a@example.test")
    monkeypatch.setattr(service, "ensure_default_project", lambda _: None)
    with patch("application.services.project_service._driver", driver):
        with pytest.raises(Exception, match="Project not found or you do not have access"):
            service.get_project_context(user, "another-org-project")


def test_organization_identity_prefers_explicit_claim_then_stable_user_identity():
    assert _organization_id({"app_metadata": {"organization_id": "acme-workspace"}}, "user-1") == "org:acme-workspace"
    assert _organization_id({"email": "dev@example.com"}, "user-1") == "user:user-1"
