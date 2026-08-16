import logging
import uuid
import hashlib
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Dict, List, Optional
import chromadb
from langchain_cohere import CohereEmbeddings
from core.config import settings

from infrastructure.repositories.vector_store_repository import VectorStoreRepository
from application.services.observability_service import breakers, store

logger = logging.getLogger(__name__)

_embeddings = CohereEmbeddings(
    cohere_api_key=settings.cohere_api_key,
    model="embed-english-light-v3.0",
)

_client = chromadb.CloudClient(
    api_key=settings.chroma_api_key,
    tenant=settings.chroma_tenant,
    database=settings.chroma_database,
)

_collection = _client.get_or_create_collection(name="notes")
_request_embedding_cache: ContextVar[dict[str, list[float]] | None] = ContextVar(
    "request_embedding_cache", default=None,
)

@contextmanager
def query_embedding_cache():
    """Reuse identical query embeddings for one agent request only."""
    token = _request_embedding_cache.set({})
    try:
        yield
    finally:
        _request_embedding_cache.reset(token)

def _chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    """Split text into overlapping chunks."""
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

class ChromaVectorStoreRepository(VectorStoreRepository):
    """Metadata-isolated Vector Store for ChromaDB."""
    
    def _where_filter(
        self,
        organization_id: str,
        project_id: str,
        source_filter: Optional[str] = None,
        metadata_filters: Optional[Dict[str, Any]] = None,
    ) -> Dict:
        # Strict isolation at the database query level
        clauses = [
            {"organization_id": {"$eq": organization_id}},
            {"project_id": {"$eq": project_id}}
        ]
        if source_filter:
            clauses.append({"source": {"$eq": source_filter}})
        for key, value in (metadata_filters or {}).items():
            if key in {"organization_id", "project_id", "source"} or value in (None, ""):
                continue
            clauses.append({key: {"$eq": value}})
        return {"$and": clauses}

    def add_vectors(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ) -> None:
        if not (len(texts) == len(embeddings) == len(metadatas) == len(ids)):
            raise ValueError("Vector inputs must have equal lengths")
        required = {"organization_id", "project_id", "document_id", "chunk_id", "content_hash"}
        if any(not required.issubset(metadata) for metadata in metadatas):
            raise ValueError("Every vector requires tenant and document provenance metadata")
        try:
            # Chroma IDs are the uniqueness boundary. Upsert makes retries
            # safe while the repository remains the only collection access point.
            _collection.upsert(
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids,
            )
        except Exception as exc:
            exc_str = str(exc)
            if "409" in exc_str or "already" in exc_str.lower() or "conflict" in exc_str.lower():
                logger.info("ChromaDB: skipping duplicate content insertions")
            else:
                raise

    def query_vectors(
        self,
        query_embedding: List[float],
        k: int,
        organization_id: str,
        project_id: str,
        source_filter: Optional[str] = None,
        metadata_filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        if not organization_id or not project_id:
            raise ValueError("organization_id and project_id are required")
        where = self._where_filter(organization_id, project_id, source_filter, metadata_filters)
        try:
            results = _collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                where=where,
            )
        except Exception as exc:
            logger.error(f"Chroma query failed: {exc}")
            raise RuntimeError("Vector store is unavailable") from exc
            
        docs = []
        seen = set()
        for i, doc in enumerate(results["documents"][0]):
            key = doc[:200]
            if key in seen:
                continue
            seen.add(key)
            meta = results["metadatas"][0][i] if results["metadatas"] else {}
            
            # Post-query hard validation to guarantee isolation (belt and suspenders)
            if meta.get("organization_id") != organization_id or meta.get("project_id") != project_id:
                continue
            if source_filter and meta.get("source") != source_filter:
                continue
            if any(meta.get(key) != value for key, value in (metadata_filters or {}).items() if key not in {"organization_id", "project_id", "source"} and value not in (None, "")):
                continue
                
            docs.append({"page_content": doc, "metadata": meta})
        return docs

    def get_by_metadata(
        self,
        organization_id: str,
        project_id: str,
        metadata_filters: Dict[str, Any],
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        if not organization_id or not project_id:
            raise ValueError("organization_id and project_id are required")
        where = self._where_filter(organization_id, project_id, metadata_filters=metadata_filters)
        try:
            raw = _collection.get(where=where, limit=limit, include=["documents", "metadatas"])
        except Exception as exc:
            logger.error("Chroma metadata fetch failed: %s", exc)
            raise RuntimeError("Vector store is unavailable") from exc
        docs = []
        for doc, meta in zip(raw.get("documents", []), raw.get("metadatas", [])):
            if meta.get("organization_id") != organization_id or meta.get("project_id") != project_id:
                continue
            if any(meta.get(key) != value for key, value in metadata_filters.items() if value not in (None, "")):
                continue
            docs.append({"page_content": doc, "metadata": meta})
        return docs

    def get_existing_ids(self, ids: List[str], organization_id: str, project_id: str) -> set[str]:
        if not ids:
            return set()
        try:
            existing = _collection.get(ids=ids, include=["metadatas"])
            return {item_id for item_id, metadata in zip(existing.get("ids", []), existing.get("metadatas", [])) if metadata.get("organization_id") == organization_id and metadata.get("project_id") == project_id}
        except Exception as exc:
            logger.warning(f"Error checking existing IDs: {exc}")
            raise RuntimeError("Vector store is unavailable") from exc

    def delete_by_source(self, organization_id: str, project_id: str, source: str) -> bool:
        try:
            where = self._where_filter(organization_id, project_id, source)
            _collection.delete(where=where)
            return True
        except Exception as exc:
            logger.error(f"Error deleting by source: {exc}")
            return False

    def delete_by_project(self, organization_id: str, project_id: str) -> bool:
        try:
            where = {"$and": [{"organization_id": {"$eq": organization_id}}, {"project_id": {"$eq": project_id}}]}
            _collection.delete(where=where)
            return True
        except Exception as exc:
            logger.error(f"Error deleting by project: {exc}")
            return False

    def delete_by_ids(self, organization_id: str, project_id: str, ids: List[str]) -> bool:
        try:
            if ids:
                _collection.delete(ids=list(self.get_existing_ids(ids, organization_id, project_id)))
            return True
        except Exception as exc:
            logger.error(f"Error deleting vectors by IDs: {exc}")
            return False

vector_store = ChromaVectorStoreRepository()

# Legacy vectors created before tenant metadata was mandatory used the
# ``main-workspace`` project and omitted organization_id.  They must not be
# queried by relaxing isolation.  Instead, migrate them only after Neo4j
# proves that the source belongs to the requested tenant/project.
_migrated_legacy_sources: set[tuple[str, str, str]] = set()

def _source_authorized_in_neo4j(organization_id: str, project_id: str, source: str) -> bool:
    try:
        from db.neo import get_driver
        driver = get_driver()
        with driver.session() as session:
            row = session.run(
                "MATCH (n) WHERE n.source = $source AND n.organization_id IS NOT NULL "
                "AND n.project_id IS NOT NULL "
                "RETURN collect(DISTINCT n.organization_id + ':' + n.project_id) AS owners",
                source=source, organization_id=organization_id, project_id=project_id,
            ).single()
        owners = list((row or {}).get("owners") or [])
        return owners == [f"{organization_id}:{project_id}"]
    except Exception as exc:
        logger.warning("Unable to validate legacy source ownership: %s", exc)
        return False

def _migrate_legacy_source_vectors(organization_id: str, project_id: str, source: str) -> int:
    key = (organization_id, project_id, source)
    if key in _migrated_legacy_sources or not _source_authorized_in_neo4j(organization_id, project_id, source):
        return 0
    try:
        raw = _collection.get(where={"source": {"$eq": source}}, include=["documents", "metadatas"])
        ids = list(raw.get("ids", []))
        documents = list(raw.get("documents", []))
        metadatas = list(raw.get("metadatas", []))
        updated_ids, updated_metadata = [], []
        for item_id, document, metadata in zip(ids, documents, metadatas):
            if metadata.get("organization_id") or metadata.get("project_id") not in (None, "main-workspace"):
                continue
            updated_ids.append(item_id)
            updated_metadata.append({
                **metadata, "organization_id": organization_id, "project_id": project_id,
                "document_id": metadata.get("document_id", source),
                "chunk_id": metadata.get("chunk_id", item_id),
                "content_hash": metadata.get("content_hash", hashlib.sha256((document or "").encode()).hexdigest()),
            })
        if updated_ids:
            _collection.update(ids=updated_ids, metadatas=updated_metadata)
            # Durable audit/mapping record. The vector ID, not the filename,
            # is the migration identity and can be reconciled after restart.
            from db.neo import get_driver
            driver = get_driver()
            with driver.session() as session:
                for vector_id, metadata in zip(updated_ids, updated_metadata):
                    session.run(
                        "MERGE (m:LegacyVectorMapping {vector_id: $vector_id}) "
                        "SET m.legacy_source = $legacy_source, m.target_source = $target_source, "
                        "m.organization_id = $organization_id, m.project_id = $project_id, "
                        "m.document_id = $document_id, m.content_hash = $content_hash, "
                        "m.status = 'MIGRATED', m.updated_at = timestamp()",
                        vector_id=vector_id, legacy_source=source,
                        target_source=source, organization_id=organization_id,
                        project_id=project_id, document_id=metadata["document_id"],
                        content_hash=metadata["content_hash"],
                    ).consume()
        _migrated_legacy_sources.add(key)
        logger.info("Migrated %d legacy vectors for authorized source %s", len(updated_ids), source)
        return len(updated_ids)
    except Exception as exc:
        logger.warning("Legacy vector migration failed: %s", exc)
        return 0

# --- Legacy Helper Methods (Will be deprecated over time) ---
def chroma_store(content: str, source: str, organization_id: str, project_id: str, metadata: dict = None) -> str:
    chunks = _chunk_text(content)
    embeddings = breakers["cohere"].call(lambda: _embeddings.embed_documents(chunks))
    store.record_usage("embedding", "cohere", units=sum(len(chunk) for chunk in chunks) // 4)
    base_metadata = {"source": source, "organization_id": organization_id, **(metadata or {})}
    if not project_id or not organization_id:
        raise ValueError("organization_id and project_id are required")
    base_metadata["project_id"] = project_id
    document_id = base_metadata.get("document_id", source)
    ids = [hashlib.sha256(f"{organization_id}:{project_id}:{document_id}:{i}:{chunk}".encode()).hexdigest() for i, chunk in enumerate(chunks)]
    metadatas = [
        {**base_metadata, "document_id": document_id,
         "chunk_id": ids[i], "content_hash": hashlib.sha256(chunk.encode()).hexdigest()}
        for i, chunk in enumerate(chunks)
    ]
    vector_store.add_vectors(chunks, embeddings, metadatas, ids)
    return f"Stored {len(chunks)} chunks in Chroma Cloud: {source}"

def chroma_search(query: str, organization_id: str, project_id: str, k: int = 4, source_filter: str = None, metadata_filters: dict | None = None) -> list:
    cache = _request_embedding_cache.get()
    cache_key = query.strip()
    if cache is not None and cache_key in cache:
        embedding = cache[cache_key]
    else:
        embedding = breakers["cohere"].call(lambda: _embeddings.embed_query(query))
        store.record_usage("embedding", "cohere", units=max(1, len(query) // 4))
        if cache is not None:
            cache[cache_key] = embedding

    results = breakers["chroma"].call(lambda: vector_store.query_vectors(embedding, k, organization_id, project_id, source_filter, metadata_filters))

    if not results and source_filter:
        _migrate_legacy_source_vectors(organization_id, project_id, source_filter)
        results = breakers["chroma"].call(lambda: vector_store.query_vectors(embedding, k, organization_id, project_id, source_filter, metadata_filters))

    return results

def chroma_delete_by_source(source: str, project_id: str, organization_id: str) -> dict:
    success = vector_store.delete_by_source(organization_id, project_id, source)
    return {"status": "success" if success else "error", "source": source}

def chroma_delete_by_project(project_id: str, organization_id: str) -> dict:
    success = vector_store.delete_by_project(organization_id, project_id)
    return {"status": "success" if success else "error", "project_id": project_id}
