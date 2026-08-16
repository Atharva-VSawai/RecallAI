"""File registry to track uploaded files and prevent duplicates."""
import hashlib
from datetime import datetime, timezone
from db.neo import _driver

def _compute_hash(file_bytes: bytes) -> str:
    """Compute SHA256 hash of file content."""
    return hashlib.sha256(file_bytes).hexdigest()

def register_file(filename: str, file_hash: str, file_type: str, source: str, project_id: str, organization_id: str) -> dict:
    """Register a new file in Neo4j."""
    with _driver.session() as session:
        result = session.run(
            """
            MERGE (p:Project {id: $project_id, organization_id: $organization_id})
            ON CREATE SET p.name = $project_id,
                          p.slug = $project_id,
                          p.organization_id = $organization_id,
                          p.status = 'ACTIVE'
            MERGE (f:File {hash: $hash, project_id: $project_id, organization_id: $organization_id})
            SET f.filename = $filename,
                f.type = $file_type,
                f.source = $source,
                f.uploaded_at = $timestamp,
                f.organization_id = $organization_id,
                f.deleted_at = null
            MERGE (f)-[:BELONGS_TO]->(p)
            RETURN f.filename as filename, f.hash as hash, f.type as type, 
                   f.source as source, f.uploaded_at as uploaded_at,
                   f.project_id as project_id
            """,
            hash=file_hash,
            filename=filename,
            file_type=file_type,
            source=source,
            project_id=project_id,
            organization_id=organization_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        return result.single().data()

def check_file_exists(file_hash: str, project_id: str, organization_id: str) -> dict | None:
    """Check if file already exists by hash."""
    with _driver.session() as session:
        result = session.run(
            """
            MATCH (f:File {hash: $hash, project_id: $project_id, organization_id: $organization_id})
            WHERE f.deleted_at IS NULL
            RETURN f.filename as filename, f.hash as hash, f.type as type,
                   f.source as source, f.uploaded_at as uploaded_at,
                   f.project_id as project_id
            """,
            hash=file_hash,
            project_id=project_id,
            organization_id=organization_id,
        )
        record = result.single()
        return record.data() if record else None

def list_all_files(project_id: str, organization_id: str, page: int = 1, page_size: int = 50) -> list[dict]:
    """List registered files with pagination, ignoring soft-deleted files."""
    skip = (page - 1) * page_size
    with _driver.session() as session:
        # Get explicitly registered File nodes
        result = session.run(
            """
            MATCH (f:File {project_id: $project_id, organization_id: $organization_id})
            WHERE f.deleted_at IS NULL
            RETURN f.filename as filename, f.hash as hash, f.type as type,
                   f.source as source, f.uploaded_at as uploaded_at,
                   f.project_id as project_id
            ORDER BY f.uploaded_at DESC
            SKIP $skip
            LIMIT $limit
            """,
            project_id=project_id,
            organization_id=organization_id,
            skip=skip,
            limit=page_size,
        )
        return [r.data() for r in result]

def count_files(project_id: str, organization_id: str) -> int:
    with _driver.session() as session:
        result = session.run("MATCH (f:File {project_id: $project_id, organization_id: $organization_id}) WHERE f.deleted_at IS NULL RETURN count(f) AS total", project_id=project_id, organization_id=organization_id).single()
        return int(result["total"] if result else 0)

def get_file_by_source(source: str, project_id: str, organization_id: str) -> dict | None:
    """Get file metadata by source identifier."""
    with _driver.session() as session:
        result = session.run(
            """
            MATCH (f:File {source: $source, project_id: $project_id, organization_id: $organization_id})
            WHERE f.deleted_at IS NULL
            RETURN f.filename as filename, f.hash as hash, f.type as type,
                   f.source as source, f.uploaded_at as uploaded_at,
                   f.project_id as project_id
            """,
            source=source,
            project_id=project_id,
            organization_id=organization_id,
        )
        record = result.single()
        return record.data() if record else None

def delete_file_by_source(source: str, project_id: str, organization_id: str) -> dict:
    """Delete one source's registry, graph, and ingestion state within its tenant.

    Decisions can be shared by multiple source Documents, so those are removed
    only after the source relationship is removed and no other source supports
    them. Source-owned containers and processing checkpoints are safe to remove.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    with _driver.session() as session:
        # Soft delete the File node
        file_result = session.run(
            """
            MATCH (f:File {source: $source, project_id: $project_id, organization_id: $organization_id})
            SET f.deleted_at = $timestamp
            RETURN count(f) as deleted_files
            """,
            source=source,
            project_id=project_id,
            organization_id=organization_id,
            timestamp=timestamp,
        )
        deleted_files = file_result.single()["deleted_files"]

        # Only delete knowledge nodes that ONLY have THIS source (no other valid sources)
        decision_result = session.run(
            """
            MATCH (doc:Document {source: $source, project_id: $project_id, organization_id: $organization_id})-[support:SUPPORTS]->(d:Decision)
            DELETE support
            WITH d
            WHERE NOT (d)<-[:SUPPORTS]-(:Document)
            DETACH DELETE d
            RETURN count(d) as deleted_decisions
            """,
            source=source,
            project_id=project_id,
            organization_id=organization_id,
        )
        deleted_decisions = decision_result.single()["deleted_decisions"]

        knowledge_result = session.run(
            """
            MATCH (m:Meeting {source: $source, project_id: $project_id, organization_id: $organization_id})-[:HAS_KNOWLEDGE]->(k:MeetingKnowledge)
            DETACH DELETE k
            RETURN count(k) as deleted_knowledge
            """,
            source=source,
            project_id=project_id,
            organization_id=organization_id,
        )
        deleted_knowledge = knowledge_result.single()["deleted_knowledge"]

        # Orphan cleanup
        orphan_result = session.run(
            """
            MATCH (n)
            WHERE n.project_id = $project_id
              AND n.organization_id = $organization_id
              AND (n:Person OR n:Reason OR n:Alternative)
              AND NOT (n)--()
            DETACH DELETE n
            RETURN count(n) as deleted_orphans
            """,
            project_id=project_id,
            organization_id=organization_id,
        )
        deleted_orphans = orphan_result.single()["deleted_orphans"]

        # Remove the source container nodes. Leaving these behind makes the
        # graph appear to contain deleted knowledge and can retain stale
        # provenance on a later upload of the same content.
        document_result = session.run(
            """
            MATCH (doc:Document {source: $source, project_id: $project_id, organization_id: $organization_id})
            DETACH DELETE doc
            RETURN count(doc) AS deleted_documents
            """,
            source=source, project_id=project_id, organization_id=organization_id,
        ).single()
        deleted_documents = document_result["deleted_documents"]

        meeting_result = session.run(
            """
            MATCH (m:Meeting {source: $source, project_id: $project_id, organization_id: $organization_id})
            DETACH DELETE m
            RETURN count(m) AS deleted_meetings
            """,
            source=source, project_id=project_id, organization_id=organization_id,
        ).single()
        deleted_meetings = meeting_result["deleted_meetings"]

        # A deleted source must not leave an active/claimed job or completed
        # chunk ledger behind. Keep the job as CANCELLED for status polling.
        job_result = session.run(
            """
            MATCH (j:IngestionJob {source_id: $source, project_id: $project_id, organization_id: $organization_id})
            OPTIONAL MATCH (c:ProcessedChunk {organization_id: $organization_id, project_id: $project_id, job_id: j.job_id})
            DELETE c
            SET j.status = CASE WHEN j.status IN ['QUEUED', 'PROCESSING', 'STALE'] THEN 'CANCELLED' ELSE j.status END,
                j.lease_owner = NULL, j.lease_until = NULL, j.updated_at = $now
            RETURN count(DISTINCT j) AS affected_jobs
            """,
            source=source, project_id=project_id, organization_id=organization_id, now=int(datetime.now(timezone.utc).timestamp()),
        ).single()
        affected_jobs = job_result["affected_jobs"]

        return {
            "deleted_decisions": deleted_decisions,
            "deleted_knowledge": deleted_knowledge,
            "deleted_orphans": deleted_orphans,
            "deleted_files": deleted_files,
            "deleted_documents": deleted_documents,
            "deleted_meetings": deleted_meetings,
            "affected_jobs": affected_jobs,
        }
