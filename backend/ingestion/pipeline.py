import fitz
import json
import logging
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from core.config import settings
from ingestion.excel import extract_text_from_excel
from ingestion.image import extract_text_from_image
from ingestion.audio import transcribe_audio

logger = logging.getLogger(__name__)

llm = ChatGroq(
    api_key=settings.groq_api_key,
    model_name="llama-3.3-70b-versatile",
    temperature=0,
)

PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an organizational memory extractor.
Extract ALL decisions, reasoning, and key information from the content.
Return a JSON array. Each item must have exactly these fields:
- decision: what was decided
- reason: why it was decided
- impact: effect on the organization
- alternatives: list of strings (alternatives considered)
- people: list of strings (people involved)
- timestamp: date if mentioned, else null
- topic: high-level domain (e.g. hiring, product, budget, tech)

Return ONLY a valid JSON array. No markdown, no explanation."""),
    ("human", "Content:\n{content}"),
])

chain = PROMPT | llm


def _structure_and_store(raw_text: str, source: str) -> dict:
    # Store raw text in ChromaDB first
    from db.chroma import chroma_store
    try:
        chroma_store(content=raw_text, source=source)
        logger.info(f"[CHROMA] ✓ Stored raw text: {source}")
    except Exception as e:
        logger.error(f"[CHROMA] ✗ Failed: {e}")

    response = chain.invoke({"content": raw_text})
    raw = response.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    items = json.loads(raw)
    if not isinstance(items, list):
        items = [items]
    logger.info(f"[GROQ] Extracted {len(items)} items from '{source}'")

    from db.neo import neo_store
    for i, item in enumerate(items):
        decision_id = neo_store(
            subject=item.get("topic", "general"),
            action=item.get("decision", ""),
            reason=item.get("reason", ""),
            source=source,
            people=item.get("people") or [],
            impact=item.get("impact", ""),
            alternatives=item.get("alternatives") or [],
            timestamp=str(item.get("timestamp") or ""),
        )
        item["decision_id"] = decision_id
        logger.info(f"[NEO4J] ✓ {i+1}/{len(items)}: '{item.get('decision', '')[:60]}'")

    return {"ingested": len(items), "items": items}


def run_ingestion(file_bytes: bytes, filename: str, source: str = "document") -> dict:
    """Universal ingestion pipeline for PDF, Excel, Images, Audio/Video."""
    file_ext = filename.lower().split('.')[-1]
    
    if file_ext in ['xlsx', 'xls']:
        raw_text = extract_text_from_excel(file_bytes, filename)
        logger.info(f"[EXTRACT] Excel '{filename}' → {len(raw_text)} chars")
    elif file_ext == 'pdf':
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        raw_text = "\n".join(page.get_text() for page in doc)
        logger.info(f"[EXTRACT] PDF '{filename}' → {len(raw_text)} chars")
    elif file_ext in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
        raw_text = extract_text_from_image(file_bytes, filename)
        logger.info(f"[EXTRACT] Image '{filename}' → {len(raw_text)} chars")
    elif file_ext in ['mp3', 'wav', 'm4a', 'mp4', 'mov', 'avi', 'mkv', 'flac', 'ogg', 'webm']:
        raw_text = transcribe_audio(file_bytes, filename)
        logger.info(f"[EXTRACT] Audio/Video '{filename}' → {len(raw_text)} chars")
    else:
        raise ValueError(f"Unsupported file type: {file_ext}. Supported: PDF, Excel, Images, Audio/Video")
    
    return _structure_and_store(raw_text, source)


def run_ingestion_from_text(raw_text: str, source: str) -> dict:
    logger.info(f"[EXTRACT] source='{source}' → {len(raw_text)} chars")
    return _structure_and_store(raw_text, source)
