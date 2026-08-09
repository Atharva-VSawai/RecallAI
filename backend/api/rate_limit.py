"""Small process-local limiter for the LLM-backed API surface.

This intentionally keeps Phase 1 infrastructure-free.  Limits are keyed by
the authenticated user and authorized project, rather than by an untrusted
client address.  Deployments with multiple API workers need a shared limiter
in the next architecture phase.
"""

from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
from time import monotonic

from fastapi import Depends, Request

from api.dependencies import get_current_user, get_project_context
from application.services.auth_service import AuthenticatedUser
from application.services.project_service import ProjectContext
from domain.exceptions import RateLimitError


@dataclass(frozen=True)
class Limit:
    requests: int
    window_seconds: int


class UserProjectRateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, bucket: str, user_id: str, project_id: str, limit: Limit, *, now: float | None = None) -> None:
        current = monotonic() if now is None else now
        key = f"{bucket}:{user_id}:{project_id}"
        with self._lock:
            hits = self._hits[key]
            cutoff = current - limit.window_seconds
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if len(hits) >= limit.requests:
                raise RateLimitError("Too many requests. Please try again shortly.")
            hits.append(current)


rate_limiter = UserProjectRateLimiter()


def require_rate_limit(bucket: str, limit: Limit):
    """Create a dependency that runs only after project membership resolves."""
    def dependency(
        _request: Request,
        user: AuthenticatedUser = Depends(get_current_user),
        project: ProjectContext = Depends(get_project_context),
    ) -> None:
        rate_limiter.check(bucket, user.user_id, project.project_id, limit)

    return dependency


QUERY_LIMIT = Limit(requests=10, window_seconds=60)
INGEST_LIMIT = Limit(requests=5, window_seconds=60)
TEAMS_SYNC_LIMIT = Limit(requests=5, window_seconds=60)
