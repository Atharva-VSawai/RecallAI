import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from application.services.observability_service import BudgetExceeded, CircuitBreaker, ObservabilityStore, cache_key


def test_cache_key_is_tenant_user_and_provider_scoped():
    assert cache_key("  What happened? ", "org-a", "project-a", "user-a", "groq", None) != cache_key("What happened?", "org-b", "project-a", "user-a", "groq", None)
    assert cache_key("What happened?", "org-a", "project-a", "user-a", "groq", None) == cache_key(" what   happened? ", "org-a", "project-a", "user-a", "groq", None)


def test_budget_blocks_before_usage_is_recorded():
    store = ObservabilityStore()
    store.set_budget("project-a", "user-a", {"cost": 1})
    store.record_usage("llm", "groq", units=1, cost=1, project_id="project-a", user_id="user-a")
    with pytest.raises(BudgetExceeded):
        store.check_budget("project-a", "user-a", estimated_cost=0.01)


def test_circuit_breaker_opens_and_recovers():
    breaker = CircuitBreaker("test", failure_threshold=2, recovery_seconds=0)
    for _ in range(2):
        with pytest.raises(RuntimeError):
            breaker.call(lambda: (_ for _ in ()).throw(RuntimeError("down")))
    assert breaker.allow()
    assert breaker.call(lambda: "ok") == "ok"


def test_dashboard_and_alerts_are_scoped_to_project(monkeypatch):
    from api.routes.observability_routes import alerts, dashboard
    from application.services.project_service import ProjectContext
    from application.services.observability_service import store

    store._usage.clear()
    store._events.clear()
    project = ProjectContext("project-a", "org-a", "Project A", "project-a", "OWNER", ("project:read",))
    store.metric("query_started", project_id="project-a")
    store.metric("query_failed", project_id="project-a")
    result = dashboard(project)
    assert result["project_id"] == "project-a"
    assert result["metrics"]["query_failed"] == 1
    assert alerts(project)["status"] == "alert"
