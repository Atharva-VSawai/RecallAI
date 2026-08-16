import hashlib
import base64
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastapi import BackgroundTasks
from application.services.auth_service import AuthenticatedUser
from application.services.job_service import JobService
from ingestion.job_runner import IngestionJobRunner
from domain.exceptions import ConflictError, IngestionError, StorageError, ValidationError

try:
    from neo4j.exceptions import Neo4jError
except ImportError:
    Neo4jError = None

if TYPE_CHECKING:
    from application.services.project_service import ProjectContext

SUPPORTED_EXTENSIONS = {"pdf": "PDF", "docx": "DOCS", "txt": "DOCS", "md": "DOCS", "markdown": "DOCS", "rtf": "DOCS", "html": "DOCS", "htm": "DOCS", "csv": "DOCS", "log": "DOCS", "xlsx": "EXCEL", "xls": "EXCEL", "png": "IMAGE", "jpg": "IMAGE", "jpeg": "IMAGE", "gif": "IMAGE", "webp": "IMAGE", "mp3": "AUDIO", "wav": "AUDIO", "m4a": "AUDIO", "flac": "AUDIO", "ogg": "AUDIO", "mp4": "VIDEO", "mov": "VIDEO", "avi": "VIDEO", "mkv": "VIDEO", "webm": "VIDEO", "m4v": "VIDEO", "3gp": "VIDEO"}
logger = logging.getLogger(__name__)


def canonical_document_id(source_prefix: str, content_hash: str) -> str:
    """Return a stable content-addressed identity for an uploaded document."""
    return f"{source_prefix}:{content_hash}"



class IngestionService:
    def __init__(self):
        pass

    def ingest_upload(self, background_tasks: BackgroundTasks, content: bytes, filename: str, user: AuthenticatedUser, provider: str, project: "ProjectContext | None" = None) -> dict:
        extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        source_type = SUPPORTED_EXTENSIONS.get(extension)
        if not source_type:
            raise ValidationError("Unsupported file type")
        if not project:
            raise ValueError("Project context is required")
        try:
            content_hash = _compute_hash(content)
            from db.file_registry import check_file_exists, register_file
            existing = check_file_exists(content_hash, project.project_id, project.organization_id)
            if existing:
                # Duplicate detected — return the already-stored file's metadata
                # as a success so the UI treats it like a normal upload.
                # Nothing is re-written to Neo4j or ChromaDB.
                logger.info("Duplicate file detected for %s (hash %s), returning existing record", filename, content_hash[:8])
                return {
                    "status": "success",
                    "duplicate": True,
                    "message": "This file was already uploaded. Using the existing knowledge.",
                    "source": existing.get("source", ""),
                    "result": {"decisions_stored": 0, "note": "duplicate — no new data stored"},
                }
            source_prefix = "image" if source_type == "IMAGE" else "video" if source_type == "VIDEO" else "audio" if source_type == "AUDIO" else "document"
            # Filenames are display metadata, not identity. Content-addressed
            # IDs prevent same-named files from colliding across tenants.
            source = canonical_document_id(source_prefix, content_hash)

            # A previous delete may have soft-deleted the File node while
            # leaving legacy graph/job state behind. Re-adding that exact
            # content must start from a clean source boundary. Active files
            # already returned above as duplicates and are unaffected.
            from db.file_registry import delete_file_by_source
            delete_file_by_source(source, project.project_id, project.organization_id)
            
            # Store durably first
            from infrastructure.repositories.input_store import get_input_store
            store = get_input_store()
            import uuid
            job_id = str(uuid.uuid4())
            try:
                uri, checksum, size = store.store(
                    project.organization_id, 
                    project.project_id, 
                    job_id, 
                    content, 
                    filename, 
                    content_type="application/octet-stream"
                )
                payload_b64 = None
            except Exception as e:
                logger.warning(f"Failed to use durable InputStore, falling back to b64: {e}")
                uri = None
                checksum = None
                size = None
                payload_b64 = base64.b64encode(content).decode("ascii")

            job = JobService().create_job(
                organization_id=project.organization_id,
                project_id=project.project_id,
                user_id=user.user_id,
                source_type=source_type,
                source_id=source,
                input_payload_b64=payload_b64,
                input_uri=uri,
                input_checksum=checksum,
                input_size=size,
                input_filename=filename,
                job_id=job_id,
                source_config={"filename": filename, "display_source": f"{source_prefix}:{filename}", "provider": provider, "document_id": source, "content_hash": content_hash},
            )
            
            runner = IngestionJobRunner(job.job_id, JobService(), project.organization_id)
            background_tasks.add_task(
                runner.process_file_bytes,
                file_bytes=content,
                filename=filename,
                provider=provider,
                store_graph=True,
                store_vector=True,
                project_id=project.project_id,
                organization_id=project.organization_id
            )
            
            from activity_store import activity_store
            activity_store.add_event("ingest", f"File ingestion started: {filename}", f"Processing {len(content)} bytes", source, user_id=user.user_id, project_id=project.project_id, organization_id=project.organization_id)
            return {"status": "success", "duplicate": False, "job_id": job.job_id, "source": source, "project_id": project.project_id}
        except Exception as exc:
            logger.exception("Document ingestion failed for %s", filename)
            # Keep the storage/conflict classification intact so the client
            # receives the actionable failure instead of a generic message.
            if isinstance(exc, (ConflictError, IngestionError, StorageError)):
                raise
            if Neo4jError and isinstance(exc, Neo4jError):
                raise StorageError(
                    "Neo4j is unavailable. Check NEO4J_URI, Neo4j credentials, and network/DNS connectivity."
                ) from exc
            raise IngestionError(f"The file could not be ingested: {exc}") from exc

    def ingest_slack(self, background_tasks: BackgroundTasks, channel_id: str, limit: int, user: AuthenticatedUser, provider: str, project: "ProjectContext | None" = None) -> dict:
        if not project:
            raise ValueError("Project context is required")
        try:
            source = f"slack:{channel_id}"
            
            job = JobService().create_job(
                organization_id=project.organization_id,
                project_id=project.project_id,
                user_id=user.user_id,
                source_type="slack",
                source_id=source,
                source_config={"channel_id": channel_id, "limit": limit, "provider": provider},
            )
            
            from ingestion.slack import SlackIngestionRunner
            runner = SlackIngestionRunner(job.job_id, JobService(), project.organization_id)
            background_tasks.add_task(runner.process_slack_channel, channel_id=channel_id, limit=limit, provider=provider)
            
            from activity_store import activity_store
            activity_store.add_event("slack", f"Slack ingestion started: #{channel_id}", f"Fetching messages", source, user_id=user.user_id, project_id=project.project_id, organization_id=project.organization_id)
            return {"status": "success", "job_id": job.job_id, "source": source, "project_id": project.project_id}
        except Exception as exc:
            raise IngestionError("Slack ingestion could not be completed") from exc


def _compute_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()
