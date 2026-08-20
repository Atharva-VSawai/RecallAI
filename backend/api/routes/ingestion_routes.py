import base64
from fastapi import APIRouter, Depends, File, Header, UploadFile, BackgroundTasks, HTTPException
from application.services.auth_service import AuthenticatedUser
from application.services.ingestion_service import IngestionService
from application.services.job_service import JobService
from api.dependencies import get_current_user
from api.dependencies import require_project_permission
from api.rate_limit import INGEST_LIMIT, require_rate_limit
from core.config import settings
from domain.exceptions import ValidationError
from domain.exceptions import AuthorizationError
from application.services.project_service import ProjectContext
from application.services.project_service import ProjectService
from schemas.requests import SlackIngestRequest

router = APIRouter(prefix="/ingest", tags=["ingestion"])

def _authorize_job(job_id: str, user: AuthenticatedUser, project_id: str | None = None):
    service = JobService()
    try:
        job = service.get_job(job_id, user.organization_id)
    except TypeError:
        # Compatibility for legacy repository adapters that have not yet
        # adopted the scoped signature; the checks below still enforce scope.
        job = service.get_job(job_id)
    if not job or job.user_id != user.user_id or job.organization_id != user.organization_id:
        raise AuthorizationError("You do not have access to this ingestion job")
    try:
        project = ProjectService().get_project_context(user, project_id or job.project_id)
    except Exception as exc:
        raise AuthorizationError("You do not have access to this ingestion job") from exc
    if project.project_id != job.project_id or project.organization_id != job.organization_id:
        raise AuthorizationError("You do not have access to this ingestion job")
    return job

def _dispatch_job(job, background_tasks: BackgroundTasks):
    service = JobService()
    if job.source_type in {"PDF", "DOCS", "EXCEL", "IMAGE", "AUDIO", "VIDEO"}:
        if not job.input_payload_b64 and not job.input_uri:
            raise ValidationError("This job has no durable input and cannot be retried")
        from ingestion.job_runner import IngestionJobRunner
        file_bytes = base64.b64decode(job.input_payload_b64) if job.input_payload_b64 else None
        background_tasks.add_task(IngestionJobRunner(job.job_id, service, job.organization_id).process_file_bytes, file_bytes=file_bytes, filename=job.source_config.get("filename", job.source_id), provider=job.source_config.get("provider", "groq"))
    elif job.source_type == "slack":
        from ingestion.slack import SlackIngestionRunner
        background_tasks.add_task(SlackIngestionRunner(job.job_id, service, job.organization_id).process_slack_channel, channel_id=job.source_config["channel_id"], limit=int(job.source_config.get("limit", 100)), provider=job.source_config.get("provider", "groq"))
    elif job.source_type == "teams_sync":
        from ingestion.teams import TeamsSyncRunner
        background_tasks.add_task(TeamsSyncRunner(job.job_id, service, job.organization_id).process_teams_sync, project_id=job.project_id, organization_id=job.organization_id, user_id=job.user_id, provider=job.source_config.get("provider", "groq"))
    else:
        raise ValidationError("Unsupported ingestion job type")

@router.post("/upload")
async def upload(background_tasks: BackgroundTasks, file: UploadFile = File(...), user: AuthenticatedUser = Depends(get_current_user), project: ProjectContext = Depends(require_project_permission("knowledge:write")), _: None = Depends(require_rate_limit("ingest-upload", INGEST_LIMIT)), x_llm_provider: str = Header(default="groq")):
    content = await file.read()
    if len(content) > settings.max_upload_size_bytes:
        raise ValidationError("Uploaded file exceeds the configured size limit")
    return IngestionService().ingest_upload(background_tasks, content, file.filename or "unknown", user, x_llm_provider, project)

@router.post("/slack")
async def slack(background_tasks: BackgroundTasks, request: SlackIngestRequest, user: AuthenticatedUser = Depends(get_current_user), project: ProjectContext = Depends(require_project_permission("knowledge:write")), _: None = Depends(require_rate_limit("ingest-slack", INGEST_LIMIT)), x_llm_provider: str = Header(default="groq")):
    return IngestionService().ingest_slack(background_tasks, request.channel_id, request.limit, user, x_llm_provider, project)


@router.post("/audio")
async def audio(background_tasks: BackgroundTasks, file: UploadFile = File(...), user: AuthenticatedUser = Depends(get_current_user), project: ProjectContext = Depends(require_project_permission("knowledge:write")), x_llm_provider: str = Header(default="groq")):
    """Compatibility endpoint; audio is processed by the universal ingestion service."""
    return await upload(background_tasks=background_tasks, file=file, user=user, project=project, x_llm_provider=x_llm_provider)


@router.post("/image")
async def image(background_tasks: BackgroundTasks, file: UploadFile = File(...), user: AuthenticatedUser = Depends(get_current_user), project: ProjectContext = Depends(require_project_permission("knowledge:write")), x_llm_provider: str = Header(default="groq")):
    """Compatibility endpoint; image OCR is handled by the universal ingestion service."""
    return await upload(background_tasks=background_tasks, file=file, user=user, project=project, x_llm_provider=x_llm_provider)

@router.get("/status/{job_id}")
async def get_job_status(job_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    job = _authorize_job(job_id, user)
    return job.model_dump()

@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    _authorize_job(job_id, user)
    cancelled = JobService().cancel_job(job_id, user.organization_id)
    return {"status": "success" if cancelled else "error", "cancelled": cancelled}

@router.post("/{job_id}/retry")
async def retry_job(job_id: str, background_tasks: BackgroundTasks, user: AuthenticatedUser = Depends(get_current_user)):
    job_service = JobService()
    _authorize_job(job_id, user)
    if job_service.retry_job(job_id, user.organization_id):
        job = job_service.get_job(job_id, user.organization_id)
        _dispatch_job(job, background_tasks)
        return {"status": "success", "job_id": job_id, "job_status": job.status.value}
    raise HTTPException(status_code=409, detail="Job cannot be retried")
