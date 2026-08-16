import logging
from core.llm import get_llm
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage
from tools.neo import search_decisions
from tools.chroma import search_raw_memory

logger = logging.getLogger(__name__)

tools = [search_decisions, search_raw_memory]
tools_map = {t.name: t for t in tools}



SYSTEM = """You are an organizational memory assistant.
Use search_decisions to find structured decisions from Neo4j.
Use search_raw_memory to find raw context, evidence and details from documents and chats.

CRITICAL RULES:
1. ONLY answer based on the data returned from the tools
2. If source_filter is active, you MUST pass source_filter to ALL tool calls
3. If the first search returns no results, RETRY with different, shorter, or more specific keywords
   - For audio/meeting questions: try "meeting", "discussion", "decision", "agenda", or topic keywords
   - For broad questions like "what happened": use search_raw_memory with a short keyword from the topic
   - Only say "No information found" after at least 2 different search attempts all return empty
4. NEVER make up or infer information not present in the tool results
5. NEVER use general knowledge - ONLY use the retrieved data
6. ALWAYS try search_decisions first, then search_raw_memory for additional context
7. For "explain", "summarize", or "what happened" questions: call search_raw_memory and synthesize the content
8. NEVER return raw transcripts verbatim - synthesize and summarize in clear prose
9. When source_filter is set, IGNORE all results from other sources even if they seem relevant

Be concise and direct. Answer ONLY what was asked:
   - If asked "who", give names only
   - If asked "why", give reasons only
   - If asked "what", give the decision only
   - If asked "when", give the timeline only

For comprehensive questions ("explain", "tell me about", "summarize", "what happened"), provide a full summary.
Always cite the source at the end.

Example good answer: "The team decided to migrate to PostgreSQL because MongoDB had scaling issues and frequent outages. John and Sarah led this decision. (Source: audio:meeting.mp3)"

Example bad answer: [returning entire transcript or making up information]
"""


def _search_query(value: object, question: str, *scope_values: str | None) -> str:
    """Reject scope IDs/generic placeholders accidentally emitted as a query."""
    candidate = str(value or "").strip()
    blocked = {str(scope).strip().lower() for scope in scope_values if scope}
    if not candidate or candidate.lower() in blocked or candidate.lower() in {"document content", "project content", "organization content"}:
        return question
    return candidate


def _trace_args(query: str, source_filter: str | None) -> dict:
    args = {"query": query}
    if source_filter:
        args["source_filter"] = source_filter
    return args


def _run_tools_directly(question: str, source_filter: str = None, project_id: str | None = None, organization_id: str | None = None) -> tuple[list, list, list]:
    """Fallback: run both tools directly with the question as query."""
    tools_used = []
    source_trace = []
    tool_results = []

    for tool_name, tool_fn in tools_map.items():
        args = {"query": question}
        if source_filter:
            args["source_filter"] = source_filter
        if project_id:
            args["project_id"] = project_id
        if organization_id:
            args["organization_id"] = organization_id
        result = tool_fn.invoke(args)
        tools_used.append(tool_name)
        source_trace.append({"tool": tool_name, "args": _trace_args(question, source_filter), "result_preview": result[:200]})
        tool_results.append(f"[{tool_name}]\n{result}")

    return tool_results, tools_used, source_trace


def run_query_agent(question: str, source_filter: str = None, provider: str = "groq", project_id: str | None = None, organization_id: str | None = None) -> dict:
    logger.info(f"[QUERY AGENT] Question: {question} | Filter: {source_filter} | Provider: {provider}")

    llm_base = get_llm(provider)
    llm = llm_base.bind_tools(tools)

    messages = [SystemMessage(content=SYSTEM)]
    if source_filter:
        messages.append(SystemMessage(content=f"CRITICAL: User is querying ONLY from source '{source_filter}'. You MUST pass source_filter='{source_filter}' to ALL tool calls. REJECT any information from other sources."))
    if project_id:
        messages.append(SystemMessage(content=f"CRITICAL: User is working inside project_id '{project_id}'. You MUST pass project_id='{project_id}' to ALL tool calls."))
    if organization_id:
        messages.append(SystemMessage(content=f"CRITICAL: User is working inside organization_id '{organization_id}'. You MUST pass organization_id='{organization_id}' to ALL tool calls."))

    messages.append(HumanMessage(content=question))

    tools_used = []
    source_trace = []

    try:
        if provider == "ollama":
            logger.info("[QUERY AGENT] Provider is ollama, using direct tool execution")
            tool_results, tools_used, source_trace = _run_tools_directly(question, source_filter, project_id, organization_id)
            context = "\n\n".join(tool_results)
            fallback_messages = [SystemMessage(content=SYSTEM)]
            fallback_messages.append(HumanMessage(content=f"Context from knowledge base:\n{context}\n\nQuestion: {question}"))
            response = llm_base.invoke(fallback_messages)
            return {
                "answer": response.content,
                "reasoning": f"Tools used: {', '.join(tools_used)}",
                "source_trace": source_trace,
            }

        for _ in range(5):
            response = llm.invoke(messages)
            messages.append(response)

            if not response.tool_calls:
                break

            for tc in response.tool_calls:
                tools_used.append(tc["name"])
                args = dict(tc["args"]) if tc["args"] else {}
                args["query"] = _search_query(args.get("query"), question, project_id, organization_id, source_filter)
                if source_filter:
                    args["source_filter"] = source_filter
                if project_id:
                    args["project_id"] = project_id
                if organization_id:
                    args["organization_id"] = organization_id
                logger.info(f"[QUERY AGENT] → tool: {tc['name']} args={args}")
                result = tools_map[tc["name"]].invoke(args)
                source_trace.append({
                    "tool": tc["name"], "args": _trace_args(args["query"], source_filter),
                    "result_preview": result[:200] if len(result) > 200 else result,
                })
                messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))

    except Exception as e:
        if "tool_use_failed" in str(e) or "400" in str(e):
            logger.warning(f"[QUERY AGENT] Tool call failed, falling back to direct tool execution: {e}")
            tool_results, tools_used, source_trace = _run_tools_directly(question, source_filter, project_id, organization_id)
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
