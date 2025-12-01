"""
ForesightOps Pipeline Nodes
===========================
LangGraph nodes for resource allocation optimization.

Nodes:
1. route_node       - Classify query vs structured params
2. retrieve_node    - Fetch assets from database
3. forecast_node    - Generate condition and demand predictions
4. analyze_node     - Run OR-Tools optimization
5. evaluate_node    - Optional scenario comparison
6. synthesize_node  - Format output for frontend
"""

import asyncio
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)
from datetime import date

from .state import ForesightState

# Import database and optimization
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from sql_db import get_session_factory
from foresight_models import Asset, Capacity, ConditionScore
from foresight import generate_infrastructure_data
from optimization_solver import CapitalPlanSolver, AllocationResult

# Import forecasting module
from forecasting.deterioration import predict_condition, get_maintenance_window
from forecasting.demand import forecast_demand, identify_bottlenecks, DemandModel

# Import external data services
from services.mock_external.weather_service import get_weather_service
from services.mock_external.demographics_service import get_demographics_service
from core.constants import (
    SOLVER_TIME_LIMIT_SLOW_MS,
    SOLVER_CONFIDENCE,
    DEFAULT_CONFIDENCE,
    CONFIDENCE_HIGH_THRESHOLD,
    CONFIDENCE_MEDIUM_THRESHOLD,
)


# --- Node 1: ROUTE ---

async def route_node(state: ForesightState) -> Dict[str, Any]:
    """
    Classify the optimization path based on input.

    - query_driven: User provided natural language query
    - data_driven: Using structured parameters (budget, weights, filters)
    """
    logger.debug("--- ROUTE NODE ---")

    query = state.get("query", "").strip()

    if query:
        path = "query_driven"
        reason = f"Natural language query provided: '{query[:50]}...'" if len(query) > 50 else f"Query: '{query}'"
    else:
        path = "data_driven"
        reason = f"Structured params: budget=${state['budget_total']:,.0f}, horizon={state['planning_horizon_years']}yr"

    return {
        "optimization_path": path,
        "trace_log": [f"Router: {path} - {reason}"],
    }


# --- Node 2: RETRIEVE ---

async def retrieve_node(state: ForesightState) -> Dict[str, Any]:
    """
    Fetch assets from database with optional filters.
    Falls back to synthetic data if database is empty.
    """
    logger.debug("--- RETRIEVE NODE ---")

    region_filter = state.get("region_filter") or []
    asset_type_filter = state.get("asset_type_filter") or []

    # Fetch from database (async wrapped)
    assets = await asyncio.to_thread(_fetch_assets_from_db, region_filter, asset_type_filter)

    if not assets:
        # Fallback to synthetic data
        assets = generate_infrastructure_data(20)

        # Apply filters to synthetic data
        if region_filter:
            assets = [a for a in assets if a.get("region") in region_filter]
        if asset_type_filter:
            assets = [a for a in assets if a.get("type") in asset_type_filter]

        source = "synthetic"
    else:
        source = "database"

    return {
        "retrieved_assets": assets,
        "trace_log": [f"Retrieved {len(assets)} assets from {source}"],
        "loop_count": state["loop_count"] + 1,
    }


def _fetch_assets_from_db(
    region_filter: List[str],
    asset_type_filter: List[str]
) -> List[Dict[str, Any]]:
    """Fetch assets from database with filters."""
    session_factory = get_session_factory()
    session = session_factory()
    try:
        query = session.query(Asset)

        # Apply filters
        if region_filter:
            query = query.filter(Asset.region.in_(region_filter))
        if asset_type_filter:
            query = query.filter(Asset.type.in_(asset_type_filter))

        assets = query.all()
        if not assets:
            return []

        today = date.today()
        results = []

        for a in assets:
            # Latest capacity effective today
            cap_value = None
            cap = (
                session.query(Capacity)
                .filter(
                    Capacity.asset_id == a.asset_id,
                    Capacity.effective_start <= today,
                    (Capacity.effective_end.is_(None)) | (Capacity.effective_end >= today),
                )
                .order_by(Capacity.effective_start.desc())
                .first()
            )
            if cap:
                cap_value = cap.capacity_value

            # Latest condition score
            cond = (
                session.query(ConditionScore)
                .filter(ConditionScore.asset_id == a.asset_id)
                .order_by(ConditionScore.observed_date.desc())
                .first()
            )
            condition_score = cond.condition_score if cond else 60

            results.append({
                "id": a.asset_id,
                "name": a.name,
                "type": a.type,
                "region": a.region,
                "age_years": a.design_life or 10,
                "condition_score": condition_score,
                "daily_usage": a.daily_usage or (cap_value or 5000),
                "replacement_cost": a.replacement_cost or 1_000_000,
                "population_growth_rate": a.population_growth_rate or 1.5,
            })

        return results
    except Exception as e:
        logger.error(f"Database fetch error: {type(e).__name__}")
        return []
    finally:
        session.close()


# --- Node 3: FORECAST ---

async def forecast_node(state: ForesightState) -> Dict[str, Any]:
    """
    Generate condition and demand predictions for retrieved assets.

    This is the NEW anticipatory planning node that:
    1. Predicts infrastructure deterioration over time
    2. Forecasts demand based on population/usage trends
    3. Identifies bottlenecks and capacity gaps
    4. Calculates weather and demographic impacts
    """
    logger.debug("--- FORECAST NODE ---")

    assets = state.get("retrieved_assets", [])
    horizon_years = state.get("planning_horizon_years", 5)

    if not assets:
        return {
            "trace_log": ["Forecast: No assets to forecast"],
            "condition_forecasts": [],
            "demand_forecasts": [],
        }

    trace = []
    condition_forecasts = []
    demand_forecasts = []
    risk_timeline = {"years": [], "critical_assets": {}}

    # Get external data services
    weather_svc = get_weather_service()
    demographics_svc = get_demographics_service()

    # Get unique regions for external data
    regions = list(set(a.get("region", "ON-Toronto") for a in assets))
    primary_region = regions[0] if regions else "ON-Toronto"

    # Fetch weather and demographic data
    weather_risk = await asyncio.to_thread(
        weather_svc.get_extreme_weather_risk,
        primary_region,
        date.today().month
    )
    demographics = await asyncio.to_thread(
        demographics_svc.get_demographic_trends,
        primary_region
    )

    trace.append(f"External data: Weather risk={weather_risk.overall_risk}, Demand index={demographics.infrastructure_demand_index:.2f}")

    # Weather impact factor based on risk
    weather_factor = 1.0
    if weather_risk.overall_risk == "Critical":
        weather_factor = 1.4
    elif weather_risk.overall_risk == "High":
        weather_factor = 1.2
    elif weather_risk.overall_risk == "Medium":
        weather_factor = 1.1

    # Process each asset for forecasting
    for asset in assets:
        asset_id = asset.get("id", "unknown")
        asset_type = asset.get("type", "Other")
        asset_region = asset.get("region", primary_region)
        condition = asset.get("condition_score", 70)
        age = asset.get("age_years", 10)
        daily_usage = asset.get("daily_usage", 5000)
        replacement_cost = asset.get("replacement_cost", 1_000_000)

        # Usage factor based on demographics
        usage_factor = 1.0 + (demographics.infrastructure_demand_index - 0.5) * 0.4

        # Generate condition forecast
        try:
            cond_forecast = await asyncio.to_thread(
                predict_condition,
                asset_id,
                asset_type,
                condition,
                age,
                horizon_years,
                weather_factor,
                usage_factor
            )

            condition_forecasts.append({
                "asset_id": asset_id,
                "asset_type": asset_type,
                "current_condition": condition,
                "forecast_points": [
                    {
                        "year": p.date.year,
                        "condition": p.predicted_condition,
                        "failure_prob": p.failure_probability,
                        "maintenance_needed": p.maintenance_recommended
                    }
                    for p in cond_forecast.forecast_points
                ],
                "expected_failure_date": cond_forecast.expected_failure_date.isoformat() if cond_forecast.expected_failure_date else None,
                "years_to_failure": cond_forecast.years_to_failure,
                "deterioration_rate": cond_forecast.deterioration_rate,
            })

            # Track in risk timeline
            if cond_forecast.years_to_failure and cond_forecast.years_to_failure <= horizon_years:
                year_key = str(int(cond_forecast.years_to_failure))
                if year_key not in risk_timeline["critical_assets"]:
                    risk_timeline["critical_assets"][year_key] = []
                risk_timeline["critical_assets"][year_key].append({
                    "asset_id": asset_id,
                    "asset_type": asset_type,
                    "failure_prob": cond_forecast.forecast_points[-1].failure_probability if cond_forecast.forecast_points else 0
                })

        except Exception as e:
            logger.warning(f"Condition forecast failed for {asset_id}: {e}")

        # Generate demand forecast
        try:
            capacity = daily_usage * 1.3  # Assume 30% headroom baseline
            demand_fc = await asyncio.to_thread(
                forecast_demand,
                asset_id,
                asset_type,
                asset_region,
                daily_usage,
                capacity,
                horizon_years
            )

            demand_forecasts.append({
                "asset_id": asset_id,
                "asset_type": asset_type,
                "current_usage": daily_usage,
                "forecast_points": demand_fc.forecasts,
                "requires_expansion": demand_fc.requires_expansion,
                "expansion_timeline": demand_fc.expansion_timeline,
                "peak_year": demand_fc.peak_demand_year,
            })

        except Exception as e:
            logger.warning(f"Demand forecast failed for {asset_id}: {e}")

    # Identify bottlenecks
    bottlenecks = await asyncio.to_thread(
        identify_bottlenecks,
        assets,
        primary_region
    )

    bottleneck_list = [
        {
            "asset_id": b.asset_id,
            "asset_name": b.asset_name,
            "type": b.bottleneck_type,
            "severity": b.severity,
            "impact": b.impact_description,
            "priority": b.resolution_priority
        }
        for b in bottlenecks[:5]  # Top 5 bottlenecks
    ]

    # External factors summary
    external_factors = {
        "weather": {
            "region": primary_region,
            "risk_level": weather_risk.overall_risk,
            "flood_risk": weather_risk.flood_risk,
            "snowstorm_risk": weather_risk.snowstorm_risk,
            "heatwave_risk": weather_risk.heatwave_risk,
            "impact_factor": weather_factor
        },
        "demographics": {
            "region": primary_region,
            "population_density": demographics.population_density,
            "median_age": demographics.median_age,
            "demand_index": demographics.infrastructure_demand_index,
            "growth_drivers": demographics.growth_drivers[:2]  # Top 2 drivers
        }
    }

    # Build risk timeline years
    current_year = date.today().year
    risk_timeline["years"] = [
        {"year": current_year + i, "label": f"Year {i+1}"}
        for i in range(horizon_years + 1)
    ]

    trace.append(f"Forecasted {len(condition_forecasts)} condition, {len(demand_forecasts)} demand predictions")
    trace.append(f"Identified {len(bottleneck_list)} bottlenecks")

    return {
        "condition_forecasts": condition_forecasts,
        "demand_forecasts": demand_forecasts,
        "risk_timeline": risk_timeline,
        "external_factors": external_factors,
        "bottlenecks": bottleneck_list,
        "trace_log": trace,
        "loop_count": state["loop_count"] + 1,
    }


# --- Node 4: ANALYZE ---

async def analyze_node(state: ForesightState) -> Dict[str, Any]:
    """
    Run OR-Tools optimization on retrieved assets.
    """
    logger.debug("--- ANALYZE NODE ---")

    assets = state.get("retrieved_assets", [])
    budget = state["budget_total"]
    weights = state["weights"]
    enforce_equity = state.get("enforce_equity", False)

    if not assets:
        return {
            "error": "No assets available for analysis",
            "trace_log": ["Analysis failed: No assets retrieved"],
            "overall_confidence": 0.0,
        }

    # Run solver (async wrapped since it may take time)
    solver = CapitalPlanSolver(time_limit_ms=SOLVER_TIME_LIMIT_SLOW_MS)
    result: AllocationResult = await asyncio.to_thread(
        solver.solve,
        assets,
        budget,
        weights,
        enforce_equity
    )

    # Compute risk scores for state tracking
    risk_scores = [
        {
            "asset_id": a["asset_id"],
            "risk_score": a["risk_score"],
            "priority_score": a["priority_score"]
        }
        for a in result.allocations
    ]

    # Determine confidence based on solver status
    confidence = SOLVER_CONFIDENCE.get(result.solver_status, DEFAULT_CONFIDENCE)

    return {
        "recommendations": result.allocations,
        "risk_scores": risk_scores,
        "analysis_result": {
            "total_budget": budget,
            "total_allocated": result.total_allocated,
            "total_requested": result.total_requested,
            "assets_funded": result.assets_funded,
            "assets_deferred": result.assets_deferred,
            "risk_reduction_pct": result.risk_reduction_pct,
            "solver_status": result.solver_status,
            "optimality_gap": result.optimality_gap,
            "equity_satisfied": result.equity_satisfied,
        },
        "overall_confidence": confidence,
        "trace_log": result.trace,
        "loop_count": state["loop_count"] + 1,
    }


# --- Node 4: EVALUATE (Optional) ---

async def evaluate_node(state: ForesightState) -> Dict[str, Any]:
    """
    Run scenario comparison if include_scenarios is True.
    Compares base case with pessimistic and optimistic scenarios.
    """
    logger.debug("--- EVALUATE NODE ---")

    if not state.get("include_scenarios"):
        return {"trace_log": ["Scenario evaluation: Skipped (not enabled)"]}

    recommendations = state.get("recommendations", [])
    if not recommendations:
        return {"trace_log": ["Scenario evaluation: No recommendations to evaluate"]}

    assets = state.get("retrieved_assets", [])
    budget = state["budget_total"]
    weights = state["weights"]

    solver = CapitalPlanSolver(time_limit_ms=3000)
    scenarios = []

    # Base case already computed - store for comparison
    base_result = state.get("analysis_result", {})

    # Pessimistic: Higher risk weight, lower budget
    pessimistic_weights = {"risk": min(weights.get("risk", 0.6) * 1.3, 1.0), "coverage": weights.get("coverage", 0.4) * 0.7}
    pessimistic_budget = budget * 0.8

    try:
        pess_result = await asyncio.to_thread(
            solver.solve, assets, pessimistic_budget, pessimistic_weights, False
        )
        scenarios.append({
            "name": "Pessimistic",
            "description": "20% budget cut, higher risk focus",
            "assets_funded": pess_result.assets_funded,
            "total_allocated": pess_result.total_allocated,
            "risk_reduction_pct": pess_result.risk_reduction_pct,
        })
    except Exception as e:
        scenarios.append({"name": "Pessimistic", "error": str(e)})

    # Optimistic: More budget, balanced weights
    optimistic_budget = budget * 1.2

    try:
        opt_result = await asyncio.to_thread(
            solver.solve, assets, optimistic_budget, weights, False
        )
        scenarios.append({
            "name": "Optimistic",
            "description": "20% budget increase",
            "assets_funded": opt_result.assets_funded,
            "total_allocated": opt_result.total_allocated,
            "risk_reduction_pct": opt_result.risk_reduction_pct,
        })
    except Exception as e:
        scenarios.append({"name": "Optimistic", "error": str(e)})

    # Equity-enforced scenario
    if not state.get("enforce_equity"):
        try:
            equity_result = await asyncio.to_thread(
                solver.solve, assets, budget, weights, True  # enforce_equity=True
            )
            scenarios.append({
                "name": "Equity-Enforced",
                "description": "10% minimum per region",
                "assets_funded": equity_result.assets_funded,
                "total_allocated": equity_result.total_allocated,
                "risk_reduction_pct": equity_result.risk_reduction_pct,
                "equity_satisfied": equity_result.equity_satisfied,
            })
        except Exception as e:
            scenarios.append({"name": "Equity-Enforced", "error": str(e)})

    return {
        "scenario_evaluations": scenarios,
        "trace_log": [f"Evaluated {len(scenarios)} scenarios"],
        "loop_count": state["loop_count"] + 1,
    }


# --- Node 5: SYNTHESIZE ---

async def synthesize_node(state: ForesightState) -> Dict[str, Any]:
    """
    Format final output for frontend consumption.
    Generates summary text and ensures schema compliance.
    """
    logger.debug("--- SYNTHESIZE NODE ---")

    language = state.get("language", "en")
    recommendations = state.get("recommendations", [])
    analysis = state.get("analysis_result", {})
    scenarios = state.get("scenario_evaluations", [])
    confidence = state.get("overall_confidence", 0.5)

    # Generate summary text
    funded = analysis.get("assets_funded", 0)
    deferred = analysis.get("assets_deferred", 0)
    allocated = analysis.get("total_allocated", 0)
    risk_reduction = analysis.get("risk_reduction_pct", 0)

    if language == "fr":
        summary = (
            f"Analyse terminee. {funded} actifs finances pour un total de "
            f"${allocated:,.0f}. Reduction du risque: {risk_reduction:.1f}%. "
            f"{deferred} actifs reportes par contraintes budgetaires."
        )
    else:
        summary = (
            f"Analysis complete. {funded} assets funded for a total of "
            f"${allocated:,.0f}. Risk reduction: {risk_reduction:.1f}%. "
            f"{deferred} assets deferred due to budget constraints."
        )

    # Add scenario insights if available
    if scenarios:
        if language == "fr":
            summary += f" {len(scenarios)} scenarios evalues pour comparaison."
        else:
            summary += f" {len(scenarios)} scenarios evaluated for comparison."

    # Update analysis result with summary
    updated_analysis = dict(analysis) if analysis else {}
    updated_analysis["summary"] = summary
    updated_analysis["status"] = "complete"

    # Confidence assessment
    if confidence >= CONFIDENCE_HIGH_THRESHOLD:
        confidence_label = "High" if language == "en" else "Eleve"
    elif confidence >= CONFIDENCE_MEDIUM_THRESHOLD:
        confidence_label = "Medium" if language == "en" else "Moyen"
    else:
        confidence_label = "Low" if language == "en" else "Faible"

    updated_analysis["confidence_label"] = confidence_label

    return {
        "analysis_result": updated_analysis,
        "trace_log": [f"Synthesis complete. Confidence: {confidence_label} ({confidence:.0%})"],
    }
