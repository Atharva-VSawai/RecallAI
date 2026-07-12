import logging
import json
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from core.config import settings
from tools.neo import search_decisions

logger = logging.getLogger(__name__)

tools = [search_decisions]

llm = ChatGroq(
    api_key=settings.groq_api_key,
    model_name="llama-3.3-70b-versatile",
    temperature=0,
).bind_tools(tools)

SYSTEM = """You are an organizational memory assistant.
Use the search_decisions tool to find relevant decisions before answering.
In your final answer always include: what was decided, why, who was involved, alternatives considered, and impact."""


def run_agent(question: str) -> dict:
    logger.info(f"[AGENT] Question: {question}")

    messages = [SystemMessage(content=SYSTEM), HumanMessage(content=question)]
    tools_used = []
    source_trace = []

    # max 3 iterations to avoid infinite loop
    for _ in range(3):
        response = llm.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            break

        for tc in response.tool_calls:
            tools_used.append(tc["name"])
            logger.info(f"[AGENT] Calling tool: {tc['name']} args={tc['args']}")

            # execute tool
            tool_result = search_decisions.invoke(tc["args"])

            source_trace.append({
                "tool": tc["name"],
                "args": tc["args"],
                "result_preview": tool_result[:300],
            })

            messages.append(ToolMessage(content=tool_result, tool_call_id=tc["id"]))

    answer = messages[-1].content
    logger.info(f"[AGENT] Done. Tools used: {tools_used}")

    return {
        "answer": answer,
        "reasoning": f"Tools used: {', '.join(tools_used) if tools_used else 'answered from context'}",
        "source_trace": source_trace,
    }
