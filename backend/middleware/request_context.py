import contextvars
import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

request_id_context: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        token = request_id_context.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            request.state.duration_ms = round((time.perf_counter() - started) * 1000, 2)
            request_id_context.reset(token)
