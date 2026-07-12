import uuid
import chromadb
from langchain_cohere import CohereEmbeddings
from core.config import settings

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


def chroma_store(content: str, source: str, metadata: dict = None) -> str:
    chunks = _chunk_text(content)
    embeddings = _embeddings.embed_documents(chunks)
    _collection.add(
        documents=chunks,
        embeddings=embeddings,
        metadatas=[{"source": source, **(metadata or {})} for _ in chunks],
        ids=[str(uuid.uuid4()) for _ in chunks],
    )
    return f"Stored {len(chunks)} chunks in Chroma Cloud: {source}"


def chroma_search(query: str, k: int = 4, source_filter: str = None) -> list:
    embedding = _embeddings.embed_query(query)
    where = {"source": {"$eq": source_filter}} if source_filter else None
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
        docs.append({"page_content": doc, "metadata": meta})
    return docs
