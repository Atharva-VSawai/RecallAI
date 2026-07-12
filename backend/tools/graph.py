from langgraph.graph import StateGraph
from agents.nodes import AgentState

def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)
    # add nodes and edges here
    return graph.compile()
