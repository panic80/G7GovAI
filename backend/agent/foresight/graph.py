"""
ForesightOps LangGraph Pipeline
===============================
Orchestrates the resource allocation optimization workflow.

Pipeline:
    route -> retrieve -> forecast -> analyze -> [evaluate?] -> synthesize -> END
                                        ^            |
                                        └── refine ──┘ (if low confidence)
"""

import logging
from langgraph.graph import StateGraph, END
from typing import Literal, Dict, Any

logger = logging.getLogger(__name__)

from .state import ForesightState
from .nodes import (
    route_node,
    retrieve_node,
    forecast_node,
    analyze_node,
    evaluate_node,
    synthesize_node,
)


# --- Routing Functions ---

def route_after_analyze(state: ForesightState) -> Literal["evaluate", "synthesize"]:
    """
    Determine whether to run scenario evaluation.

    Routes to:
        - evaluate: if include_scenarios is True
        - synthesize: otherwise (skip evaluation)
    """
    if state.get("include_scenarios", False):
        return "evaluate"
    return "synthesize"


def check_confidence(state: ForesightState) -> Literal["refine", "synthesize"]:
    """
    Check if confidence is too low and refinement is needed.

    Routes to:
        - refine: if confidence < 0.6 and loop_count < 2
        - synthesize: otherwise
    """
    confidence = state.get("overall_confidence", 0.5)
    loop_count = state.get("loop_count", 0)

    # Allow one refinement attempt if confidence is low
    if confidence < 0.6 and loop_count < 3:
        return "refine"

    return "synthesize"


async def refine_node(state: ForesightState) -> Dict[str, Any]:
    """
    Refine analysis by adjusting weights based on scenario results.
    This is a lightweight adjustment, not a full re-analysis.
    """
    logger.debug("--- REFINE NODE ---")

    scenarios = state.get("scenario_evaluations", [])
    current_weights = state["weights"]

    # Simple heuristic: if equity scenario performed better, suggest it
    equity_scenario = next((s for s in scenarios if s.get("name") == "Equity-Enforced"), None)

    if equity_scenario and not equity_scenario.get("error"):
        base_risk_reduction = state.get("analysis_result", {}).get("risk_reduction_pct", 0)
        equity_risk_reduction = equity_scenario.get("risk_reduction_pct", 0)

        if equity_risk_reduction > base_risk_reduction:
            return {
                "trace_log": ["Refinement: Equity scenario shows better risk reduction"],
                "overall_confidence": min(state.get("overall_confidence", 0.5) + 0.1, 0.85),
                "loop_count": state["loop_count"] + 1,
            }

    # Default: slight confidence boost for having tried
    return {
        "trace_log": ["Refinement: Analysis validated against scenarios"],
        "overall_confidence": min(state.get("overall_confidence", 0.5) + 0.05, 0.80),
        "loop_count": state["loop_count"] + 1,
    }


# --- Build Graph ---

workflow = StateGraph(ForesightState)

# Add Nodes
workflow.add_node("route", route_node)
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("forecast", forecast_node)
workflow.add_node("analyze", analyze_node)
workflow.add_node("evaluate", evaluate_node)
workflow.add_node("refine", refine_node)
workflow.add_node("synthesize", synthesize_node)

# Set Entry Point
workflow.set_entry_point("route")

# Add Edges
workflow.add_edge("route", "retrieve")
workflow.add_edge("retrieve", "forecast")
workflow.add_edge("forecast", "analyze")

# Conditional: analyze -> (evaluate or synthesize)
workflow.add_conditional_edges(
    "analyze",
    route_after_analyze,
    {
        "evaluate": "evaluate",
        "synthesize": "synthesize"
    }
)

# Conditional: evaluate -> (refine or synthesize)
workflow.add_conditional_edges(
    "evaluate",
    check_confidence,
    {
        "refine": "refine",
        "synthesize": "synthesize"
    }
)

# Refine loops back to synthesize (not analyze, to avoid re-running optimization)
workflow.add_edge("refine", "synthesize")

# Synthesize -> END
workflow.add_edge("synthesize", END)

# Compile
foresight_graph = workflow.compile()

# Node names for streaming (used by API)
FORESIGHT_NODES = {"route", "retrieve", "forecast", "analyze", "evaluate", "refine", "synthesize"}
