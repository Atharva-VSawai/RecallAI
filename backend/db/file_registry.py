"""File registry to track uploaded files and prevent duplicates."""
import hashlib
from datetime import datetime, timezone
from neo4j import GraphDatabase
from core.config import settings

_driver = GraphDatabase.driver(
    settings.neo4j_uri,
    auth=(settings.neo4j_username, settings.neo4j_password),
)

def _compute_hash(file_bytes: bytes) -> str:
    """Compute SHA256 hash of file content."""
    return hashlib.sha256(file_bytes).hexdigest()

def register_file(filename: str, file_hash: str, file_type: str, source: str) -> dict:
    """Register a new file in Neo4j."""
    with _driver.session() as session:
        result = session.run(
            """
            MERGE (f:File {hash: $hash})
            SET f.filename = $filename,
                f.type = $file_type,
                f.source = $source,
                f.uploaded_at = $timestamp
            RETURN f.filename as filename, f.hash as hash, f.type as type, 
                   f.source as source, f.uploaded_at as uploaded_at
            """,
            hash=file_hash,
            filename=filename,
            file_type=file_type,
            source=source,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        return result.single().data()

def check_file_exists(file_hash: str) -> dict | None:
    """Check if file already exists by hash."""
    with _driver.session() as session:
        result = session.run(
            """
            MATCH (f:File {hash: $hash})
            RETURN f.filename as filename, f.hash as hash, f.type as type,
                   f.source as source, f.uploaded_at as uploaded_at
            """,
            hash=file_hash,
        )
        record = result.single()
        return record.data() if record else None

def list_all_files() -> list[dict]:
    """List all registered files."""
    with _driver.session() as session:
        # Get explicitly registered File nodes
        result = session.run(
            """
            MATCH (f:File)
            RETURN f.filename as filename, f.hash as hash, f.type as type,
                   f.source as source, f.uploaded_at as uploaded_at
            """
        )
        registered = {r["source"]: r.data() for r in result}

        # Also collect sources from Decision nodes (covers audio/image/slack ingestions)
        result = session.run(
            """
            MATCH (d:Decision)
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
            RETURN filename, '' as hash, type, source, '' as uploaded_at
            """
        )
        for r in result:
            if r["source"] not in registered:
                registered[r["source"]] = r.data()

        files = sorted(registered.values(), key=lambda f: f.get("uploaded_at") or "", reverse=True)
        return files

def get_file_by_source(source: str) -> dict | None:
    """Get file metadata by source identifier."""
    with _driver.session() as session:
        result = session.run(
            """
            MATCH (f:File {source: $source})
            RETURN f.filename as filename, f.hash as hash, f.type as type,
                   f.source as source, f.uploaded_at as uploaded_at
            """,
            source=source,
        )
        record = result.single()
        return record.data() if record else None
