import logging
from typing import List, Optional

import fitz
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from core.llm import get_llm
from ingestion.audio import transcribe_audio
from ingestion.excel import extract_text_from_excel
from ingestion.image import extract_text_from_image

logger = logging.getLogger(__name__)


class DecisionItem(BaseModel):
    decision: str = Field(description="what was decided")
    reason: str = Field(description="why it was decided")
    impact: str = Field(description="effect on the organization")
    alternatives: List[str] = Field(default_factory=list)
    people: List[str] = Field(default_factory=list)
    timestamp: Optional[str] = Field(default=None)
    topic: str = Field(description="high-level domain")


class ExtractionResult(BaseModel):
    items: List[DecisionItem]


PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an organizational memory extractor.
Extract ALL decisions, reasoning, and key information from the content.
Follow the JSON schema perfectly."""),
    ("human", "Content:\n{content}"),
])


def _structure_and_store(
    raw_text: str,
    source: str,
    provider: str = "groq",
    store_graph: bool = True,
    store_vector: bool = True,
) -> dict:
    """Extract content and optionally write legacy projections.

    Services use both persistence flags as False so PostgreSQL can commit the
    authoritative transaction before projection writes occur.
    """
    if store_vector:
        from db.chroma import chroma_store
        chroma_store(content=raw_text, source=source)

    llm = get_llm(provider)
    chain = PROMPT | llm.with_structured_output(ExtractionResult)
    max_len = 1000 if provider == "ollama" else 100000
    chunks, current_chunk = [], ""
    for paragraph in raw_text.split("\n"):
        if len(current_chunk) + len(paragraph) > max_len and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = paragraph + "\n"
        else:
            current_chunk += paragraph + "\n"
    if current_chunk:
        chunks.append(current_chunk.strip())

    items = []
    for index, chunk in enumerate(chunks):
        if not chunk.strip():
            continue
        try:
            response = chain.invoke({"content": chunk})
            if response and response.items:
                items.extend(item.model_dump() for item in response.items if item.decision.strip())
        except Exception as exc:
            logger.error("Extraction failed for chunk %s/%s: %s", index + 1, len(chunks), exc)

    if store_graph:
        from db.neo import neo_store
        for item in items:
            item["decision_id"] = neo_store(
                subject=item.get("topic", "general"), action=item.get("decision", ""),
                reason=item.get("reason", ""), source=source, people=item.get("people") or [],
                impact=item.get("impact", ""), alternatives=item.get("alternatives") or [],
                timestamp=str(item.get("timestamp") or ""),
            )
    return {"ingested": len(items), "items": items, "raw_text": raw_text}


def run_ingestion(file_bytes: bytes, filename: str, source: str = "document", provider: str = "groq", store_graph: bool = True, store_vector: bool = True) -> dict:
    file_ext = filename.lower().rsplit(".", 1)[-1]
    if file_ext in {"xlsx", "xls"}:
        raw_text = extract_text_from_excel(file_bytes, filename)
    elif file_ext == "pdf":
        document = fitz.open(stream=file_bytes, filetype="pdf")
        raw_text = "\n".join(page.get_text() for page in document)
    elif file_ext in {"png", "jpg", "jpeg", "gif", "webp"}:
        raw_text = extract_text_from_image(file_bytes, filename, provider=provider)
    elif file_ext in {"mp3", "wav", "m4a", "mp4", "mov", "avi", "mkv", "flac", "ogg", "webm"}:
        raw_text = transcribe_audio(file_bytes, filename)
    else:
        raise ValueError(f"Unsupported file type: {file_ext}")
    return _structure_and_store(raw_text, source, provider, store_graph, store_vector)


def run_ingestion_from_text(raw_text: str, source: str, provider: str = "groq", store_graph: bool = True, store_vector: bool = True) -> dict:
    return _structure_and_store(raw_text, source, provider, store_graph, store_vector)
