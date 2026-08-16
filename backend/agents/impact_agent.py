import logging
from core.llm import get_llm
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage
from tools.impact_tools import find_related_decisions, find_decisions_by_person
from tools.chroma import search_raw_memory

logger = logging.getLogger(__name__)

tools = [find_related_decisions, find_decisions_by_person, search_raw_memory]
tools_map = {t.name: t for t in tools}



SYSTEM = """You are an impact analysis agent.
You answer "what if" and "what breaks" questions about organizational decisions.

CRITICAL RULES:
1. ONLY answer based on the data returned from the tools
2. If source_filter is active, you MUST pass source_filter to ALL tool calls
3. If the first search returns no results, RETRY with different or shorter keywords before giving up
   - Only say "No information found" after at least 2 different search attempts all return empty
4. NEVER make up or infer information not present in the tool results
5. NEVER use general knowledge - ONLY use the retrieved data
6. NEVER return raw transcripts - synthesize and analyze
7. When source_filter is set, IGNORE all results from other sources even if they seem relevant

Steps:
1. Use find_related_decisions to find all decisions connected to the topic
2. Use search_raw_memory to find raw context and evidence
3. Use find_decisions_by_person if a person is mentioned
4. Analyze the chain of decisions and reason about what would be affected
5. Give a clear, concise impact assessment with:
   - What would break or change
   - Who would be affected
   - Risk level (Low / Medium / High)

Be direct and concise. Focus on the specific impact being asked about.
Always cite sources."""


def _search_topic(value: object, question: str, *scope_values: str | None) -> str:
    candidate = str(value or "").strip()
    blocked = {str(scope).strip().lower() for scope in scope_values if scope}
    if not candidate or candidate.lower() in blocked or candidate.lower() in {"document content", "project content", "organization content"}:
        return question
    return candidate


def _trace_args(key: str, value: str, source_filter: str | None) -> dict:
    args = {key: value}
    if source_filter:
        args["source_filter"] = source_filter
    return args


def _run_tools_directly(question: str, source_filter: str = None, project_id: str | None = None, organization_id: str | None = None) -> tuple[list, list, list]:
    tools_used, source_trace, tool_results = [], [], []
    for tool_name, tool_fn in tools_map.items():
        key = "topic" if tool_name == "find_related_decisions" else ("person_name" if tool_name == "find_decisions_by_person" else "query")
        args = {key: question}
        if source_filter:
            args["source_filter"] = source_filter
        if project_id:
            args["project_id"] = project_id
        if organization_id:
            args["organization_id"] = organization_id
        result = tool_fn.invoke(args)
        tools_used.append(tool_name)
        source_trace.append({"tool": tool_name, "args": _trace_args(key, question, source_filter), "result_preview": result[:200]})
        tool_results.append(f"[{tool_name}]\n{result}")
    return tool_results, tools_used, source_trace


def run_impact_agent(question: str, source_filter: str = None, provider: str = "groq", project_id: str | None = None, organization_id: str | None = None) -> dict:
    logger.info(f"[IMPACT AGENT] Question: {question} | Filter: {source_filter} | Provider: {provider}")

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
            logger.info("[IMPACT AGENT] Provider is ollama, using direct tool execution")
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
                key = "topic" if tc["name"] == "find_related_decisions" else ("person_name" if tc["name"] == "find_decisions_by_person" else "query")
                args[key] = _search_topic(args.get(key), question, project_id, organization_id, source_filter)
                if source_filter:
                    args["source_filter"] = source_filter
                if project_id:
                    args["project_id"] = project_id
                if organization_id:
                    args["organization_id"] = organization_id
                logger.info(f"[IMPACT AGENT] → tool: {tc['name']} args={args}")
                result = tools_map[tc["name"]].invoke(args)
                source_trace.append({
                    "tool": tc["name"], "args": _trace_args(key, args[key], source_filter),
                    "result_preview": result[:200] if len(result) > 200 else result,
                })
                messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))

    except Exception as e:
        if "tool_use_failed" in str(e) or "400" in str(e):
            logger.warning(f"[IMPACT AGENT] Tool call failed, falling back to direct execution: {e}")
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
