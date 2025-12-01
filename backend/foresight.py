import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, date
from typing import List, Dict, Any

from sql_db import get_session_factory

logger = logging.getLogger(__name__)
from foresight_models import Asset, Capacity, ConditionScore, SupplyNode, SupplyRoute
from optimization_solver import (
    CapitalPlanSolver,
    NetworkFlowSolver,
    solve_capital_plan,
    solve_emergency_flow,
)

# --- Mock Data Generators (fallbacks) ---


def generate_infrastructure_data(count: int = 10) -> List[Dict[str, Any]]:
    """Generates mock infrastructure assets with condition and usage data."""
    types = ["Bridge", "Highway Segment", "Water Main", "Public Building"]
    regions = ["North", "East", "West", "Central"]

    assets = []
    for i in range(count):
        asset_type = np.random.choice(types)
        region = np.random.choice(regions)
        # Condition: 0 (Failed) to 100 (New)
        condition = int(np.random.normal(60, 20))
        condition = max(0, min(100, condition))

        assets.append(
            {
                "id": f"AST-{1000+i}",
                "name": f"{region} {asset_type} {i+1}",
                "type": asset_type,
                "region": region,
                "age_years": np.random.randint(5, 60),
                "condition_score": condition,
                "daily_usage": np.random.randint(1000, 50000),
                "replacement_cost": np.random.randint(500000, 50000000),
                "population_growth_rate": round(np.random.uniform(0.5, 4.0), 2),  # %
            }
        )
    return assets


def generate_supply_chain_data() -> Dict[str, Any]:
    """Generates a mock supply chain graph and current status."""
    nodes = [
        {
            "id": "WH-Main",
            "type": "Warehouse",
            "lat": 45.42,
            "lng": -75.69,
            "status": "Operational",
        },
        {
            "id": "Hosp-North",
            "type": "Hospital",
            "lat": 45.50,
            "lng": -75.70,
            "status": "Critical Low",
        },
        {
            "id": "Dist-East",
            "type": "Distribution",
            "lat": 45.40,
            "lng": -75.60,
            "status": "Operational",
        },
    ]

    routes = [
        {
            "source": "WH-Main",
            "target": "Hosp-North",
            "distance_km": 12,
            "base_time_min": 25,
        },
        {
            "source": "WH-Main",
            "target": "Dist-East",
            "distance_km": 8,
            "base_time_min": 15,
        },
        {
            "source": "Dist-East",
            "target": "Hosp-North",
            "distance_km": 15,
            "base_time_min": 30,
        },
    ]

    return {"nodes": nodes, "routes": routes}


# --- Core Logic ---


def _fetch_assets_from_db() -> List[Dict[str, Any]]:
    """Fetch assets and latest capacity/condition from the DB; return [] if none."""
    session_factory = get_session_factory()
    session = session_factory()
    try:
        assets: List[Asset] = session.query(Asset).all()
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
                    (Capacity.effective_end.is_(None))
                    | (Capacity.effective_end >= today),
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
            condition_score = cond.condition_score if cond else None

            results.append(
                {
                    "id": a.asset_id,
                    "name": a.name,
                    "type": a.type,
                    "region": a.region,
                    "age_years": a.design_life or 0,
                    "condition_score": (
                        condition_score if condition_score is not None else 60
                    ),
                    "daily_usage": a.daily_usage or (cap_value or 0),
                    "replacement_cost": a.replacement_cost or 0,
                    "population_growth_rate": a.population_growth_rate or 0.0,
                }
            )
        return results
    except Exception as e:
        logger.warning(f"Error fetching infrastructure data from DB: {e}")
        return []
    finally:
        session.close()


def run_capital_planning(
    budget: float, prioritization_weights: Dict[str, float]
) -> Dict[str, Any]:
    """
    Prioritizes infrastructure projects using OR-Tools MILP optimization.
    Pulls from DB if populated; falls back to synthetic data otherwise.

    Uses the CapitalPlanSolver for optimal allocation under budget constraints.
    """
    assets = _fetch_assets_from_db()
    if not assets:
        assets = generate_infrastructure_data(20)

    # Map legacy weight keys to solver format
    weights = {
        "risk": prioritization_weights.get("risk", 0.5),
        "coverage": prioritization_weights.get("impact", 0.5),
    }

    # Run OR-Tools optimization
    result = solve_capital_plan(
        assets=assets,
        budget=budget,
        weights=weights,
        enforce_equity=False  # Legacy endpoint doesn't use equity
    )

    # Convert solver result to legacy format for backwards compatibility
    projects = []
    for alloc in result.allocations:
        # Find original asset to get all fields
        original = next((a for a in assets if a["id"] == alloc["asset_id"]), {})

        projects.append({
            "id": alloc["asset_id"],
            "name": alloc["asset_name"],
            "type": alloc.get("asset_type", original.get("type", "Unknown")),
            "region": alloc["region"],
            "age_years": original.get("age_years", 0),
            "condition_score": alloc["current_condition"],
            "daily_usage": original.get("daily_usage", 0),
            "replacement_cost": alloc["replacement_cost"],
            "population_growth_rate": original.get("population_growth_rate", 0),
            "predicted_failure_prob": alloc["risk_score"],
            "failure_impact": 0,  # Not tracked in new solver
            "priority_score": alloc["priority_score"],
            "status": alloc["status"],
        })

    return {
        "total_requested": result.total_requested,
        "total_funded": result.total_allocated,
        "projects": projects[:15],  # Return top 15 for UI
        # New fields from solver
        "solver_status": result.solver_status,
        "risk_reduction_pct": result.risk_reduction_pct,
        "assets_funded": result.assets_funded,
        "assets_deferred": result.assets_deferred,
    }


def _fetch_supply_chain_from_db() -> Dict[str, Any]:
    session_factory = get_session_factory()
    session = session_factory()
    try:
        nodes = session.query(SupplyNode).all()
        routes = session.query(SupplyRoute).all()
        if not nodes or not routes:
            return {}
        nodes_out = [
            {
                "id": n.node_id,
                "type": n.type,
                "lat": n.lat,
                "lng": n.lon,
                "status": n.status,
            }
            for n in nodes
        ]
        routes_out = [
            {
                "source": r.source_id,
                "target": r.target_id,
                "distance_km": r.distance_km,
                "base_time_min": r.base_time_min,
            }
            for r in routes
        ]
        return {"nodes": nodes_out, "routes": routes_out}
    except Exception as e:
        logger.warning(f"Error fetching supply chain data from DB: {e}")
        return {}
    finally:
        session.close()


def simulate_emergency_response(event_type: str) -> Dict[str, Any]:
    """
    Simulates supply chain adaptations using OR-Tools min-cost max-flow.
    Uses NetworkFlowSolver to optimize routing under disruption scenarios.

    Preference: DB topology; fallback to mock.
    """
    network = _fetch_supply_chain_from_db()
    if not network:
        network = generate_supply_chain_data()

    # Run network flow optimization
    result = solve_emergency_flow(
        nodes=network["nodes"],
        routes=network["routes"],
        event_type=event_type
    )

    # Convert solver result to legacy format
    affected_routes = []
    for route in result.routes:
        # Map status from solver to expected format
        status = route.get("status", "On Time")
        if status == "Active":
            est_time = route.get("estimated_time")
            orig_time = route.get("original_time", 0)
            if est_time and orig_time and est_time > orig_time * 1.2:
                status = "Delayed"
            else:
                status = "On Time"

        affected_routes.append({
            "source": route["source"],
            "target": route["target"],
            "original_time": route["original_time"],
            "estimated_time": route.get("estimated_time") or route["original_time"],
            "status": status,
            "traffic_index": route.get("traffic_index", 0),
        })

    return {
        "event": event_type,
        "network_status": result.network_status,
        "routes": affected_routes,
        "alerts": result.alerts,
        # New fields from solver
        "solver_status": result.solver_status,
        "blocked_edges": len(result.blocked_edges),
        "rerouted_paths": len(result.rerouted_paths),
    }
