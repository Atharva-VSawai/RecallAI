import logging
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from core.config import settings

logger = logging.getLogger(__name__)

_llm = ChatGroq(api_key=settings.groq_api_key, model_name="llama-3.3-70b-versatile", temperature=0)

SYSTEM = """Classify the user question into one of two types:
- IMPACT: questions about what would happen, what breaks, what changes, risks, what if scenarios
- QUERY: questions about why something was decided, who decided, what was decided, history

Reply with ONLY one word: IMPACT or QUERY"""


def route(question: str) -> str:
    response = _llm.invoke([SystemMessage(content=SYSTEM), HumanMessage(content=question)])
    label = response.content.strip().upper()
    result = "IMPACT" if "IMPACT" in label else "QUERY"
    logger.info(f"[ROUTER] '{question[:60]}' → {result}")
    return result


def run(question: str, source_filter: str = None) -> dict:
    agent_type = route(question)

    if agent_type == "IMPACT":
        from agents.impact_agent import run_impact_agent
        result = run_impact_agent(question, source_filter=source_filter)
    else:
        from agents.query_agent import run_query_agent
        result = run_query_agent(question, source_filter=source_filter)

    result["agent_used"] = agent_type
    return result
