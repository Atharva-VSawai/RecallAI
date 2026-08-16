from typing import Optional
from langchain_core.tools import StructuredTool
from pydantic import BaseModel
from db.neo import neo_search


class SearchDecisionsInput(BaseModel):
    query: str
    source_filter: Optional[str] = None
    project_id: Optional[str] = None
    organization_id: Optional[str] = None


def _search_decisions(
    query: str,
    source_filter: Optional[str] = None,
    project_id: Optional[str] = None,
    organization_id: Optional[str] = None,
) -> str:
    # neo_search uses fulltext index which handles missing org/project gracefully,
    # but we still pass them for proper tenant isolation.
    records = neo_search(
        query,
        organization_id=organization_id,
        project_id=project_id,
        source_filter=source_filter,
    )
    if not records:
        return f"No decisions found for: {query}"
    output = []
    for r in records:
        output.append(
            f"Decision: {r['decision']}\n"
            f"Topic: {r['topic']}\n"
            f"Reasons: {', '.join(r['reasons']) if r['reasons'] else 'N/A'}\n"
            f"People: {', '.join(r['people']) if r['people'] else 'N/A'}\n"
            f"Alternatives: {', '.join(r['alternatives']) if r['alternatives'] else 'N/A'}\n"
            f"Impact: {r['impact']}\n"
            f"Source: {r['source']} | Timestamp: {r['timestamp']}\n"
            f"ID: {r['id']}"
        )
    return "\n---\n".join(output)


search_decisions = StructuredTool.from_function(
    func=_search_decisions,
    name="search_decisions",
    description="Search organizational memory for decisions, reasons, people and alternatives related to a topic or question.",
    args_schema=SearchDecisionsInput,
)
