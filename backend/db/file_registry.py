"""File registry to track uploaded files and prevent duplicates."""
import hashlib
from datetime import datetime, timezone
from db.neo import _driver

def _compute_hash(file_bytes: bytes) -> str:
    """Compute SHA256 hash of file content."""
    return hashlib.sha256(file_bytes).hexdigest()

def register_file(filename: str, file_hash: str, file_type: str, source: str, project_id: str | None = None, organization_id: str = "default") -> dict:
    """Register a new file in Neo4j."""
    with _driver.session() as session:
        result = session.run(
            """
            MERGE (p:Project {id: $project_id})
            ON CREATE SET p.name = $project_id,
                          p.slug = $project_id,
                          p.organization_id = $organization_id,
                          p.status = 'ACTIVE'
            MERGE (f:File {hash: $hash, project_id: $project_id})
            SET f.filename = $filename,
                f.type = $file_type,
                f.source = $source,
                f.uploaded_at = $timestamp,
                f.organization_id = $organization_id
            MERGE (f)-[:BELONGS_TO]->(p)
            RETURN f.filename as filename, f.hash as hash, f.type as type, 
                   f.source as source, f.uploaded_at as uploaded_at,
                   f.project_id as project_id
            """,
            hash=file_hash,
            filename=filename,
            file_type=file_type,
            source=source,
            project_id=project_id or "main-workspace",
            organization_id=organization_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        return result.single().data()

def check_file_exists(file_hash: str, project_id: str | None = None) -> dict | None:
    """Check if file already exists by hash."""
    with _driver.session() as session:
        result = session.run(
            """
            MATCH (f:File {hash: $hash})
            WHERE ($project_id IS NULL OR f.project_id = $project_id)
            RETURN f.filename as filename, f.hash as hash, f.type as type,
                   f.source as source, f.uploaded_at as uploaded_at,
                   f.project_id as project_id
            """,
            hash=file_hash,
            project_id=project_id,
        )
        record = result.single()
        return record.data() if record else None

def list_all_files(project_id: str | None = None) -> list[dict]:
    """List all registered files."""
    with _driver.session() as session:
        # Get explicitly registered File nodes
        result = session.run(
            """
            MATCH (f:File)
            WHERE ($project_id IS NULL OR f.project_id = $project_id)
            RETURN f.filename as filename, f.hash as hash, f.type as type,
                   f.source as source, f.uploaded_at as uploaded_at,
                   f.project_id as project_id
            """,
            project_id=project_id,
        )
        registered = {r["source"]: r.data() for r in result}

        # Also collect sources from Decision nodes (covers audio/image/slack ingestions)
        result = session.run(
            """
            MATCH (d:Decision)
            WHERE ($project_id IS NULL OR d.project_id = $project_id)
            WITH DISTINCT d.source as source
            WHERE source IS NOT NULL AND source <> ''
            WITH source,
                 CASE
                   WHEN source STARTS WITH 'document:' THEN substring(source, 9)
                   WHEN source STARTS WITH 'audio:' THEN substring(source, 6)
                   WHEN source STARTS WITH 'image:' THEN substring(source, 6)
                   WHEN source STARTS WITH 'slack:' THEN '#' + substring(source, 6)
                   ELSE source
                 END as filename,
                 CASE
                   WHEN toLower(source) CONTAINS '.pdf' THEN 'pdf'
                   WHEN toLower(source) CONTAINS '.xlsx' THEN 'xlsx'
                   WHEN toLower(source) CONTAINS '.xls' THEN 'xls'
                   WHEN toLower(source) CONTAINS '.mp3' THEN 'mp3'
                   WHEN toLower(source) CONTAINS '.mp4' THEN 'mp4'
                   WHEN toLower(source) CONTAINS '.mov' THEN 'mov'
                   WHEN toLower(source) CONTAINS '.avi' THEN 'avi'
                   WHEN toLower(source) CONTAINS '.wav' THEN 'wav'
                   WHEN toLower(source) CONTAINS '.m4a' THEN 'm4a'
                   WHEN toLower(source) CONTAINS '.png' THEN 'png'
                   WHEN toLower(source) CONTAINS '.jpg' THEN 'jpg'
                   WHEN toLower(source) CONTAINS '.jpeg' THEN 'jpeg'
                   WHEN toLower(source) CONTAINS '.gif' THEN 'gif'
                   WHEN toLower(source) CONTAINS '.webp' THEN 'webp'
                   WHEN source STARTS WITH 'slack:' THEN 'slack'
                   ELSE 'unknown'
                 END as type
            RETURN filename, '' as hash, type, source, '' as uploaded_at, $project_id as project_id
            """,
            project_id=project_id,
        )
        for r in result:
            if r["source"] not in registered:
                registered[r["source"]] = r.data()

        files = sorted(registered.values(), key=lambda f: f.get("uploaded_at") or "", reverse=True)
        return files

def get_file_by_source(source: str, project_id: str | None = None) -> dict | None:
    """Get file metadata by source identifier."""
    with _driver.session() as session:
        result = session.run(
            """
            MATCH (f:File {source: $source})
            WHERE ($project_id IS NULL OR f.project_id = $project_id)
            RETURN f.filename as filename, f.hash as hash, f.type as type,
                   f.source as source, f.uploaded_at as uploaded_at,
                   f.project_id as project_id
            """,
            source=source,
            project_id=project_id,
        )
        record = result.single()
        return record.data() if record else None

def delete_file_by_source(source: str, project_id: str | None = None) -> dict:
    """Delete a file and all its associated decisions from Neo4j."""
    with _driver.session() as session:
        # First delete all Decision nodes associated with this source
        decision_result = session.run(
            """
            MATCH (d:Decision {source: $source})
            WHERE ($project_id IS NULL OR d.project_id = $project_id)
            DETACH DELETE d
            RETURN count(d) as deleted_decisions
            """,
            source=source,
            project_id=project_id,
        )
        deleted_decisions = decision_result.single()["deleted_decisions"]

        knowledge_result = session.run(
            """
            MATCH (k:MeetingKnowledge {source: $source})
            WHERE ($project_id IS NULL OR k.project_id = $project_id)
            DETACH DELETE k
            RETURN count(k) as deleted_knowledge
            """,
            source=source,
            project_id=project_id,
        )
        deleted_knowledge = knowledge_result.single()["deleted_knowledge"]

        # Person/Reason/Alternative nodes are shared by project and may be
        # referenced by another source. Only remove nodes that became orphaned.
        orphan_result = session.run(
            """
            MATCH (n)
            WHERE ($project_id IS NULL OR n.project_id = $project_id)
              AND (n:Person OR n:Reason OR n:Alternative)
              AND NOT (n)--()
            DETACH DELETE n
            RETURN count(n) as deleted_orphans
            """,
            project_id=project_id,
        )
        deleted_orphans = orphan_result.single()["deleted_orphans"]

        # Then delete the File node itself
        file_result = session.run(
            """
            MATCH (f:File {source: $source})
            WHERE ($project_id IS NULL OR f.project_id = $project_id)
            DETACH DELETE f
            RETURN count(f) as deleted_files
            """,
            source=source,
            project_id=project_id,
        )
        deleted_files = file_result.single()["deleted_files"]

        return {
            "deleted_decisions": deleted_decisions,
            "deleted_knowledge": deleted_knowledge,
            "deleted_orphans": deleted_orphans,
            "deleted_files": deleted_files
        }
