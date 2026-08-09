import logging
import re
from core.llm import get_llm
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)



SYSTEM = """Classify the user question into one of two types:
- IMPACT: questions about what would happen, what breaks, what changes, risks, what if scenarios
- QUERY: questions about why something was decided, who decided, what was decided, history

Reply with ONLY one word: IMPACT or QUERY"""


_DIRECT_IMPACT_PATTERNS = (
    re.compile(r"\bwhat\s+if\b", re.IGNORECASE),
    re.compile(r"\bwhat\s+(?:happens|breaks|changes|fails)\s+if\b", re.IGNORECASE),
    re.compile(r"\bwhat\s+(?:would|will|could|might)\s+(?:happen|break|change|fail|be\s+affected)\b", re.IGNORECASE),
    re.compile(r"\b(?:risk|risks|consequence|consequences)\s+of\b", re.IGNORECASE),
    re.compile(r"\bimpact\s+of\s+(?!the\s+(?:decision|meeting)|this\s+(?:decision|meeting))", re.IGNORECASE),
)
_CONDITIONAL_IMPACT_PATTERN = re.compile(
    r"\b(?:if\s+we|if\s+(?:it|this|that)\s+(?:is|were|was)|would\s+it)\b.*\b(?:remove|drop|delay|change|replace|migrate|disable|break|fail|affect)\b",
    re.IGNORECASE,
)
_FACTUAL_QUERY_PATTERN = re.compile(
    r"^\s*(?:who|why|when|where|which|what\s+(?:was|is|did|does)|how\s+(?:did|does|is)|list|find|show|tell\s+me|explain)\b",
    re.IGNORECASE,
)


def _deterministic_route(question: str) -> str | None:
    """Classify only high-confidence intent; leave ambiguity to the LLM."""
    normalized = " ".join(question.split())
    if not normalized:
        return None
    if any(pattern.search(normalized) for pattern in _DIRECT_IMPACT_PATTERNS):
        return "IMPACT"
    if _CONDITIONAL_IMPACT_PATTERN.search(normalized):
        return "IMPACT"
    if _FACTUAL_QUERY_PATTERN.search(normalized):
        return "QUERY"
    return None


def route(question: str, provider: str = "groq") -> str:
    deterministic = _deterministic_route(question)
    if deterministic:
        logger.info("[ROUTER] deterministic '%s' -> %s", question[:60], deterministic)
        return deterministic

    llm = get_llm(provider)
    response = llm.invoke([SystemMessage(content=SYSTEM), HumanMessage(content=question)])
    label = response.content.strip().upper()
    result = "IMPACT" if "IMPACT" in label else "QUERY"
    logger.info(f"[ROUTER] '{question[:60]}' → {result}")
    return result


def run(question: str, source_filter: str = None, provider: str = "groq", project_id: str | None = None, organization_id: str | None = None) -> dict:
    agent_type = route(question, provider=provider)

    if agent_type == "IMPACT":
        from agents.impact_agent import run_impact_agent
        result = run_impact_agent(question, source_filter=source_filter, provider=provider, project_id=project_id, organization_id=organization_id)
    else:
        from agents.query_agent import run_query_agent
        result = run_query_agent(question, source_filter=source_filter, provider=provider, project_id=project_id, organization_id=organization_id)

    result["agent_used"] = agent_type
    return result
