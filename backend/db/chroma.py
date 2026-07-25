import logging
import uuid
import chromadb
from langchain_cohere import CohereEmbeddings
from core.config import settings

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


def _where_filter(project_id: str | None = None, source_filter: str | None = None) -> dict | None:
    clauses = []
    if project_id:
        clauses.append({"project_id": {"$eq": project_id}})
    if source_filter:
        clauses.append({"source": {"$eq": source_filter}})
    if not clauses:
        return None
    return clauses[0] if len(clauses) == 1 else {"$and": clauses}


def chroma_store(content: str, source: str, metadata: dict = None, project_id: str | None = None) -> str:
    chunks = _chunk_text(content)
    embeddings = _embeddings.embed_documents(chunks)
    base_metadata = {"source": source, **(metadata or {})}
    if project_id:
        base_metadata["project_id"] = project_id
    try:
        _collection.add(
            documents=chunks,
            embeddings=embeddings,
            metadatas=[base_metadata for _ in chunks],
            ids=[str(uuid.uuid4()) for _ in chunks],
        )
    except Exception as exc:
        exc_str = str(exc)
        # ChromaDB Cloud returns 409 when duplicate content is detected.
        # Treat this as a silent no-op — the vectors are already stored.
        if "409" in exc_str or "already" in exc_str.lower() or "conflict" in exc_str.lower():
            logger.info("ChromaDB: skipping duplicate content for source '%s': %s", source, exc_str[:120])
            return f"Skipped {len(chunks)} duplicate chunks in Chroma Cloud: {source}"
        raise
    return f"Stored {len(chunks)} chunks in Chroma Cloud: {source}"


def chroma_search(query: str, k: int = 4, source_filter: str = None, project_id: str | None = None) -> list:
    embedding = _embeddings.embed_query(query)
    legacy_default_project = project_id == "main-workspace"
    where = _where_filter(
        project_id=None if legacy_default_project else project_id,
        source_filter=source_filter,
    )
    try:
        results = _collection.query(
            query_embeddings=[embedding],
            n_results=k,
            where=where,
        )
    except Exception:
        # ChromaDB throws when filter matches 0 docs — return empty
        return []
    docs = []
    seen = set()
    for i, doc in enumerate(results["documents"][0]):
        key = doc[:200]
        if key in seen:
            continue
        seen.add(key)
        meta = results["metadatas"][0][i] if results["metadatas"] else {}
        # Hard-enforce filter: discard any result from a different source
        if source_filter and meta.get("source") != source_filter:
            continue
        if project_id and meta.get("project_id") != project_id:
            if not (legacy_default_project and "project_id" not in meta):
                continue
        docs.append({"page_content": doc, "metadata": meta})
    return docs

def chroma_delete_by_source(source: str, project_id: str | None = None) -> dict:
    """Delete all text chunks matching the given source from Chroma."""
    try:
        _collection.delete(where=_where_filter(project_id=project_id, source_filter=source))
        return {"status": "success", "source": source}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def chroma_delete_by_project(project_id: str) -> dict:
    try:
        _collection.delete(where={"project_id": {"$eq": project_id}})
        return {"status": "success", "project_id": project_id}
    except Exception as e:
        return {"status": "error", "error": str(e)}
