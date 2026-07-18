import logging
from core.llm import get_llm
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)



SYSTEM = """Classify the user question into one of two types:
- IMPACT: questions about what would happen, what breaks, what changes, risks, what if scenarios
- QUERY: questions about why something was decided, who decided, what was decided, history

Reply with ONLY one word: IMPACT or QUERY"""


def route(question: str, provider: str = "groq") -> str:
    llm = get_llm(provider)
    response = llm.invoke([SystemMessage(content=SYSTEM), HumanMessage(content=question)])
    label = response.content.strip().upper()
    result = "IMPACT" if "IMPACT" in label else "QUERY"
    logger.info(f"[ROUTER] '{question[:60]}' → {result}")
    return result


def run(question: str, source_filter: str = None, provider: str = "groq") -> dict:
    agent_type = route(question, provider=provider)

    if agent_type == "IMPACT":
        from agents.impact_agent import run_impact_agent
        result = run_impact_agent(question, source_filter=source_filter, provider=provider)
    else:
        from agents.query_agent import run_query_agent
        result = run_query_agent(question, source_filter=source_filter, provider=provider)

    result["agent_used"] = agent_type
    return result
