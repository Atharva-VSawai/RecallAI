import hashlib
import logging
from neo4j.exceptions import Neo4jError
from application.services.auth_service import AuthenticatedUser
from domain.exceptions import ConflictError, IngestionError, StorageError, ValidationError
from db.file_registry import _compute_hash, check_file_exists, register_file
from activity_store import activity_store

SUPPORTED_EXTENSIONS = {"pdf": "PDF", "xlsx": "EXCEL", "xls": "EXCEL", "png": "IMAGE", "jpg": "IMAGE", "jpeg": "IMAGE", "gif": "IMAGE", "webp": "IMAGE", "mp3": "AUDIO", "wav": "AUDIO", "m4a": "AUDIO", "flac": "AUDIO", "ogg": "AUDIO", "mp4": "VIDEO", "mov": "VIDEO", "avi": "VIDEO", "mkv": "VIDEO", "webm": "VIDEO"}
logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(self):
        pass

    def ingest_upload(self, content: bytes, filename: str, user: AuthenticatedUser, provider: str) -> dict:
        extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        source_type = SUPPORTED_EXTENSIONS.get(extension)
        if not source_type:
            raise ValidationError("Unsupported file type")
        try:
            content_hash = _compute_hash(content)
            existing = check_file_exists(content_hash)
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
            source_prefix = "image" if source_type == "IMAGE" else "audio" if source_type in {"AUDIO", "VIDEO"} else "document"
            source = f"{source_prefix}:{filename}"
            from ingestion.pipeline import run_ingestion
            result = run_ingestion(content, filename, source, provider=provider)
            register_file(filename, content_hash, extension, source)
            activity_store.add_event("ingest", f"File ingested: {filename}", f"Processed {len(content)} bytes", source, user_id=user.user_id)
            return {"status": "success", "duplicate": False, "result": result, "source": source}
        except Exception as exc:
            logger.exception("Document ingestion failed for %s", filename)
            # Keep the storage/conflict classification intact so the client
            # receives the actionable failure instead of a generic message.
            if isinstance(exc, (ConflictError, IngestionError, StorageError)):
                raise
            if isinstance(exc, Neo4jError):
                raise StorageError(
                    "Neo4j is unavailable. Check NEO4J_URI, Neo4j credentials, and network/DNS connectivity."
                ) from exc
            raise IngestionError(f"The file could not be ingested: {exc}") from exc

    def ingest_slack(self, channel_id: str, limit: int, user: AuthenticatedUser, provider: str) -> dict:
        try:
            from ingestion.slack import fetch_slack_text
            from ingestion.pipeline import run_ingestion_from_text
            raw_text = fetch_slack_text(channel_id, limit)
            source = f"slack:{channel_id}"
            result = run_ingestion_from_text(raw_text, source, provider=provider)
            activity_store.add_event("slack", f"Slack ingestion: #{channel_id}", f"Processed {limit} messages from channel", source, user_id=user.user_id)
            return {"status": "success", "result": result, "source": source}
        except Exception as exc:
            raise IngestionError("Slack ingestion could not be completed") from exc
