from enum import Enum
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    STALE = "STALE"


class JobStage(str, Enum):
    VALIDATE = "VALIDATE"
    REGISTER_SOURCE = "REGISTER_SOURCE"
    EXTRACT_TEXT = "EXTRACT_TEXT"
    CHUNK = "CHUNK"
    EMBED = "EMBED"
    STORE_SEMANTIC_MEMORY = "STORE_SEMANTIC_MEMORY"
    EXTRACT_STRUCTURED_KNOWLEDGE = "EXTRACT_STRUCTURED_KNOWLEDGE"
    WRITE_KNOWLEDGE_GRAPH = "WRITE_KNOWLEDGE_GRAPH"
    FINALIZE = "FINALIZE"


class IngestionJob(BaseModel):
    job_id: str
    organization_id: str
    project_id: str
    user_id: str
    source_type: str
    source_id: str
    # Durable reconstruction data.
    input_payload_b64: Optional[str] = None
    input_uri: Optional[str] = None
    input_checksum: Optional[str] = None
    input_size: Optional[int] = None
    input_content_type: Optional[str] = None
    input_filename: Optional[str] = None
    
    source_config: Dict[str, Any] = Field(default_factory=dict)
    status: JobStatus = JobStatus.QUEUED
    current_stage: Optional[JobStage] = None
    progress: float = 0.0
    total_units: int = 0
    completed_units: int = 0
    error_message: Optional[str] = None
    retry_count: int = 0
    
    # Lease mechanism
    lease_owner: Optional[str] = None
    lease_until: Optional[int] = None
    version: int = 0
    attempt: int = 0
    checkpoint_sequence: int = 0

    # State for checkpointing (e.g. which chunks are completed)
    checkpoint_state: Dict[str, Any] = Field(default_factory=dict)

    created_at: int
    started_at: Optional[int] = None
    updated_at: Optional[int] = None
    completed_at: Optional[int] = None
    failed_at: Optional[int] = None
