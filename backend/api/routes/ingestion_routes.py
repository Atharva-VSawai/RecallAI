from fastapi import APIRouter, Depends, File, Header, UploadFile
from fastapi.concurrency import run_in_threadpool
from application.services.auth_service import AuthenticatedUser
from application.services.ingestion_service import IngestionService
from api.dependencies import get_current_user
from core.config import settings
from domain.exceptions import ValidationError
from schemas.requests import SlackIngestRequest

router = APIRouter(prefix="/ingest", tags=["ingestion"])

@router.post("/upload")
async def upload(file: UploadFile = File(...), user: AuthenticatedUser = Depends(get_current_user), x_llm_provider: str = Header(default="groq")):
    content = await file.read()
    if len(content) > settings.max_upload_size_bytes:
        raise ValidationError("Uploaded file exceeds the configured size limit")
    return await run_in_threadpool(IngestionService().ingest_upload, content, file.filename or "unknown", user, x_llm_provider)

@router.post("/slack")
async def slack(request: SlackIngestRequest, user: AuthenticatedUser = Depends(get_current_user), x_llm_provider: str = Header(default="groq")):
    return await run_in_threadpool(IngestionService().ingest_slack, request.channel_id, request.limit, user, x_llm_provider)


@router.post("/audio")
async def audio(file: UploadFile = File(...), user: AuthenticatedUser = Depends(get_current_user), x_llm_provider: str = Header(default="groq")):
    """Compatibility endpoint; audio is processed by the universal ingestion service."""
    return await upload(file, user, x_llm_provider)


@router.post("/image")
async def image(file: UploadFile = File(...), user: AuthenticatedUser = Depends(get_current_user), x_llm_provider: str = Header(default="groq")):
    """Compatibility endpoint; image OCR is handled by the universal ingestion service."""
    return await upload(file, user, x_llm_provider)
