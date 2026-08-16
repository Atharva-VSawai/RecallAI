import time
import uuid
import logging
from typing import Optional, List, Dict, Any

from domain.job import IngestionJob, JobStatus, JobStage
from infrastructure.repositories.job_repository import JobRepository, Neo4jJobRepository

logger = logging.getLogger(__name__)

class JobService:
    def __init__(self, repository: JobRepository = None):
        self.repository = repository or Neo4jJobRepository()

    def create_job(
        self,
        organization_id: str,
        project_id: str,
        user_id: str,
        source_type: str,
        source_id: str,
        input_payload_b64: Optional[str] = None,
        source_config: Optional[Dict[str, Any]] = None,
        input_uri: Optional[str] = None,
        input_checksum: Optional[str] = None,
        input_size: Optional[int] = None,
        input_content_type: Optional[str] = None,
        input_filename: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> IngestionJob:
        job = IngestionJob(
            job_id=job_id or str(uuid.uuid4()),
            organization_id=organization_id,
            project_id=project_id,
            user_id=user_id,
            source_type=source_type,
            source_id=source_id,
            input_payload_b64=input_payload_b64,
            input_uri=input_uri,
            input_checksum=input_checksum,
            input_size=input_size,
            input_content_type=input_content_type,
            input_filename=input_filename,
            source_config=source_config or {},
            status=JobStatus.QUEUED,
            created_at=int(time.time()),
            updated_at=int(time.time())
        )
        self.repository.create_job(job)
        return job

    def get_job(self, job_id: str, organization_id: Optional[str] = None) -> Optional[IngestionJob]:
        return self.repository.get_job(job_id, organization_id)

    def mark_started(self, job_id: str, worker_id: str, lease_seconds: int = 300, organization_id: str | None = None) -> bool:
        """
        Attempts to atomically claim a job. Returns True if successful.
        """
        if self.repository.claim_job(job_id, worker_id, lease_seconds):
            job = self.get_job(job_id, organization_id) if organization_id else None
            if job and not job.current_stage:
                job.current_stage = JobStage.VALIDATE
                self.repository.update_job(job, expected_version=job.version)
            return True
        return False

    def mark_completed(self, job_id: str, worker_id: str, expected_version: int) -> None:
        self.repository.complete_job(job_id, worker_id, expected_version)

    def mark_failed(self, job_id: str, worker_id: str, expected_version: int, error_message: str) -> None:
        self.repository.fail_job(job_id, worker_id, expected_version, error_message)

    def update_progress(
        self,
        job_id: str,
        expected_version: int,
        worker_id: str,
        stage: Optional[JobStage] = None,
        progress: Optional[float] = None,
        completed_units: Optional[int] = None,
        total_units: Optional[int] = None,
        checkpoint_state: Optional[dict] = None,
        lease_seconds: int = 300
    ) -> bool:
        job = self.get_job(job_id)
        if not job:
            return False
        
        # Verify ownership
        if job.lease_owner != worker_id or job.version != expected_version:
            logger.warning(f"Worker {worker_id} (version {expected_version}) tried to update job {job_id} but it is owned by {job.lease_owner} (version {job.version})")
            return False

        if stage:
            job.current_stage = stage
        if progress is not None:
            job.progress = progress
        if completed_units is not None:
            job.completed_units = completed_units
        if total_units is not None:
            job.total_units = total_units
        if checkpoint_state is not None:
            job.checkpoint_state.update(checkpoint_state)
        
        job.lease_until = int(time.time()) + lease_seconds
        job.updated_at = int(time.time())
        return self.repository.update_job(job, expected_version=expected_version)

    def cancel_job(self, job_id: str, organization_id: str | None = None) -> bool:
        statuses = [JobStatus.QUEUED, JobStatus.PROCESSING, JobStatus.STALE]
        changed = self.repository.transition(job_id, statuses, JobStatus.CANCELLED, organization_id) if organization_id else self.repository.transition(job_id, statuses, JobStatus.CANCELLED)
        if changed:
            job = self.get_job(job_id, organization_id)
            if job:
                job.updated_at = int(time.time())
                self.repository.update_job(job)
        return changed

    def reclaim_expired_leases(self) -> int:
        """
        Reclaims PROCESSING jobs whose leases have expired.
        Transitions them to STALE so they can be re-QUEUED.
        """
        stale_jobs = self.repository.get_reclaimable_jobs()
        reclaimed_count = 0
        for job in stale_jobs:
            if self.repository.transition(job.job_id, [JobStatus.PROCESSING], JobStatus.STALE):
                logger.warning(f"Job {job.job_id} lease expired. Marked as STALE.")
                reclaimed_count += 1
        return reclaimed_count
        
    def check_stale_jobs(self, timeout_seconds: int = 300) -> int:
        """Legacy compatibility wrapper for older routines."""
        return self.reclaim_expired_leases()

    def retry_job(self, job_id: str, organization_id: str | None = None) -> bool:
        """
        Sets a FAILED or STALE job back to QUEUED.
        """
        job = self.get_job(job_id, organization_id)
        if not job or job.status not in [JobStatus.FAILED, JobStatus.STALE]:
            return False
        statuses = [JobStatus.FAILED, JobStatus.STALE]
        changed = self.repository.transition(job_id, statuses, JobStatus.QUEUED, organization_id) if organization_id else self.repository.transition(job_id, statuses, JobStatus.QUEUED)
        if not changed:
            return False
        job.status = JobStatus.QUEUED
        job.retry_count += 1
        job.error_message = None
        job.lease_owner = None
        job.lease_until = None
        job.current_stage = None
        if job.input_uri and job.input_payload_b64:
            job.input_payload_b64 = None
        job.updated_at = int(time.time())
        self.repository.update_job(job)
        return True
