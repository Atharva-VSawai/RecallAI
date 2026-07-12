from typing import Optional
from langchain_core.tools import StructuredTool
from pydantic import BaseModel
from db.neo import neo_impact_search, neo_search as _neo_search


class TopicInput(BaseModel):
    topic: str
    source_filter: Optional[str] = None


class PersonInput(BaseModel):
    person_name: str
    source_filter: Optional[str] = None


def _find_related_decisions(topic: str, source_filter: Optional[str] = None) -> str:
    records = neo_impact_search(topic, source_filter=source_filter)
    if not records:
        return f"No related decisions found for: {topic}"
    output = []
    for r in records:
        output.append(
            f"Decision: {r['decision']}\n"
            f"Topic: {r['topic']}\n"
            f"Reasons: {', '.join(r['reasons']) if r['reasons'] else 'N/A'}\n"
            f"People: {', '.join(r['people']) if r['people'] else 'N/A'}\n"
            f"Alternatives considered: {', '.join(r['alternatives']) if r['alternatives'] else 'N/A'}\n"
            f"Known impact: {r['impact']}\n"
            f"Source: {r['source']}"
        )
    return "\n---\n".join(output)


def _find_decisions_by_person(person_name: str, source_filter: Optional[str] = None) -> str:
    records = _neo_search(person_name, source_filter=source_filter)
    if not records:
        return f"No decisions found involving: {person_name}"
    output = []
    for r in records:
        output.append(
            f"Decision: {r['decision']}\n"
            f"People involved: {', '.join(r['people']) if r['people'] else 'N/A'}\n"
            f"Reason: {', '.join(r['reasons']) if r['reasons'] else 'N/A'}\n"
            f"Impact: {r['impact']}"
        )
    return "\n---\n".join(output)


find_related_decisions = StructuredTool.from_function(
    func=_find_related_decisions,
    name="find_related_decisions",
    description="Find all decisions related to a topic, system, or person. Use to understand what is connected before simulating impact.",
    args_schema=TopicInput,
)

find_decisions_by_person = StructuredTool.from_function(
    func=_find_decisions_by_person,
    name="find_decisions_by_person",
    description="Find all decisions made by or involving a specific person.",
    args_schema=PersonInput,
)
