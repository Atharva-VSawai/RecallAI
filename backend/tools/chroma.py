from typing import Optional
from langchain_core.tools import StructuredTool
from pydantic import BaseModel
from db.chroma import chroma_search


class SearchRawMemoryInput(BaseModel):
    query: str
    source_filter: Optional[str] = None


def _search_raw_memory(query: str, source_filter: Optional[str] = None) -> str:
    docs = chroma_search(query, k=3, source_filter=source_filter)
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
