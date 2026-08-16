"""Low-dependency cost, metrics, resilience, and cache primitives.

The in-process store is intentionally bounded and safe to use when the
analytics database is unavailable. Deployments can replace the store with a
durable adapter without changing callers.
"""
from __future__ import annotations

import hashlib
import threading
import time
from collections import Counter, deque
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Callable

from core.config import settings
from domain.exceptions import RateLimitError


_scope: ContextVar[dict[str, str]] = ContextVar("usage_scope", default={})


@contextmanager
def usage_scope(**values: str | None):
    token = _scope.set({key: str(value) for key, value in values.items() if value})
    try:
        yield
    finally:
        _scope.reset(token)


def current_scope() -> dict[str, str]:
    return dict(_scope.get())


def _cost(provider: str, kind: str, units: int, unit_cost: float | None = None) -> float:
    if unit_cost is not None:
        return max(0.0, units * unit_cost)
    rates = {
        "llm": {"groq": settings.groq_cost_per_1k_tokens, "ollama": 0.0},
        "embedding": {"cohere": settings.cohere_cost_per_1k_tokens},
        "transcription": {"groq": settings.groq_transcription_cost_per_minute},
    }
    divisor = 1000 if kind in {"llm", "embedding"} else 1
    return max(0.0, units / divisor * rates.get(kind, {}).get(provider, 0.0))


class BudgetExceeded(RateLimitError):
    """Raised before a billable operation when a project/user budget is hit."""


class ObservabilityStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._usage: deque[dict[str, Any]] = deque(maxlen=10000)
        self._events: deque[dict[str, Any]] = deque(maxlen=10000)
        self._budgets: dict[tuple[str, str], dict[str, float]] = {}
        self._cache: dict[str, tuple[float, Any]] = {}

    def set_budget(self, project_id: str, user_id: str | None, limits: dict[str, float]) -> dict[str, Any]:
        key = (project_id, user_id or "*")
        with self._lock:
            self._budgets[key] = {name: float(value) for name, value in limits.items() if value is not None}
            return {"project_id": project_id, "user_id": user_id, "limits": dict(self._budgets[key])}

    def _spent(self, project_id: str, user_id: str | None) -> float:
        return sum(float(item.get("cost", 0)) for item in self._usage if item.get("project_id") == project_id and (not user_id or item.get("user_id") in {user_id, None}))

    def check_budget(self, project_id: str | None, user_id: str | None, estimated_cost: float = 0.0) -> None:
        if not project_id:
            return
        with self._lock:
            limits = [self._budgets.get((project_id, "*")), self._budgets.get((project_id, user_id or ""))]
            spent = self._spent(project_id, user_id)
            for budget in limits:
                if budget and budget.get("cost", float("inf")) < spent + estimated_cost:
                    raise BudgetExceeded("Usage budget exceeded for this project or user")

    def record_usage(self, kind: str, provider: str, units: int = 0, cost: float | None = None, **metadata: Any) -> dict[str, Any]:
        scope = current_scope()
        item = {
            "kind": kind, "provider": provider, "units": int(max(0, units)),
            "cost": _cost(provider, kind, int(max(0, units)), cost),
            "timestamp": time.time(), **scope, **metadata,
        }
        with self._lock:
            self._usage.append(item)
        self._persist("usage_events", {
            "organization_id": item.get("organization_id", "unknown"),
            "project_id": item.get("project_id", "unknown"), "user_id": item.get("user_id"),
            "kind": kind, "provider": provider, "units": item["units"], "cost": item["cost"],
            "metadata": metadata,
        })
        return item

    def metric(self, name: str, value: float = 1.0, **metadata: Any) -> None:
        with self._lock:
            self._events.append({"name": name, "value": value, "timestamp": time.time(), **current_scope(), **metadata})
        self._persist("operational_metrics", {"organization_id": current_scope().get("organization_id"), "project_id": current_scope().get("project_id"), "user_id": current_scope().get("user_id"), "name": name, "value": value, "metadata": metadata})

    @staticmethod
    def _persist(table: str, payload: dict[str, Any]) -> None:
        if not settings.supabase_url or not settings.supabase_service_role_key:
            return
        try:
            from db.supabase_client import supabase
            supabase.table(table).insert(payload).execute()
        except Exception:
            # Telemetry must never take down a user request.
            return

    def snapshot(self, project_id: str | None = None) -> dict[str, Any]:
        with self._lock:
            usage = [item for item in self._usage if not project_id or item.get("project_id") == project_id]
            events = [item for item in self._events if not project_id or item.get("project_id") == project_id]
        by_kind = Counter(item["kind"] for item in usage)
        by_provider = Counter(item["provider"] for item in usage)
        metric_counts = Counter(item["name"] for item in events)
        return {"usage": {"events": len(usage), "total_cost": round(sum(item["cost"] for item in usage), 8), "by_kind": dict(by_kind), "by_provider": dict(by_provider)}, "metrics": dict(metric_counts), "recent_usage": usage[-50:]}

    def cache_get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._cache.get(key)
            if not entry or entry[0] <= time.time():
                self._cache.pop(key, None)
                return None
            self.metric("query_cache_hit")
            return entry[1]

    def cache_set(self, key: str, value: Any, ttl: int) -> None:
        with self._lock:
            if len(self._cache) >= settings.query_cache_max_entries:
                self._cache.pop(next(iter(self._cache)))
            self._cache[key] = (time.time() + ttl, value)


store = ObservabilityStore()


@dataclass
class CircuitBreaker:
    name: str
    failure_threshold: int = 3
    recovery_seconds: int = 30
    failures: int = 0
    opened_at: float | None = None

    def allow(self) -> bool:
        if self.opened_at is None:
            return True
        if time.time() - self.opened_at >= self.recovery_seconds:
            self.opened_at = None
            self.failures = 0
            return True
        return False

    def success(self) -> None:
        self.failures = 0
        self.opened_at = None

    def failure(self) -> None:
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.opened_at = time.time()

    def call(self, operation: Callable[[], Any]) -> Any:
        if not self.allow():
            store.metric("provider_circuit_open", provider=self.name)
            raise RuntimeError(f"Provider circuit is open: {self.name}")
        try:
            result = operation()
            self.success()
            return result
        except Exception:
            self.failure()
            store.metric("provider_failure", provider=self.name)
            raise


breakers = {name: CircuitBreaker(name) for name in ("groq", "ollama", "cohere", "neo4j", "chroma")}


def cache_key(question: str, organization_id: str, project_id: str, user_id: str | None, provider: str, source_filter: str | None) -> str:
    raw = "|".join([organization_id, project_id, user_id or "", provider, source_filter or "", " ".join(question.lower().split())])
    return hashlib.sha256(raw.encode()).hexdigest()
