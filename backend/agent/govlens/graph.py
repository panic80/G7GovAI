from langgraph.graph import StateGraph, END
from typing import Literal

from .state import GovLensState
from .nodes import (
    router_node,
    retrieve_node,
    grade_documents_node,
    rewrite_query_node,
    generate_node,
)

# --- EDGES & LOGIC ---


def route_strategy(
    state: GovLensState,
) -> Literal["simple_retrieve", "complex_retrieve"]:
    """
    Determines the path after the router.
    """
    if state["search_strategy"] == "complex":
        return "complex_retrieve"
    return "simple_retrieve"


def check_relevance(state: GovLensState) -> Literal["generate", "rewrite"]:
    """
    Determines if we have enough info or need to loop.
    """
    # Check the last log entry from the grader (hacky but stateless-friendly)
    last_log = state["trace_log"][-1]

    if "Documents graded as relevant" in last_log:
        return "generate"

    # If the grader failed (e.g., network/LLM issue), skip the rewrite loop
    # and move directly to synthesis to avoid crashing the stream.
    if "error" in last_log.lower():
        return "generate"

    if state["loop_count"] > 3:  # Max 3 retries
        return "generate"

    return "rewrite"


# --- GRAPH CONSTRUCTION ---

workflow = StateGraph(GovLensState)

# Add Nodes
workflow.add_node("router", router_node)
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("grader", grade_documents_node)
workflow.add_node("rewrite", rewrite_query_node)
workflow.add_node("generate", generate_node)

# Set Entry Point
workflow.set_entry_point("router")

# Conditional Edges from Router
workflow.add_conditional_edges(
    "router",
    route_strategy,
    {"simple_retrieve": "retrieve", "complex_retrieve": "retrieve"},
)


# Edge: Retrieve -> (Simple vs Complex Logic)
def post_retrieve_route(state: GovLensState) -> Literal["generate", "grader"]:
    if state["search_strategy"] == "complex":
        return "grader"
    return "generate"


workflow.add_conditional_edges(
    "retrieve", post_retrieve_route, {"generate": "generate", "grader": "grader"}
)

# Edge: Grader -> (Generate vs Rewrite)
workflow.add_conditional_edges(
    "grader", check_relevance, {"generate": "generate", "rewrite": "rewrite"}
)

# Edge: Rewrite -> Retrieve (Loop)
workflow.add_edge("rewrite", "retrieve")

# Edge: Generate -> End
workflow.add_edge("generate", END)

# Compile
govlens_graph = workflow.compile()
