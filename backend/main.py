from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.error_handlers import register_exception_handlers
from api.router import api_router
from core.config import settings
from infrastructure.logging import configure_logging
from middleware.request_context import RequestContextMiddleware
import asyncio
import logging


configure_logging()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    from db.neo import close_driver, ensure_search_indexes, init_driver
    driver = init_driver()
    renewal_task = None
    try:
        await asyncio.to_thread(driver.verify_connectivity)
        await asyncio.to_thread(ensure_search_indexes)
        logging.getLogger(__name__).info("neo4j.startup.connected")
    except Exception:
        logging.getLogger(__name__).exception("neo4j.startup.connectivity_check_failed")
    if settings.graph_webhook_url or settings.teams_webhook_url:
        renewal_task = asyncio.create_task(_teams_subscription_renewal_loop())
    try:
        yield
    finally:
        if renewal_task:
            renewal_task.cancel()
            await asyncio.gather(renewal_task, return_exceptions=True)
        close_driver()


app = FastAPI(title="Recall.AI API", version="1.0.0", lifespan=lifespan)

async def _teams_subscription_renewal_loop():
    while True:
        await asyncio.sleep(3600)
        try:
            from application.services.teams_service import TeamsService
            await asyncio.to_thread(TeamsService().renew_subscriptions)
        except Exception:
            # Renewal is best-effort; the next cycle or manual endpoint can retry.
            pass

app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    # Local development is commonly opened as either localhost or 127.0.0.1,
    # and Next.js may use a different port during development.
    # Next.js may be opened through localhost, IPv4 loopback, or IPv6
    # loopback (`http://[::1]:3000`). Browsers surface a rejected CORS
    # preflight as the misleading generic `Failed to fetch` error.
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|\[::1\]|0\.0\.0\.0)(:\d+)?$",
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-LLM-Provider", "X-Project-ID", "X-Request-ID"],
)
register_exception_handlers(app)
app.include_router(api_router)
