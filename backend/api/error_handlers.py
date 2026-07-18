import logging
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from neo4j.exceptions import Neo4jError, ServiceUnavailable
from domain.exceptions import DomainError
from middleware.request_context import request_id_context

logger = logging.getLogger(__name__)


def _error(code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": {
        "code": code, "message": message, "request_id": request_id_context.get(),
    }})


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error_handler(_: Request, exc: DomainError):
        return _error(exc.code, exc.message, exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError):
        return _error("VALIDATION_ERROR", "Invalid request data", 422)

    @app.exception_handler(ServiceUnavailable)
    async def neo4j_unavailable_handler(_: Request, exc: ServiceUnavailable):
        logger.exception("Neo4j is unavailable")
        return _error(
            "STORAGE_UNAVAILABLE",
            "Neo4j is unavailable. Check NEO4J_URI, Neo4j credentials, and network/DNS connectivity.",
            503,
        )

    @app.exception_handler(Neo4jError)
    async def neo4j_error_handler(_: Request, exc: Neo4jError):
        logger.exception("Neo4j request failed")
        return _error("STORAGE_ERROR", "Neo4j could not complete the request.", 503)

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_: Request, exc: Exception):
        logger.exception("Unhandled API error")
        return _error("INTERNAL_ERROR", "An unexpected error occurred", 500)
