from typing import Optional
from langchain_core.tools import StructuredTool
from pydantic import BaseModel
from db.chroma import chroma_search


class SearchRawMemoryInput(BaseModel):
    query: str
    source_filter: Optional[str] = None
    project_id: Optional[str] = None
    organization_id: Optional[str] = None


def _search_raw_memory(
    query: str,
    source_filter: Optional[str] = None,
    project_id: Optional[str] = None,
    organization_id: Optional[str] = None,
) -> str:
    # organization_id and project_id are required by chroma_search for tenant isolation.
    # When not provided (e.g. missing context), fall back gracefully instead of crashing.
    if not organization_id or not project_id:
        return "No relevant content found in raw memory."
    docs = chroma_search(
        query,
        organization_id=organization_id,
        project_id=project_id,
        k=3,
        source_filter=source_filter,
    )
    if not docs:
        return "No relevant content found in raw memory."
    results = []
    for d in docs:
        content = d['page_content']
        if len(content) > 300:
            content = content[:300] + "..."
        results.append(
            f"Source: {d['metadata'].get('source', 'unknown')}\n"
            f"Content: {content}"
        )
    return "\n---\n".join(results)


search_raw_memory = StructuredTool.from_function(
    func=_search_raw_memory,
    name="search_raw_memory",
    description="Search raw document and chat content semantically. Use to find context, evidence, and details that may not be captured as structured decisions.",
    args_schema=SearchRawMemoryInput,
)
