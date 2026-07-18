"""Experimental graph-builder scaffold.

Phase 1 freeze marker: this module is not part of the active API route path.
Do not use it for new functionality until it is reviewed in Phase 2.
"""

from langgraph.graph import StateGraph
from agents.nodes import AgentState

def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)
    # add nodes and edges here
    return graph.compile()
