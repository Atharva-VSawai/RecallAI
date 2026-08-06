from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.error_handlers import register_exception_handlers
from api.router import api_router
from core.config import settings
from infrastructure.logging import configure_logging
from middleware.request_context import RequestContextMiddleware
import asyncio


configure_logging()
app = FastAPI(title="Recall.AI API", version="1.0.0")

async def _teams_subscription_renewal_loop():
    while True:
        await asyncio.sleep(3600)
        try:
            from application.services.teams_service import TeamsService
            await asyncio.to_thread(TeamsService().renew_subscriptions)
        except Exception:
            # Renewal is best-effort; the next cycle or manual endpoint can retry.
            pass

@app.on_event("startup")
async def start_background_tasks():
    if settings.graph_webhook_url or settings.teams_webhook_url:
        asyncio.create_task(_teams_subscription_renewal_loop())
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
