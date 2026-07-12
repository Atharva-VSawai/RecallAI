import logging
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage
from core.config import settings
from tools.neo import search_decisions
from tools.chroma import search_raw_memory

logger = logging.getLogger(__name__)

tools = [search_decisions, search_raw_memory]
tools_map = {t.name: t for t in tools}

llm_base = ChatGroq(
    api_key=settings.groq_api_key,
    model_name="llama-3.3-70b-versatile",
    temperature=0,
)
llm = llm_base.bind_tools(tools)

SYSTEM = """You are an organizational memory assistant.
Use search_decisions to find structured decisions from Neo4j.
Use search_raw_memory to find raw context, evidence and details from documents and chats.

CRITICAL RULES:
1. ONLY answer based on the data returned from the tools
2. If source_filter is active, you MUST ONLY use information from that EXACT source - NEVER mix in data from other sources
3. If tools return no results for the filtered source, say "No information found in [filename]"
4. NEVER make up or infer information not present in the tool results
5. NEVER use general knowledge - ONLY use the retrieved data
6. ALWAYS prioritize search_decisions results - these contain the extracted, structured information
7. Use search_raw_memory ONLY for additional context or when search_decisions returns nothing
8. NEVER return raw transcripts or long document excerpts - synthesize and summarize
9. When source_filter is set, IGNORE all results from other sources even if they seem relevant

Be concise and direct. Answer ONLY what was asked:
   - If asked "who", give names only
   - If asked "why", give reasons only
   - If asked "what", give the decision only
   - If asked "when", give the timeline only

Only provide full details if the user asks for comprehensive information or "tell me about" or "explain".
Always cite the source at the end.

Example good answer: "The team decided to migrate to PostgreSQL because MongoDB had scaling issues and frequent outages. John and Sarah led this decision. (Source: audio:meeting.mp3)"

Example bad answer: [returning entire transcript or making up information]
"""


def _run_tools_directly(question: str, source_filter: str = None) -> tuple[list, list]:
    """Fallback: run both tools directly with the question as query."""
    tools_used = []
    source_trace = []
    tool_results = []

    for tool_name, tool_fn in tools_map.items():
        args = {"query": question}
        if source_filter:
            args["source_filter"] = source_filter
        result = tool_fn.invoke(args)
        tools_used.append(tool_name)
        source_trace.append({"tool": tool_name, "args": args, "result_preview": result[:200]})
        tool_results.append(f"[{tool_name}]\n{result}")

    return tool_results, tools_used, source_trace


def run_query_agent(question: str, source_filter: str = None) -> dict:
    logger.info(f"[QUERY AGENT] Question: {question} | Filter: {source_filter}")

    messages = [SystemMessage(content=SYSTEM)]
    if source_filter:
        messages.append(SystemMessage(content=f"CRITICAL: User is querying ONLY from source '{source_filter}'. You MUST pass source_filter='{source_filter}' to ALL tool calls. REJECT any information from other sources."))

    messages.append(HumanMessage(content=question))

    tools_used = []
    source_trace = []

    try:
        for _ in range(3):
            response = llm.invoke(messages)
            messages.append(response)

            if not response.tool_calls:
                break

            for tc in response.tool_calls:
                tools_used.append(tc["name"])
                args = dict(tc["args"]) if tc["args"] else {}
                if source_filter:
                    args["source_filter"] = source_filter
                logger.info(f"[QUERY AGENT] → tool: {tc['name']} args={args}")
                result = tools_map[tc["name"]].invoke(args)
                source_trace.append({
                    "tool": tc["name"], "args": args,
                    "result_preview": result[:200] if len(result) > 200 else result,
                })
                messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))

    except Exception as e:
        if "tool_use_failed" in str(e) or "400" in str(e):
            logger.warning(f"[QUERY AGENT] Tool call failed, falling back to direct tool execution: {e}")
            tool_results, tools_used, source_trace = _run_tools_directly(question, source_filter)
            context = "\n\n".join(tool_results)
            fallback_messages = [SystemMessage(content=SYSTEM)]
            fallback_messages.append(HumanMessage(content=f"Context from knowledge base:\n{context}\n\nQuestion: {question}"))
            response = llm_base.invoke(fallback_messages)
            return {
                "answer": response.content,
                "reasoning": f"Tools used (fallback): {', '.join(tools_used)}",
                "source_trace": source_trace,
            }
        raise

    return {
        "answer": messages[-1].content,
        "reasoning": f"Tools used: {', '.join(tools_used) if tools_used else 'context only'}",
        "source_trace": source_trace,
    }
