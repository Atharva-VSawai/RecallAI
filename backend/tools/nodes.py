"""State definition for the experimental graph-builder scaffold.

Phase 1 freeze marker: retained for historical compatibility only. The active
agent flow currently uses backend/agents and this file must not be extended
without Phase 2 review.
"""

from typing import TypedDict

class AgentState(TypedDict):
    messages: list
