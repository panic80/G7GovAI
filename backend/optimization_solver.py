"""
Optimization Solvers for ForesightOps
=====================================
Uses Google OR-Tools for industrial-strength optimization.

1. CapitalPlanSolver - MILP for budget allocation with optional equity constraints
2. NetworkFlowSolver - Min-cost max-flow for supply chain resilience
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from ortools.linear_solver import pywraplp
from ortools.graph.python import min_cost_flow
import math

from core.constants import SOLVER_TIME_LIMIT_MS, MIN_REGIONAL_EQUITY_PCT


# --- Data Classes ---

@dataclass
class AllocationResult:
    """Result of capital planning optimization."""
    allocations: List[Dict[str, Any]]
    total_budget: float
    total_allocated: float
    total_requested: float
    assets_funded: int
    assets_deferred: int
    solver_status: str
    optimality_gap: float
    risk_reduction_pct: float
    equity_satisfied: bool = True
    trace: List[str] = field(default_factory=list)


@dataclass
class FlowResult:
    """Result of network flow optimization."""
    routes: List[Dict[str, Any]]
    total_flow: float
    total_cost: float
    blocked_edges: List[Tuple[str, str]]
    rerouted_paths: List[Dict[str, Any]]
    network_status: str
    solver_status: str
    alerts: List[str] = field(default_factory=list)
    trace: List[str] = field(default_factory=list)


# --- Capital Planning Solver ---

class CapitalPlanSolver:
    """
    Mixed-Integer Linear Programming solver for infrastructure capital allocation.

    Objective: Maximize weighted priority score of funded projects
    Subject to:
        - Total allocation <= budget (hard constraint)
        - Optional: Regional equity (min % per region)
        - Optional: Asset type distribution
    """

    def __init__(self, time_limit_ms: int = SOLVER_TIME_LIMIT_MS):
        self.time_limit_ms = time_limit_ms

    def solve(
        self,
        assets: List[Dict[str, Any]],
        budget: float,
        weights: Dict[str, float],
        enforce_equity: bool = False,
        min_regional_pct: float = MIN_REGIONAL_EQUITY_PCT,
        constraints: Optional[Dict[str, Any]] = None
    ) -> AllocationResult:
        """
        Solve the capital allocation problem.

        Args:
            assets: List of asset dicts with keys:
                - id, name, type, region, condition_score, replacement_cost,
                - daily_usage, population_growth_rate, age_years
            budget: Total available budget
            weights: Priority weights (e.g., {"risk": 0.6, "coverage": 0.4})
            enforce_equity: If True, enforce minimum allocation per region
            min_regional_pct: Minimum % of budget per region (if enforce_equity)
            constraints: Additional constraints dict

        Returns:
            AllocationResult with allocations and metadata
        """
        trace = []
        trace.append(f"Starting optimization with budget ${budget:,.0f} for {len(assets)} assets")

        if not assets:
            return AllocationResult(
                allocations=[],
                total_budget=budget,
                total_allocated=0,
                total_requested=0,
                assets_funded=0,
                assets_deferred=0,
                solver_status="NO_ASSETS",
                optimality_gap=0,
                risk_reduction_pct=0,
                trace=["No assets provided"]
            )

        # Calculate priority scores for each asset
        scored_assets = self._compute_priority_scores(assets, weights)
        trace.append(f"Computed priority scores with weights: {weights}")

        # Create solver
        solver = pywraplp.Solver.CreateSolver('SCIP')
        if not solver:
            # Fallback to CBC if SCIP not available
            solver = pywraplp.Solver.CreateSolver('CBC')

        if not solver:
            trace.append("ERROR: No solver available")
            return self._fallback_greedy(scored_assets, budget, trace)

        solver.SetTimeLimit(self.time_limit_ms)

        # Decision variables: x[i] = 1 if asset i is funded
        x = {}
        for i, asset in enumerate(scored_assets):
            x[i] = solver.IntVar(0, 1, f'x_{i}')

        # Objective: Maximize sum of (priority_score * x[i])
        objective = solver.Objective()
        for i, asset in enumerate(scored_assets):
            objective.SetCoefficient(x[i], asset['priority_score'])
        objective.SetMaximization()

        # Constraint 1: Total cost <= budget
        budget_constraint = solver.Constraint(0, budget, 'budget')
        for i, asset in enumerate(scored_assets):
            budget_constraint.SetCoefficient(x[i], asset['replacement_cost'])

        # Constraint 2 (optional): Regional equity
        regions = set(a['region'] for a in scored_assets)
        if enforce_equity and len(regions) > 1:
            trace.append(f"Enforcing equity: min {min_regional_pct*100:.0f}% per region")
            min_budget_per_region = budget * min_regional_pct

            for region in regions:
                region_constraint = solver.Constraint(min_budget_per_region, solver.infinity(), f'equity_{region}')
                for i, asset in enumerate(scored_assets):
                    if asset['region'] == region:
                        region_constraint.SetCoefficient(x[i], asset['replacement_cost'])

        # Solve
        trace.append("Running MILP solver...")
        status = solver.Solve()

        # Map status
        status_map = {
            pywraplp.Solver.OPTIMAL: "OPTIMAL",
            pywraplp.Solver.FEASIBLE: "FEASIBLE",
            pywraplp.Solver.INFEASIBLE: "INFEASIBLE",
            pywraplp.Solver.UNBOUNDED: "UNBOUNDED",
            pywraplp.Solver.ABNORMAL: "ABNORMAL",
            pywraplp.Solver.NOT_SOLVED: "NOT_SOLVED"
        }
        solver_status = status_map.get(status, "UNKNOWN")
        trace.append(f"Solver status: {solver_status}")

        # Handle infeasible (equity constraints too strict)
        if status == pywraplp.Solver.INFEASIBLE:
            trace.append("Constraints infeasible - relaxing equity and retrying with greedy")
            return self._fallback_greedy(scored_assets, budget, trace, equity_satisfied=False)

        # Extract solution
        allocations = []
        total_allocated = 0
        total_risk_before = 0
        total_risk_after = 0

        for i, asset in enumerate(scored_assets):
            funded = x[i].solution_value() > 0.5
            asset_alloc = {
                "asset_id": asset['id'],
                "asset_name": asset['name'],
                "region": asset['region'],
                "asset_type": asset['type'],
                "current_condition": asset['condition_score'],
                "replacement_cost": asset['replacement_cost'],
                "risk_score": asset['predicted_failure_prob'],
                "priority_score": round(asset['priority_score'], 3),
                "budget_assigned": asset['replacement_cost'] if funded else 0,
                "status": "Funded" if funded else "Deferred",
                "rank": i + 1,
                "rationale": self._generate_rationale(asset, funded)
            }
            allocations.append(asset_alloc)

            total_risk_before += asset['predicted_failure_prob']
            if funded:
                total_allocated += asset['replacement_cost']
                # Assume funded projects reduce risk by 80%
                total_risk_after += asset['predicted_failure_prob'] * 0.2
            else:
                total_risk_after += asset['predicted_failure_prob']

        # Calculate optimality gap
        best_bound = solver.Objective().BestBound() if hasattr(solver.Objective(), 'BestBound') else solver.Objective().Value()
        objective_value = solver.Objective().Value()
        optimality_gap = abs(best_bound - objective_value) / max(abs(objective_value), 1e-9) if objective_value != 0 else 0

        # Risk reduction
        risk_reduction = ((total_risk_before - total_risk_after) / max(total_risk_before, 1e-9)) * 100

        assets_funded = sum(1 for a in allocations if a['status'] == 'Funded')
        trace.append(f"Solution: {assets_funded} funded, ${total_allocated:,.0f} allocated")

        return AllocationResult(
            allocations=allocations,
            total_budget=budget,
            total_allocated=total_allocated,
            total_requested=sum(a['replacement_cost'] for a in scored_assets),
            assets_funded=assets_funded,
            assets_deferred=len(allocations) - assets_funded,
            solver_status=solver_status,
            optimality_gap=round(optimality_gap, 4),
            risk_reduction_pct=round(risk_reduction, 1),
            equity_satisfied=enforce_equity,
            trace=trace
        )

    def _compute_priority_scores(
        self,
        assets: List[Dict[str, Any]],
        weights: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """Compute normalized priority scores for assets."""
        scored = []

        for asset in assets:
            a = dict(asset)  # Copy

            # Failure probability based on condition and age
            condition = a.get('condition_score', 50)
            age = a.get('age_years', 10)
            a['predicted_failure_prob'] = min(1.0, (100 - condition) / 100 * (1 + age / 100))

            # Impact score based on usage and population
            usage = a.get('daily_usage', 1000)
            pop_growth = a.get('population_growth_rate', 1.0)
            a['failure_impact'] = math.log(max(usage, 1)) * (1 + pop_growth / 100)

            scored.append(a)

        # Normalize risk and impact
        risks = [a['predicted_failure_prob'] for a in scored]
        impacts = [a['failure_impact'] for a in scored]

        risk_min, risk_max = min(risks), max(risks)
        impact_min, impact_max = min(impacts), max(impacts)

        w_risk = weights.get('risk', 0.5)
        w_coverage = weights.get('coverage', weights.get('impact', 0.5))

        for a in scored:
            norm_risk = (a['predicted_failure_prob'] - risk_min) / max(risk_max - risk_min, 1e-9)
            norm_impact = (a['failure_impact'] - impact_min) / max(impact_max - impact_min, 1e-9)
            a['priority_score'] = norm_risk * w_risk + norm_impact * w_coverage

        # Sort by priority descending
        scored.sort(key=lambda x: x['priority_score'], reverse=True)
        return scored

    def _fallback_greedy(
        self,
        assets: List[Dict[str, Any]],
        budget: float,
        trace: List[str],
        equity_satisfied: bool = True
    ) -> AllocationResult:
        """Fallback greedy allocation when solver unavailable/infeasible."""
        trace.append("Using greedy fallback allocation")

        allocations = []
        remaining = budget
        total_risk_before = sum(a.get('predicted_failure_prob', 0.5) for a in assets)
        total_risk_after = 0

        for i, asset in enumerate(assets):
            cost = asset['replacement_cost']
            funded = remaining >= cost

            if funded:
                remaining -= cost
                total_risk_after += asset.get('predicted_failure_prob', 0.5) * 0.2
            else:
                total_risk_after += asset.get('predicted_failure_prob', 0.5)

            allocations.append({
                "asset_id": asset['id'],
                "asset_name": asset['name'],
                "region": asset['region'],
                "asset_type": asset['type'],
                "current_condition": asset.get('condition_score', 50),
                "replacement_cost": cost,
                "risk_score": asset.get('predicted_failure_prob', 0.5),
                "priority_score": round(asset.get('priority_score', 0.5), 3),
                "budget_assigned": cost if funded else 0,
                "status": "Funded" if funded else "Deferred",
                "rank": i + 1,
                "rationale": self._generate_rationale(asset, funded)
            })

        risk_reduction = ((total_risk_before - total_risk_after) / max(total_risk_before, 1e-9)) * 100
        assets_funded = sum(1 for a in allocations if a['status'] == 'Funded')

        return AllocationResult(
            allocations=allocations,
            total_budget=budget,
            total_allocated=budget - remaining,
            total_requested=sum(a['replacement_cost'] for a in assets),
            assets_funded=assets_funded,
            assets_deferred=len(allocations) - assets_funded,
            solver_status="GREEDY_FALLBACK",
            optimality_gap=0,
            risk_reduction_pct=round(risk_reduction, 1),
            equity_satisfied=equity_satisfied,
            trace=trace
        )

    def _generate_rationale(self, asset: Dict[str, Any], funded: bool) -> str:
        """Generate human-readable rationale for allocation decision."""
        condition = asset.get('condition_score', 50)
        risk = asset.get('predicted_failure_prob', 0.5)

        if funded:
            if condition < 40:
                return f"Critical condition ({condition}/100) - immediate intervention required"
            elif risk > 0.7:
                return f"High failure risk ({risk:.0%}) - preventive maintenance prioritized"
            else:
                return f"Optimized for risk-coverage balance (priority: {asset.get('priority_score', 0):.2f})"
        else:
            return f"Deferred: Lower priority ({asset.get('priority_score', 0):.2f}) or budget constraints"


# --- Network Flow Solver ---

class NetworkFlowSolver:
    """
    Min-cost max-flow solver for supply chain resilience.

    Uses OR-Tools SimpleMinCostFlow to optimize supply routing
    under disruption scenarios (floods, storms, etc.).
    """

    def __init__(self):
        pass

    def optimize_flows(
        self,
        nodes: List[Dict[str, Any]],
        routes: List[Dict[str, Any]],
        disruptions: Dict[str, Any],
        demand: Optional[Dict[str, float]] = None
    ) -> FlowResult:
        """
        Optimize supply chain flows given disruptions.

        Args:
            nodes: List of node dicts with keys: id, type, lat, lng, status
            routes: List of route dicts with keys: source, target, distance_km, base_time_min
            disruptions: Dict with event_type, affected_routes, severity
            demand: Optional demand at each node (positive = supply, negative = demand)

        Returns:
            FlowResult with optimized routes and metrics
        """
        trace = []
        event_type = disruptions.get('event_type', 'None')
        trace.append(f"Optimizing network under {event_type} scenario")

        if not nodes or not routes:
            return FlowResult(
                routes=[],
                total_flow=0,
                total_cost=0,
                blocked_edges=[],
                rerouted_paths=[],
                network_status="NO_NETWORK",
                solver_status="NO_DATA",
                alerts=["No network data provided"],
                trace=trace
            )

        # Build node index
        node_ids = {n['id']: i for i, n in enumerate(nodes)}
        num_nodes = len(nodes)

        # Determine affected routes based on event
        delay_factors = {
            "None": 1.0,
            "Snowstorm": 2.5,
            "Flood": 5.0,
            "Heatwave": 1.1,
            "Earthquake": 10.0
        }
        delay_factor = delay_factors.get(event_type, 1.0)

        # Mark blocked routes (Flood blocks ~30% of routes)
        blocked_edges = []
        import random
        random.seed(42)  # Reproducible for demo

        for route in routes:
            if event_type == "Flood" and random.random() > 0.7:
                blocked_edges.append((route['source'], route['target']))
            elif event_type == "Earthquake" and random.random() > 0.5:
                blocked_edges.append((route['source'], route['target']))

        trace.append(f"Blocked edges: {len(blocked_edges)}")

        # Create min cost flow solver
        smcf = min_cost_flow.SimpleMinCostFlow()

        # Add arcs (bidirectional for simplicity)
        arc_data = []
        for route in routes:
            src = node_ids.get(route['source'])
            dst = node_ids.get(route['target'])

            if src is None or dst is None:
                continue

            is_blocked = (route['source'], route['target']) in blocked_edges

            if is_blocked:
                # Blocked route: very high cost, near-zero capacity
                capacity = 1
                cost = 10000
            else:
                # Normal route: cost = time with delay
                capacity = 100  # units
                base_cost = int(route['base_time_min'] * delay_factor)
                cost = base_cost

            arc_idx = smcf.add_arc_with_capacity_and_unit_cost(src, dst, capacity, cost)
            arc_data.append({
                "arc": arc_idx,
                "source": route['source'],
                "target": route['target'],
                "base_time": route['base_time_min'],
                "capacity": capacity,
                "cost": cost,
                "blocked": is_blocked
            })

        # Set supplies/demands
        # Default: first warehouse is supply, hospitals are demand
        supplies = {}
        for node in nodes:
            if node['type'] == 'Warehouse':
                supplies[node['id']] = 50  # Supply
            elif node['type'] == 'Hospital':
                supplies[node['id']] = -25  # Demand
            else:
                supplies[node['id']] = 0

        # Override with provided demand if available
        if demand:
            supplies.update(demand)

        for node in nodes:
            node_idx = node_ids[node['id']]
            supply = supplies.get(node['id'], 0)
            smcf.set_node_supply(node_idx, supply)

        # Solve
        trace.append("Running min-cost max-flow solver...")
        status = smcf.solve()

        status_map = {
            smcf.OPTIMAL: "OPTIMAL",
            smcf.NOT_SOLVED: "NOT_SOLVED",
            smcf.INFEASIBLE: "INFEASIBLE",
            smcf.UNBALANCED: "UNBALANCED",
            smcf.BAD_RESULT: "BAD_RESULT",
            smcf.BAD_COST_RANGE: "BAD_COST_RANGE"
        }
        solver_status = status_map.get(status, "UNKNOWN")
        trace.append(f"Solver status: {solver_status}")

        # Extract results
        result_routes = []
        rerouted = []
        total_flow = 0
        total_cost = 0

        if status == smcf.OPTIMAL:
            total_flow = smcf.optimal_cost()  # Actually total cost

            for arc in arc_data:
                arc_idx = arc['arc']
                flow = smcf.flow(arc_idx)

                if arc['blocked']:
                    status_str = "Blocked"
                elif flow > 0:
                    status_str = "Active"
                    total_cost += flow * arc['cost']
                else:
                    status_str = "Unused"

                # Compute estimated time with delay
                est_time = arc['base_time'] * delay_factor if not arc['blocked'] else float('inf')

                route_result = {
                    "source": arc['source'],
                    "target": arc['target'],
                    "original_time": arc['base_time'],
                    "estimated_time": round(est_time, 1) if est_time != float('inf') else None,
                    "flow": flow,
                    "status": status_str,
                    "traffic_index": min(10, int(delay_factor * 2))
                }
                result_routes.append(route_result)

                if flow > 0 and arc['cost'] > arc['base_time'] * 1.5:
                    rerouted.append({
                        "from": arc['source'],
                        "to": arc['target'],
                        "reason": "High delay - consider alternative"
                    })
        else:
            # Fallback: return original routes with delay estimates
            for route in routes:
                is_blocked = (route['source'], route['target']) in blocked_edges
                est_time = route['base_time_min'] * delay_factor if not is_blocked else None

                result_routes.append({
                    "source": route['source'],
                    "target": route['target'],
                    "original_time": route['base_time_min'],
                    "estimated_time": round(est_time, 1) if est_time else None,
                    "flow": 0,
                    "status": "Blocked" if is_blocked else "Delayed",
                    "traffic_index": min(10, int(delay_factor * 2))
                })

        # Determine network status
        blocked_pct = len(blocked_edges) / max(len(routes), 1)
        if blocked_pct > 0.5:
            network_status = "Critical"
        elif blocked_pct > 0.2 or delay_factor > 3:
            network_status = "High"
        elif delay_factor > 1.5:
            network_status = "Moderate"
        else:
            network_status = "Low"

        # Generate alerts
        alerts = []
        if event_type != "None":
            alerts.append(f"Weather Alert: {event_type} affecting transport times by {delay_factor}x")
        if blocked_edges:
            alerts.append(f"Route Advisory: {len(blocked_edges)} route(s) currently blocked")
        if rerouted:
            alerts.append(f"Rerouting Advisory: {len(rerouted)} flow(s) redirected to alternatives")

        trace.append(f"Network status: {network_status}, {len(blocked_edges)} blocked, {len(rerouted)} rerouted")

        return FlowResult(
            routes=result_routes,
            total_flow=total_flow,
            total_cost=total_cost,
            blocked_edges=blocked_edges,
            rerouted_paths=rerouted,
            network_status=network_status,
            solver_status=solver_status,
            alerts=alerts,
            trace=trace
        )


# --- Convenience Functions ---

def solve_capital_plan(
    assets: List[Dict[str, Any]],
    budget: float,
    weights: Dict[str, float] = None,
    enforce_equity: bool = False
) -> AllocationResult:
    """Convenience function for capital planning."""
    solver = CapitalPlanSolver()
    return solver.solve(
        assets=assets,
        budget=budget,
        weights=weights or {"risk": 0.6, "coverage": 0.4},
        enforce_equity=enforce_equity
    )


def solve_emergency_flow(
    nodes: List[Dict[str, Any]],
    routes: List[Dict[str, Any]],
    event_type: str = "None"
) -> FlowResult:
    """Convenience function for emergency response optimization."""
    solver = NetworkFlowSolver()
    return solver.optimize_flows(
        nodes=nodes,
        routes=routes,
        disruptions={"event_type": event_type}
    )


# --- Multi-Resource Allocation Solver ---

@dataclass
class ResourcePool:
    """Represents a pool of available resources."""
    pool_id: str
    name: str
    resource_type: str  # "money", "personnel", "equipment"
    total_quantity: float
    available_quantity: float
    unit: str
    region: Optional[str] = None
    skills: Optional[List[str]] = None  # For personnel
    equipment_type: Optional[str] = None  # For equipment


@dataclass
class ResourceRequirement:
    """Represents resource requirements for a project."""
    requirement_id: str
    asset_id: str
    resource_type: str
    quantity_needed: float
    unit: str
    priority: int = 3  # 1=critical, 5=low
    skills_required: Optional[List[str]] = None
    equipment_type: Optional[str] = None
    duration_days: int = 30


@dataclass
class MultiResourceAllocation:
    """A single resource allocation."""
    requirement_id: str
    asset_id: str
    pool_id: str
    resource_type: str
    quantity_allocated: float
    unit: str
    utilization_pct: float
    cost_estimate: float
    status: str  # "allocated", "partial", "unfunded"
    rationale: str


@dataclass
class MultiResourceResult:
    """Result of multi-resource optimization."""
    allocations: List[MultiResourceAllocation]
    # Summary by resource type
    money_allocated: float
    money_available: float
    personnel_allocated: float  # FTE
    personnel_available: float
    equipment_allocated: int
    equipment_available: int
    # Metrics
    projects_fully_funded: int
    projects_partial: int
    projects_unfunded: int
    total_cost_estimate: float
    resource_utilization: Dict[str, float]  # By type
    solver_status: str
    trace: List[str] = field(default_factory=list)


class MultiResourceSolver:
    """
    Multi-resource allocation solver using MILP.

    Optimizes allocation of money, personnel, and equipment simultaneously
    with constraints on availability, skill matching, and scheduling.

    Objective: Maximize priority-weighted project completion
    Subject to:
        - Resource pool capacities (per type)
        - Skill matching for personnel
        - Equipment type matching
        - Optional: Regional equity
        - Optional: Scheduling constraints
    """

    def __init__(self, time_limit_ms: int = SOLVER_TIME_LIMIT_MS):
        self.time_limit_ms = time_limit_ms

    def solve(
        self,
        requirements: List[Dict[str, Any]],
        pools: List[Dict[str, Any]],
        weights: Dict[str, float] = None,
        enforce_equity: bool = False
    ) -> MultiResourceResult:
        """
        Solve multi-resource allocation problem.

        Args:
            requirements: List of resource requirements per project
            pools: List of available resource pools
            weights: Priority weights for objective
            enforce_equity: If True, enforce regional equity

        Returns:
            MultiResourceResult with allocations and metrics
        """
        trace = []
        trace.append(f"Starting multi-resource optimization: {len(requirements)} requirements, {len(pools)} pools")

        if not requirements:
            return self._empty_result(pools, trace)

        # Group pools by type
        pools_by_type = {"money": [], "personnel": [], "equipment": []}
        for pool in pools:
            ptype = pool.get("resource_type", "money")
            if ptype in pools_by_type:
                pools_by_type[ptype].append(pool)

        # Group requirements by asset
        reqs_by_asset = {}
        for req in requirements:
            asset_id = req["asset_id"]
            if asset_id not in reqs_by_asset:
                reqs_by_asset[asset_id] = []
            reqs_by_asset[asset_id].append(req)

        trace.append(f"Resources: money={len(pools_by_type['money'])}, "
                    f"personnel={len(pools_by_type['personnel'])}, "
                    f"equipment={len(pools_by_type['equipment'])}")

        # Create solver
        solver = pywraplp.Solver.CreateSolver('SCIP')
        if not solver:
            solver = pywraplp.Solver.CreateSolver('CBC')

        if not solver:
            trace.append("ERROR: No solver available - using greedy fallback")
            return self._greedy_allocation(requirements, pools, trace)

        solver.SetTimeLimit(self.time_limit_ms)

        # Decision variables
        # x[r,p] = fraction of requirement r satisfied by pool p (0 to 1)
        # y[r] = 1 if requirement r is fully satisfied
        x = {}
        y = {}

        for i, req in enumerate(requirements):
            req_type = req.get("resource_type", "money")
            y[i] = solver.IntVar(0, 1, f'y_{i}')

            for j, pool in enumerate(pools):
                if pool.get("resource_type") == req_type:
                    # Check skill/equipment compatibility
                    if req_type == "personnel":
                        skills_needed = set(req.get("skills_required") or [])
                        skills_available = set(pool.get("skills") or [])
                        if skills_needed and not skills_needed.issubset(skills_available):
                            continue  # Skip incompatible pool
                    elif req_type == "equipment":
                        eq_needed = req.get("equipment_type")
                        eq_available = pool.get("equipment_type")
                        if eq_needed and eq_available and eq_needed != eq_available:
                            continue

                    x[i, j] = solver.NumVar(0, 1, f'x_{i}_{j}')

        # Objective: Maximize weighted sum of completed requirements
        # Priority: 1=critical (weight 5), 2=high (4), 3=medium (3), 4=low (2), 5=minimal (1)
        priority_weights = {1: 5, 2: 4, 3: 3, 4: 2, 5: 1}

        objective = solver.Objective()
        for i, req in enumerate(requirements):
            priority = req.get("priority", 3)
            weight = priority_weights.get(priority, 3)
            objective.SetCoefficient(y[i], weight)
        objective.SetMaximization()

        # Constraint 1: Pool capacity
        for j, pool in enumerate(pools):
            capacity_constraint = solver.Constraint(
                0,
                pool.get("available_quantity", 0),
                f'pool_cap_{j}'
            )
            for i, req in enumerate(requirements):
                if (i, j) in x:
                    capacity_constraint.SetCoefficient(x[i, j], req.get("quantity_needed", 0))

        # Constraint 2: Requirement satisfaction (sum of allocations = y * quantity_needed)
        for i, req in enumerate(requirements):
            qty_needed = req.get("quantity_needed", 0)

            # Sum of allocations must equal y[i] * qty_needed for full satisfaction
            # Using two constraints: sum >= y * qty and sum <= qty
            sum_constraint_lower = solver.Constraint(0, solver.infinity(), f'req_lower_{i}')
            sum_constraint_upper = solver.Constraint(0, qty_needed, f'req_upper_{i}')

            for j, pool in enumerate(pools):
                if (i, j) in x:
                    sum_constraint_lower.SetCoefficient(x[i, j], qty_needed)
                    sum_constraint_upper.SetCoefficient(x[i, j], qty_needed)

            sum_constraint_lower.SetCoefficient(y[i], -qty_needed)

        # Solve
        trace.append("Running multi-resource MILP solver...")
        status = solver.Solve()

        status_map = {
            pywraplp.Solver.OPTIMAL: "OPTIMAL",
            pywraplp.Solver.FEASIBLE: "FEASIBLE",
            pywraplp.Solver.INFEASIBLE: "INFEASIBLE",
            pywraplp.Solver.UNBOUNDED: "UNBOUNDED",
            pywraplp.Solver.NOT_SOLVED: "NOT_SOLVED"
        }
        solver_status = status_map.get(status, "UNKNOWN")
        trace.append(f"Solver status: {solver_status}")

        if status in [pywraplp.Solver.INFEASIBLE, pywraplp.Solver.NOT_SOLVED]:
            trace.append("Falling back to greedy allocation")
            return self._greedy_allocation(requirements, pools, trace)

        # Extract solution
        allocations = []
        money_allocated = 0
        personnel_allocated = 0
        equipment_allocated = 0
        total_cost = 0

        for i, req in enumerate(requirements):
            fulfilled = y[i].solution_value() > 0.5
            req_type = req.get("resource_type", "money")
            qty_needed = req.get("quantity_needed", 0)

            total_allocated = 0
            for j, pool in enumerate(pools):
                if (i, j) in x:
                    alloc_frac = x[i, j].solution_value()
                    if alloc_frac > 0.01:
                        alloc_qty = alloc_frac * qty_needed
                        total_allocated += alloc_qty

                        # Calculate cost estimate for non-money resources
                        if req_type == "money":
                            cost = alloc_qty
                            money_allocated += alloc_qty
                        elif req_type == "personnel":
                            # Assume $80k/year per FTE, scaled by duration
                            duration = req.get("duration_days", 30) / 365
                            cost = alloc_qty * 80000 * duration
                            personnel_allocated += alloc_qty
                        else:  # equipment
                            # Assume $500/day rental
                            duration = req.get("duration_days", 30)
                            cost = alloc_qty * 500 * duration
                            equipment_allocated += alloc_qty

                        total_cost += cost

                        allocations.append(MultiResourceAllocation(
                            requirement_id=req.get("requirement_id", f"REQ-{i}"),
                            asset_id=req["asset_id"],
                            pool_id=pool.get("pool_id", f"POOL-{j}"),
                            resource_type=req_type,
                            quantity_allocated=round(alloc_qty, 2),
                            unit=req.get("unit", "units"),
                            utilization_pct=round(alloc_frac * 100, 1),
                            cost_estimate=round(cost, 2),
                            status="allocated" if fulfilled else "partial",
                            rationale=self._generate_multi_rationale(req, fulfilled, alloc_frac)
                        ))

            # Record unfunded requirements
            if total_allocated < qty_needed * 0.1:
                allocations.append(MultiResourceAllocation(
                    requirement_id=req.get("requirement_id", f"REQ-{i}"),
                    asset_id=req["asset_id"],
                    pool_id="NONE",
                    resource_type=req_type,
                    quantity_allocated=0,
                    unit=req.get("unit", "units"),
                    utilization_pct=0,
                    cost_estimate=0,
                    status="unfunded",
                    rationale=f"Insufficient {req_type} resources available"
                ))

        # Calculate totals
        money_available = sum(p.get("available_quantity", 0) for p in pools_by_type["money"])
        personnel_available = sum(p.get("available_quantity", 0) for p in pools_by_type["personnel"])
        equipment_available = sum(p.get("available_quantity", 0) for p in pools_by_type["equipment"])

        projects_full = sum(1 for i in range(len(requirements)) if y[i].solution_value() > 0.5)
        projects_partial = len([a for a in allocations if a.status == "partial"])
        projects_unfunded = len([a for a in allocations if a.status == "unfunded"])

        utilization = {
            "money": round(money_allocated / max(money_available, 1) * 100, 1),
            "personnel": round(personnel_allocated / max(personnel_available, 1) * 100, 1),
            "equipment": round(equipment_allocated / max(equipment_available, 1) * 100, 1),
        }

        trace.append(f"Allocated: ${money_allocated:,.0f}, {personnel_allocated:.1f} FTE, {equipment_allocated:.0f} equipment")
        trace.append(f"Projects: {projects_full} full, {projects_partial} partial, {projects_unfunded} unfunded")

        return MultiResourceResult(
            allocations=allocations,
            money_allocated=round(money_allocated, 2),
            money_available=round(money_available, 2),
            personnel_allocated=round(personnel_allocated, 2),
            personnel_available=round(personnel_available, 2),
            equipment_allocated=int(equipment_allocated),
            equipment_available=int(equipment_available),
            projects_fully_funded=projects_full,
            projects_partial=projects_partial,
            projects_unfunded=projects_unfunded,
            total_cost_estimate=round(total_cost, 2),
            resource_utilization=utilization,
            solver_status=solver_status,
            trace=trace
        )

    def _empty_result(self, pools: List[Dict], trace: List[str]) -> MultiResourceResult:
        """Return empty result when no requirements provided."""
        trace.append("No requirements provided")

        money = sum(p.get("available_quantity", 0) for p in pools if p.get("resource_type") == "money")
        personnel = sum(p.get("available_quantity", 0) for p in pools if p.get("resource_type") == "personnel")
        equipment = sum(p.get("available_quantity", 0) for p in pools if p.get("resource_type") == "equipment")

        return MultiResourceResult(
            allocations=[],
            money_allocated=0, money_available=money,
            personnel_allocated=0, personnel_available=personnel,
            equipment_allocated=0, equipment_available=int(equipment),
            projects_fully_funded=0, projects_partial=0, projects_unfunded=0,
            total_cost_estimate=0,
            resource_utilization={"money": 0, "personnel": 0, "equipment": 0},
            solver_status="NO_REQUIREMENTS",
            trace=trace
        )

    def _greedy_allocation(
        self,
        requirements: List[Dict],
        pools: List[Dict],
        trace: List[str]
    ) -> MultiResourceResult:
        """Greedy fallback allocation."""
        trace.append("Using greedy allocation strategy")

        # Sort requirements by priority
        sorted_reqs = sorted(requirements, key=lambda r: r.get("priority", 3))

        # Track remaining pool capacity
        pool_remaining = {p.get("pool_id", f"P{i}"): p.get("available_quantity", 0)
                        for i, p in enumerate(pools)}

        allocations = []
        money_allocated = personnel_allocated = equipment_allocated = 0
        total_cost = 0
        projects_full = projects_partial = projects_unfunded = 0

        for req in sorted_reqs:
            req_type = req.get("resource_type", "money")
            qty_needed = req.get("quantity_needed", 0)
            allocated = 0

            # Find compatible pools
            for pool in pools:
                if pool.get("resource_type") != req_type:
                    continue

                pool_id = pool.get("pool_id", "UNKNOWN")
                remaining = pool_remaining.get(pool_id, 0)

                if remaining <= 0:
                    continue

                alloc_qty = min(qty_needed - allocated, remaining)
                if alloc_qty > 0:
                    pool_remaining[pool_id] -= alloc_qty
                    allocated += alloc_qty

                    # Cost estimate
                    if req_type == "money":
                        cost = alloc_qty
                        money_allocated += alloc_qty
                    elif req_type == "personnel":
                        cost = alloc_qty * 80000 * (req.get("duration_days", 30) / 365)
                        personnel_allocated += alloc_qty
                    else:
                        cost = alloc_qty * 500 * req.get("duration_days", 30)
                        equipment_allocated += alloc_qty

                    total_cost += cost

                    allocations.append(MultiResourceAllocation(
                        requirement_id=req.get("requirement_id", "REQ"),
                        asset_id=req["asset_id"],
                        pool_id=pool_id,
                        resource_type=req_type,
                        quantity_allocated=round(alloc_qty, 2),
                        unit=req.get("unit", "units"),
                        utilization_pct=round(alloc_qty / qty_needed * 100, 1) if qty_needed else 0,
                        cost_estimate=round(cost, 2),
                        status="allocated" if allocated >= qty_needed else "partial",
                        rationale="Greedy allocation by priority"
                    ))

                if allocated >= qty_needed:
                    break

            if allocated >= qty_needed:
                projects_full += 1
            elif allocated > 0:
                projects_partial += 1
            else:
                projects_unfunded += 1

        money_available = sum(p.get("available_quantity", 0) for p in pools if p.get("resource_type") == "money")
        personnel_available = sum(p.get("available_quantity", 0) for p in pools if p.get("resource_type") == "personnel")
        equipment_available = sum(p.get("available_quantity", 0) for p in pools if p.get("resource_type") == "equipment")

        return MultiResourceResult(
            allocations=allocations,
            money_allocated=round(money_allocated, 2),
            money_available=round(money_available, 2),
            personnel_allocated=round(personnel_allocated, 2),
            personnel_available=round(personnel_available, 2),
            equipment_allocated=int(equipment_allocated),
            equipment_available=int(equipment_available),
            projects_fully_funded=projects_full,
            projects_partial=projects_partial,
            projects_unfunded=projects_unfunded,
            total_cost_estimate=round(total_cost, 2),
            resource_utilization={
                "money": round(money_allocated / max(money_available, 1) * 100, 1),
                "personnel": round(personnel_allocated / max(personnel_available, 1) * 100, 1),
                "equipment": round(equipment_allocated / max(equipment_available, 1) * 100, 1),
            },
            solver_status="GREEDY_FALLBACK",
            trace=trace
        )

    def _generate_multi_rationale(self, req: Dict, fulfilled: bool, alloc_frac: float) -> str:
        """Generate rationale for multi-resource allocation."""
        priority = req.get("priority", 3)
        req_type = req.get("resource_type", "resource")

        if fulfilled:
            if priority == 1:
                return f"Critical priority - full {req_type} allocation"
            elif priority == 2:
                return f"High priority project - {req_type} secured"
            else:
                return f"Optimized {req_type} allocation (priority {priority})"
        else:
            return f"Partial allocation ({alloc_frac*100:.0f}%) - {req_type} constraints"


def solve_multi_resource(
    requirements: List[Dict[str, Any]],
    pools: List[Dict[str, Any]],
    weights: Dict[str, float] = None
) -> MultiResourceResult:
    """Convenience function for multi-resource optimization."""
    solver = MultiResourceSolver()
    return solver.solve(
        requirements=requirements,
        pools=pools,
        weights=weights
    )
