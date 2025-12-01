"""
ForesightOps State Definition
=============================
State management for the resource allocation optimization agent.

Pipeline:
1. ROUTE      -> Classify query vs structured params
2. RETRIEVE   -> Fetch assets from database
3. FORECAST   -> Generate condition and demand predictions
4. ANALYZE    -> Run OR-Tools optimization
5. EVALUATE   -> Optional scenario comparison
6. SYNTHESIZE -> Format output for frontend
"""

from typing import TypedDict, List, Dict, Any, Optional, Annotated, Literal
import operator
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from core.constants import (
    DEFAULT_BUDGET,
    DEFAULT_PLANNING_HORIZON_YEARS,
    DEFAULT_WEIGHTS,
)


class ForesightState(TypedDict):
    """
    State for ForesightOps resource allocation optimizer.

    Accumulator fields (append-only):
        - retrieved_assets: Assets fetched from database
        - risk_scores: Computed risk metrics per asset
        - scenario_evaluations: Results from scenario comparisons
        - trace_log: Execution trace for UI transparency

    Control fields:
        - loop_count: Safety counter for refinement loops
        - optimization_path: Selected optimization strategy

    Output fields:
        - analysis_result: Summary statistics
        - recommendations: Final allocation recommendations
        - overall_confidence: Confidence score (0-1)
    """

    # === INPUT ===
    query: str  # Natural language query (optional)
    language: str  # "en" or "fr"
    budget_total: float  # Total budget for allocation
    planning_horizon_years: int  # Planning horizon (default 5)
    weights: Dict[str, float]  # Priority weights {"risk": 0.6, "coverage": 0.4}
    region_filter: Optional[List[str]]  # Filter by region codes
    asset_type_filter: Optional[List[str]]  # Filter by asset types
    include_scenarios: bool  # Run scenario analysis
    enforce_equity: bool  # Enforce regional equity constraints

    # === PROCESSING (ACCUMULATORS) ===
    retrieved_assets: Annotated[List[Dict[str, Any]], operator.add]
    risk_scores: Annotated[List[Dict[str, Any]], operator.add]
    scenario_evaluations: Annotated[List[Dict[str, Any]], operator.add]
    trace_log: Annotated[List[str], operator.add]

    # === FORECASTING ===
    condition_forecasts: Annotated[List[Dict[str, Any]], operator.add]  # Per-asset condition predictions
    demand_forecasts: Annotated[List[Dict[str, Any]], operator.add]  # Per-asset demand projections
    risk_timeline: Optional[Dict[str, Any]]  # Timeline of when assets will fail
    external_factors: Optional[Dict[str, Any]]  # Weather, demographics impact
    anticipatory_score: Optional[Dict[str, Any]]  # Proactive vs reactive metrics
    bottlenecks: Annotated[List[Dict[str, Any]], operator.add]  # Identified bottlenecks

    # === STATE CONTROL ===
    loop_count: int
    optimization_path: Literal["query_driven", "data_driven", ""]

    # === OUTPUT ===
    analysis_result: Optional[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    overall_confidence: float
    error: Optional[str]


def create_initial_state(
    query: str = "",
    language: str = "en",
    budget_total: float = DEFAULT_BUDGET,
    planning_horizon_years: int = DEFAULT_PLANNING_HORIZON_YEARS,
    weights: Optional[Dict[str, float]] = None,
    region_filter: Optional[List[str]] = None,
    asset_type_filter: Optional[List[str]] = None,
    include_scenarios: bool = False,
    enforce_equity: bool = False,
) -> ForesightState:
    """
    Factory function to create initial ForesightState.

    Args:
        query: Natural language query (optional)
        language: Response language ("en" or "fr")
        budget_total: Total budget for allocation (default $10M)
        planning_horizon_years: Planning horizon (default 5 years)
        weights: Priority weights (default risk=0.6, coverage=0.4)
        region_filter: Optional list of region codes to include
        asset_type_filter: Optional list of asset types to include
        include_scenarios: Run scenario comparison (default False)
        enforce_equity: Enforce regional equity constraints (default False)

    Returns:
        Initialized ForesightState
    """
    return ForesightState(
        # Input
        query=query,
        language=language,
        budget_total=budget_total,
        planning_horizon_years=planning_horizon_years,
        weights=weights or DEFAULT_WEIGHTS,
        region_filter=region_filter,
        asset_type_filter=asset_type_filter,
        include_scenarios=include_scenarios,
        enforce_equity=enforce_equity,

        # Processing (empty accumulators)
        retrieved_assets=[],
        risk_scores=[],
        scenario_evaluations=[],
        trace_log=[],

        # Forecasting (empty)
        condition_forecasts=[],
        demand_forecasts=[],
        risk_timeline=None,
        external_factors=None,
        anticipatory_score=None,
        bottlenecks=[],

        # Control
        loop_count=0,
        optimization_path="",

        # Output
        analysis_result=None,
        recommendations=[],
        overall_confidence=0.0,
        error=None,
    )
