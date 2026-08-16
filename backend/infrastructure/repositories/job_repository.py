import json
import time
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any

from domain.job import IngestionJob, JobStatus, JobStage
from db.neo import _driver

class JobRepository(ABC):
    @abstractmethod
    def create_job(self, job: IngestionJob) -> None:
        pass

    @abstractmethod
    def get_job(self, job_id: str, organization_id: str) -> Optional[IngestionJob]:
        pass

    @abstractmethod
    def update_job(self, job: IngestionJob, expected_version: Optional[int] = None) -> bool:
        pass

    @abstractmethod
    def get_stale_jobs(self, timeout_seconds: int) -> List[IngestionJob]:
        pass

    @abstractmethod
    def get_reclaimable_jobs(self) -> List[IngestionJob]:
        pass

    @abstractmethod
    def transition(self, job_id: str, from_statuses: List[JobStatus], to_status: JobStatus, organization_id: Optional[str] = None) -> bool:
        pass

    @abstractmethod
    def claim_job(self, job_id: str, worker_id: str, lease_seconds: int) -> bool:
        pass

    @abstractmethod
    def release_lease(self, job_id: str, worker_id: str) -> bool:
        pass

    @abstractmethod
    def complete_job(self, job_id: str, worker_id: str, expected_version: int) -> bool:
        pass

    @abstractmethod
    def fail_job(self, job_id: str, worker_id: str, expected_version: int, error_message: str) -> bool:
        pass


class Neo4jJobRepository(JobRepository):
    """
    Neo4j is being used for job persistence in Phase 2 because the
    current project does not yet have a database migration workflow for
    Supabase/Postgres.
    """
    def create_job(self, job: IngestionJob) -> None:
        with _driver.session() as session:
            session.run("""
                CREATE (j:IngestionJob {
                    job_id: $job_id,
                    organization_id: $organization_id,
                    project_id: $project_id,
                    user_id: $user_id,
                    source_type: $source_type,
                    source_id: $source_id,
                    input_payload_b64: $input_payload_b64,
                    input_uri: $input_uri,
                    input_checksum: $input_checksum,
                    input_size: $input_size,
                    input_content_type: $input_content_type,
                    input_filename: $input_filename,
                    source_config: $source_config,
                    status: $status,
                    current_stage: $current_stage,
                    progress: $progress,
                    total_units: $total_units,
                    completed_units: $completed_units,
                    error_message: $error_message,
                    retry_count: $retry_count,
                    checkpoint_state: $checkpoint_state,
                    lease_owner: $lease_owner,
                    lease_until: $lease_until,
                    version: $version,
                    attempt: $attempt,
                    checkpoint_sequence: $checkpoint_sequence,
                    created_at: $created_at,
                    started_at: $started_at,
                    updated_at: $updated_at,
                    completed_at: $completed_at,
                    failed_at: $failed_at
                })
            """,
                job_id=job.job_id,
                organization_id=job.organization_id,
                project_id=job.project_id,
                user_id=job.user_id,
                source_type=job.source_type,
                source_id=job.source_id,
                input_payload_b64=job.input_payload_b64,
                input_uri=job.input_uri,
                input_checksum=job.input_checksum,
                input_size=job.input_size,
                input_content_type=job.input_content_type,
                input_filename=job.input_filename,
                source_config=json.dumps(job.source_config),
                status=job.status.value,
                current_stage=job.current_stage.value if job.current_stage else None,
                progress=job.progress,
                total_units=job.total_units,
                completed_units=job.completed_units,
                error_message=job.error_message,
                retry_count=job.retry_count,
                checkpoint_state=json.dumps(job.checkpoint_state),
                lease_owner=job.lease_owner,
                lease_until=job.lease_until,
                version=job.version,
                attempt=job.attempt,
                checkpoint_sequence=job.checkpoint_sequence,
                created_at=job.created_at,
                started_at=job.started_at,
                updated_at=job.updated_at,
                completed_at=job.completed_at,
                failed_at=job.failed_at
            )

    def _dict_to_job(self, data: Dict[str, Any]) -> IngestionJob:
        return IngestionJob(
            job_id=data["job_id"],
            organization_id=data.get("organization_id", "_quarantined"),
            project_id=data.get("project_id", ""),
            user_id=data.get("user_id", ""),
            source_type=data.get("source_type", ""),
            source_id=data.get("source_id", ""),
            input_payload_b64=data.get("input_payload_b64"),
            input_uri=data.get("input_uri"),
            input_checksum=data.get("input_checksum"),
            input_size=data.get("input_size"),
            input_content_type=data.get("input_content_type"),
            input_filename=data.get("input_filename"),
            source_config=json.loads(data.get("source_config") or "{}") if isinstance(data.get("source_config") or "{}", str) else data.get("source_config", {}),
            status=JobStatus(data["status"]),
            current_stage=JobStage(data["current_stage"]) if data.get("current_stage") else None,
            progress=data.get("progress", 0.0),
            total_units=data.get("total_units", 0),
            completed_units=data.get("completed_units", 0),
            error_message=data.get("error_message"),
            retry_count=data.get("retry_count", 0),
            checkpoint_state=json.loads(data.get("checkpoint_state") or "{}") if isinstance(data.get("checkpoint_state") or "{}", str) else data.get("checkpoint_state", {}),
            lease_owner=data.get("lease_owner"),
            lease_until=data.get("lease_until"),
            version=data.get("version", 0),
            attempt=data.get("attempt", 0),
            checkpoint_sequence=data.get("checkpoint_sequence", 0),
            created_at=data.get("created_at", int(time.time())),
            started_at=data.get("started_at"),
            updated_at=data.get("updated_at"),
            completed_at=data.get("completed_at"),
            failed_at=data.get("failed_at")
        )

    def get_job(self, job_id: str, organization_id: Optional[str] = None) -> Optional[IngestionJob]:
        with _driver.session() as session:
            query = "MATCH (j:IngestionJob {job_id: $job_id}) "
            if organization_id:
                query += "WHERE j.organization_id = $organization_id "
            query += "RETURN j"
            result = session.run(query, job_id=job_id, organization_id=organization_id).single()
            if not result:
                return None
            return self._dict_to_job(dict(result["j"]))

    def update_job(self, job: IngestionJob, expected_version: Optional[int] = None) -> bool:
        with _driver.session() as session:
            query = """
                MATCH (j:IngestionJob {job_id: $job_id})
                WHERE j.status = $status
            """
            if expected_version is not None:
                query += "  AND j.version = $expected_version "
                
            query += """
                SET j.status = $status,
                    j.current_stage = $current_stage,
                    j.progress = $progress,
                    j.total_units = $total_units,
                    j.completed_units = $completed_units,
                    j.error_message = $error_message,
                    j.retry_count = $retry_count,
                    j.input_payload_b64 = $input_payload_b64,
                    j.input_uri = $input_uri,
                    j.input_checksum = $input_checksum,
                    j.input_size = $input_size,
                    j.input_content_type = $input_content_type,
                    j.input_filename = $input_filename,
                    j.source_config = $source_config,
                    j.checkpoint_state = $checkpoint_state,
                    j.lease_owner = $lease_owner,
                    j.lease_until = $lease_until,
                    j.version = coalesce(j.version, 0) + 1,
                    j.attempt = $attempt,
                    j.checkpoint_sequence = $checkpoint_sequence,
                    j.updated_at = $updated_at,
                    j.started_at = $started_at,
                    j.completed_at = $completed_at,
                    j.failed_at = $failed_at
                RETURN count(j) AS changed
            """
            result = session.run(
                query,
                job_id=job.job_id,
                status=job.status.value,
                expected_version=expected_version,
                current_stage=job.current_stage.value if job.current_stage else None,
                progress=job.progress,
                total_units=job.total_units,
                completed_units=job.completed_units,
                error_message=job.error_message,
                retry_count=job.retry_count,
                input_payload_b64=job.input_payload_b64,
                input_uri=job.input_uri,
                input_checksum=job.input_checksum,
                input_size=job.input_size,
                input_content_type=job.input_content_type,
                input_filename=job.input_filename,
                source_config=json.dumps(job.source_config),
                checkpoint_state=json.dumps(job.checkpoint_state),
                lease_owner=job.lease_owner,
                lease_until=job.lease_until,
                attempt=job.attempt,
                checkpoint_sequence=job.checkpoint_sequence,
                updated_at=job.updated_at,
                started_at=job.started_at,
                completed_at=job.completed_at,
                failed_at=job.failed_at
            ).single()
            return bool(result and result["changed"])

    def claim_job(self, job_id: str, worker_id: str, lease_seconds: int) -> bool:
        now = int(time.time())
        lease_until = now + lease_seconds
        with _driver.session() as session:
            result = session.run(
                """
                MATCH (j:IngestionJob {job_id: $job_id})
                WHERE j.status IN ['QUEUED', 'STALE'] AND (j.lease_until IS NULL OR j.lease_until < $now)
                SET j.status = 'PROCESSING',
                    j.lease_owner = $worker_id,
                    j.lease_until = $lease_until,
                    j.version = coalesce(j.version, 0) + 1,
                    j.attempt = coalesce(j.attempt, 0) + 1,
                    j.started_at = coalesce(j.started_at, $now),
                    j.updated_at = $now
                RETURN count(j) AS claimed
                """,
                job_id=job_id, worker_id=worker_id, lease_until=lease_until, now=now
            ).single()
            return bool(result and result["claimed"])

    def release_lease(self, job_id: str, worker_id: str) -> bool:
        with _driver.session() as session:
            result = session.run(
                """
                MATCH (j:IngestionJob {job_id: $job_id, lease_owner: $worker_id})
                SET j.lease_owner = NULL, j.lease_until = NULL, j.updated_at = $now
                RETURN count(j) AS released
                """,
                job_id=job_id, worker_id=worker_id, now=int(time.time())
            ).single()
            return bool(result and result["released"])

    def complete_job(self, job_id: str, worker_id: str, expected_version: int) -> bool:
        with _driver.session() as session:
            result = session.run(
                """
                MATCH (j:IngestionJob {job_id: $job_id, lease_owner: $worker_id, version: $expected_version})
                SET j.status = 'COMPLETED', j.progress = 1.0, j.completed_at = $now, j.updated_at = $now, j.lease_owner = NULL, j.lease_until = NULL
                RETURN count(j) AS completed
                """,
                job_id=job_id, worker_id=worker_id, expected_version=expected_version, now=int(time.time())
            ).single()
            return bool(result and result["completed"])

    def fail_job(self, job_id: str, worker_id: str, expected_version: int, error_message: str) -> bool:
        with _driver.session() as session:
            result = session.run(
                """
                MATCH (j:IngestionJob {job_id: $job_id, lease_owner: $worker_id, version: $expected_version})
                SET j.status = 'FAILED', j.error_message = $error_message, j.failed_at = $now, j.updated_at = $now, j.lease_owner = NULL, j.lease_until = NULL
                RETURN count(j) AS failed
                """,
                job_id=job_id, worker_id=worker_id, expected_version=expected_version, error_message=error_message, now=int(time.time())
            ).single()
            return bool(result and result["failed"])

    def transition(self, job_id: str, from_statuses: List[JobStatus], to_status: JobStatus, organization_id: Optional[str] = None) -> bool:
        with _driver.session() as session:
            result = session.run(
                """
                MATCH (j:IngestionJob {job_id: $job_id})
                WHERE j.status IN $from_statuses
                  AND ($organization_id IS NULL OR j.organization_id = $organization_id)
                SET j.status = $to_status, j.updated_at = $updated_at
                RETURN count(j) AS changed
                """,
                job_id=job_id,
                from_statuses=[status.value for status in from_statuses],
                to_status=to_status.value,
                updated_at=int(time.time()),
                organization_id=organization_id,
            ).single()
            return bool(result and result["changed"])

    def get_stale_jobs(self, timeout_seconds: int) -> List[IngestionJob]:
        # Legacy stale check based on updated_at
        cutoff_time = int(time.time()) - timeout_seconds
        with _driver.session() as session:
            result = session.run("""
                MATCH (j:IngestionJob)
                WHERE j.status IN ['PROCESSING', 'QUEUED']
                  AND (j.updated_at < $cutoff_time OR (j.updated_at IS NULL AND j.created_at < $cutoff_time))
                RETURN j
            """, cutoff_time=cutoff_time)
            return [self._dict_to_job(dict(record["j"])) for record in result]

    def get_reclaimable_jobs(self) -> List[IngestionJob]:
        # New lease-aware reclaim
        now = int(time.time())
        with _driver.session() as session:
            result = session.run("""
                MATCH (j:IngestionJob)
                WHERE j.status = 'PROCESSING' AND j.lease_until < $now
                RETURN j
            """, now=now)
            return [self._dict_to_job(dict(record["j"])) for record in result]
