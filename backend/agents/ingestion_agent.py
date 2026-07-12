import logging
import json
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from core.config import settings
from tools.ingestion_tools import validate_content, extract_and_store

logger = logging.getLogger(__name__)

tools = [validate_content, extract_and_store]
tools_map = {t.name: t for t in tools}

llm = ChatGroq(
    api_key=settings.groq_api_key,
    model_name="llama-3.3-70b-versatile",
    temperature=0,
).bind_tools(tools)

SYSTEM = """You are an ingestion agent responsible for building organizational memory.
Given raw content:
1. First call validate_content to check if it contains decisions worth storing
2. If result starts with PROCESS: call extract_and_store with the content and source
3. If result starts with SKIP: stop and return why it was skipped
Always use tools. Never answer directly."""


def run_ingestion_agent(content: str, source: str) -> dict:
    logger.info(f"[INGESTION AGENT] source='{source}' len={len(content)}")
    messages = [
        SystemMessage(content=SYSTEM),
        HumanMessage(content=f"Source: {source}\n\nContent:\n{content}"),
    ]

    for _ in range(4):
        response = llm.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            break

        for tc in response.tool_calls:
            logger.info(f"[INGESTION AGENT] → tool: {tc['name']}")
            args = dict(tc["args"]) if tc["args"] else {}
            if tc["name"] == "extract_and_store":
                args["source"] = source
            result = tools_map[tc["name"]].invoke(args)
            messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

    # extract result from tool message
    for msg in reversed(messages):
        if hasattr(msg, "tool_call_id") and hasattr(msg, "content"):
            try:
                parsed = json.loads(msg.content)
                if "ingested" in parsed:
                    return parsed
            except Exception:
                pass

    return {"status": messages[-1].content}
