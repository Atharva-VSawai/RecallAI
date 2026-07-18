import json
import logging
from langchain.tools import tool
from core.llm import get_llm
from langchain_core.prompts import ChatPromptTemplate
from core.config import settings
from ingestion.pipeline import ExtractionResult
from db.neo import neo_store

logger = logging.getLogger(__name__)



_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Extract data from Excel rows. Each row = 1 record.

Financial data: Extract category, amount, date.
Audit data: Extract finding, status, owner.
Other: Extract key info from each row.

Follow the JSON schema perfectly."""),
    ("human", "{content}"),
])




@tool
def extract_and_store(content: str, source: str, provider: str = "groq") -> str:
    """Extract decisions from raw text using LLM and store them into Neo4j graph memory."""
    # Always store raw text in Chroma first
    from db.chroma import chroma_store
    try:
        chroma_store(content=content, source=source, metadata={"status": "processing"})
        logger.info(f"[INGEST TOOL] ✓ Stored raw text in ChromaDB: {source}")
    except Exception as e:
        logger.error(f"[INGEST TOOL] ✗ ChromaDB storage failed: {e}")
    
    # Try to extract and store decisions
    try:
        llm = get_llm(provider)
        structured_llm = llm.with_structured_output(ExtractionResult)
        chain = _PROMPT | structured_llm
        
        response = structured_llm.invoke(_PROMPT.format_messages(content=content))
        
        items = []
        if response and response.items:
            items = [item.model_dump() for item in response.items if item.decision and item.decision.strip()]
        
        logger.info(f"[INGEST TOOL] LLM extracted {len(items)} items")

        stored = []
        neo4j_errors = []
        
        for idx, item in enumerate(items):
            try:
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
                stored.append(item)
                logger.info(f"[INGEST TOOL] ✓ Neo4j stored {idx+1}/{len(items)}: {decision_id}")
            except Exception as e:
                logger.error(f"[INGEST TOOL] ✗ Neo4j error for item {idx+1}: {e}")
                neo4j_errors.append(str(e))
                item["decision_id"] = "neo4j_error"
                stored.append(item)

        result = {"ingested": len(stored), "items": stored}
        if neo4j_errors:
            result["neo4j_errors"] = neo4j_errors
            result["note"] = "Some items failed Neo4j but raw content is in ChromaDB"
        
        logger.info(f"[INGEST TOOL] Final result: {len(stored)} items stored")
        return json.dumps(result)
        
    except Exception as e:
        logger.error(f"[INGEST TOOL] Extraction failed: {e}")
        return json.dumps({
            "ingested": 0,
            "error": str(e),
            "note": "Raw content stored in ChromaDB, but extraction failed"
        })


@tool
def validate_content(content: str) -> str:
    """Check if content has data worth storing."""
    if len(content.strip()) < 30:
        return "SKIP: too short"
    
    # Always process Excel
    if "Excel:" in content or "[SHEET:" in content:
        return "PROCESS: Excel data"
    
    # Check keywords
    keywords = ["decided", "decision", "expense", "revenue", "audit", "project", "task"]
    if any(k in content.lower() for k in keywords):
        return "PROCESS: data found"
    
    return "SKIP: no data patterns"
