import time
from typing import Optional, Dict, Any
from db.neo import _driver

class ProcessingLedger:
    """
    Race-safe ledger for idempotent chunk processing.
    Tracks whether a specific chunk (by index and content hash) has been fully
    processed and written to the knowledge graph and vector store.
    """
    
    @staticmethod
    def mark_chunk_processing(
        organization_id: str,
        project_id: str,
        job_id: str,
        chunk_index: int,
        content_hash: str,
        worker_id: str,
        lease_timeout: int = 300
    ) -> bool:
        """
        Attempts to claim a chunk for processing.
        Returns True if claimed, False if already completed or actively processing by another worker.
        """
        now = int(time.time())
        cutoff = now - lease_timeout
        with _driver.session() as session:
            result = session.run("""
                MERGE (c:ProcessedChunk {
                    organization_id: $organization_id,
                    project_id: $project_id,
                    job_id: $job_id,
                    chunk_index: $chunk_index
                })
                ON CREATE SET 
                    c.content_hash = $content_hash,
                    c.status = 'PROCESSING',
                    c.worker_id = $worker_id,
                    c.attempt = 1,
                    c.updated_at = $now
                ON MATCH SET
                    c.status = CASE WHEN c.status = 'FAILED' OR (c.status = 'PROCESSING' AND c.updated_at < $cutoff) THEN 'PROCESSING' ELSE c.status END,
                    c.worker_id = CASE WHEN c.status = 'FAILED' OR (c.status = 'PROCESSING' AND c.updated_at < $cutoff) THEN $worker_id ELSE c.worker_id END,
                    c.attempt = CASE WHEN c.status = 'FAILED' OR (c.status = 'PROCESSING' AND c.updated_at < $cutoff AND c.worker_id <> $worker_id) THEN coalesce(c.attempt, 0) + 1 ELSE c.attempt END,
                    c.updated_at = CASE WHEN c.status = 'FAILED' OR (c.status = 'PROCESSING' AND c.updated_at < $cutoff) OR (c.status = 'PROCESSING' AND c.worker_id = $worker_id) THEN $now ELSE c.updated_at END
                WITH c
                RETURN c.status = 'PROCESSING' AND c.worker_id = $worker_id AS claimed
            """,
                organization_id=organization_id,
                project_id=project_id,
                job_id=job_id,
                chunk_index=chunk_index,
                content_hash=content_hash,
                worker_id=worker_id,
                now=now,
                cutoff=cutoff
            ).single()
            return bool(result and result["claimed"])

    @staticmethod
    def mark_chunk_completed(
        organization_id: str,
        project_id: str,
        job_id: str,
        chunk_index: int,
        worker_id: str
    ) -> bool:
        """Marks a claimed chunk as COMPLETED."""
        now = int(time.time())
        with _driver.session() as session:
            result = session.run("""
                MATCH (c:ProcessedChunk {
                    organization_id: $organization_id,
                    project_id: $project_id,
                    job_id: $job_id,
                    chunk_index: $chunk_index,
                    worker_id: $worker_id
                })
                SET c.status = 'COMPLETED',
                    c.completed_at = $now,
                    c.updated_at = $now
                RETURN count(c) as changed
            """,
                organization_id=organization_id,
                project_id=project_id,
                job_id=job_id,
                chunk_index=chunk_index,
                worker_id=worker_id,
                now=now
            ).single()
            return bool(result and result["changed"])

    @staticmethod
    def mark_chunk_failed(
        organization_id: str,
        project_id: str,
        job_id: str,
        chunk_index: int,
        worker_id: str
    ) -> bool:
        """Marks a claimed chunk as FAILED."""
        now = int(time.time())
        with _driver.session() as session:
            result = session.run("""
                MATCH (c:ProcessedChunk {
                    organization_id: $organization_id,
                    project_id: $project_id,
                    job_id: $job_id,
                    chunk_index: $chunk_index,
                    worker_id: $worker_id
                })
                SET c.status = 'FAILED',
                    c.updated_at = $now
                RETURN count(c) as changed
            """,
                organization_id=organization_id,
                project_id=project_id,
                job_id=job_id,
                chunk_index=chunk_index,
                worker_id=worker_id,
                now=now
            ).single()
            return bool(result and result["changed"])
            
    @staticmethod
    def is_chunk_completed(
        organization_id: str,
        project_id: str,
        job_id: str,
        chunk_index: int
    ) -> bool:
        """Checks if a chunk is already completed."""
        with _driver.session() as session:
            result = session.run("""
                MATCH (c:ProcessedChunk {
                    organization_id: $organization_id,
                    project_id: $project_id,
                    job_id: $job_id,
                    chunk_index: $chunk_index,
                    status: 'COMPLETED'
                })
                RETURN count(c) > 0 as is_completed
            """,
                organization_id=organization_id,
                project_id=project_id,
                job_id=job_id,
                chunk_index=chunk_index
            ).single()
            return bool(result and result["is_completed"])
