"""Legacy standalone agent path.

Phase 1 freeze marker: current API routes use agents.router instead. Do not
extend this module for new features; review or remove it during Phase 2 after
manual compatibility verification.
"""

import logging
import json
from core.llm import get_llm
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from tools.neo import search_decisions

logger = logging.getLogger(__name__)

tools = [search_decisions]



SYSTEM = """You are an organizational memory assistant.
Use the search_decisions tool to find relevant decisions before answering.
In your final answer always include: what was decided, why, who was involved, alternatives considered, and impact."""


def run_agent(question: str, provider: str = "groq") -> dict:
    logger.info(f"[AGENT] Question: {question} | Provider: {provider}")
    llm = get_llm(provider).bind_tools(tools)

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
