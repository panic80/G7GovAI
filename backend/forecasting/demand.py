"""
Infrastructure Demand Forecasting
=================================
Projects future demand based on population and usage trends.
"""

from dataclasses import dataclass
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
import math
import random

random.seed(42)

# Import demographics service for population data
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from services.mock_external.demographics_service import get_demographics_service
except ImportError:
    get_demographics_service = None

try:
    from config.thresholds import CAPACITY_THRESHOLDS, DEMAND_ELASTICITY
except ImportError:
    # Fallback if config not available
    CAPACITY_THRESHOLDS = {"warning": 0.75, "critical": 0.90}
    DEMAND_ELASTICITY = {
        "Bridge": 1.2,
        "Highway Segment": 1.3,
        "Water Main": 0.9,
        "Public Building": 1.0,
        "Hospital": 1.1,
    }


@dataclass
class DemandForecast:
    """Demand forecast for an asset or service."""
    asset_id: str
    asset_type: str
    region: str
    current_usage: float
    forecasts: List[Dict]  # [{year, demand, capacity_utilization, growth_rate}]
    peak_demand_year: int
    requires_expansion: bool
    expansion_timeline: Optional[str]


@dataclass
class CapacityGap:
    """Analysis of capacity vs demand gap."""
    asset_id: str
    current_capacity: float
    current_demand: float
    utilization_pct: float
    projected_demand_5yr: float
    projected_gap_5yr: float
    gap_severity: str  # None, Minor, Moderate, Severe, Critical
    recommended_action: str


@dataclass
class Bottleneck:
    """Infrastructure bottleneck identification."""
    asset_id: str
    asset_name: str
    region: str
    bottleneck_type: str  # Capacity, Condition, Access
    severity: float  # 0-1
    affected_population: int
    impact_description: str
    resolution_priority: int


class DemandModel:
    """
    Infrastructure demand forecasting model.

    Projects future demand based on:
    - Population growth
    - Historical usage trends
    - Asset type characteristics
    - Regional economic factors
    """

    # Use centralized config for thresholds and elasticity
    # Capacity thresholds (from config.thresholds)
    UTILIZATION_WARNING = CAPACITY_THRESHOLDS["warning"]
    UTILIZATION_CRITICAL = CAPACITY_THRESHOLDS["critical"]

    def __init__(self):
        self.demographics = get_demographics_service() if get_demographics_service else None

    def forecast_demand(
        self,
        asset_id: str,
        asset_type: str,
        region: str,
        current_usage: float,
        current_capacity: float,
        horizon_years: int = 10
    ) -> DemandForecast:
        """
        Forecast demand for an asset.

        Args:
            asset_id: Asset identifier
            asset_type: Type of asset
            region: Region code
            current_usage: Current daily/annual usage
            current_capacity: Current capacity
            horizon_years: Years to forecast

        Returns:
            DemandForecast with projections
        """
        elasticity = DEMAND_ELASTICITY.get(asset_type, 1.0)

        # Get population growth rate
        if self.demographics:
            projection = self.demographics.get_population_projection(region, horizon_years)
            base_growth_rate = projection.projections[1]["growth_rate"] / 100 if len(projection.projections) > 1 else 0.015
        else:
            base_growth_rate = 0.015  # Default 1.5%

        forecasts = []
        current_year = date.today().year
        peak_demand = current_usage
        peak_year = current_year
        requires_expansion = False
        expansion_year = None

        for year_offset in range(horizon_years + 1):
            year = current_year + year_offset

            # Demand growth with elasticity
            # Add some variance and diminishing returns over time
            year_growth = base_growth_rate * elasticity * (1 - year_offset * 0.02)
            year_growth += random.gauss(0, 0.005)  # Small variance

            # Compound growth
            demand = current_usage * math.pow(1 + year_growth, year_offset)

            # Capacity utilization
            utilization = demand / current_capacity if current_capacity > 0 else 1.0

            forecasts.append({
                "year": year,
                "demand": round(demand, 0),
                "capacity": current_capacity,
                "capacity_utilization": round(utilization, 3),
                "growth_rate": round(year_growth * 100, 2)
            })

            # Track peak
            if demand > peak_demand:
                peak_demand = demand
                peak_year = year

            # Check if expansion needed
            if utilization > self.UTILIZATION_CRITICAL and not requires_expansion:
                requires_expansion = True
                expansion_year = year

        # Expansion timeline
        if requires_expansion and expansion_year:
            years_until = expansion_year - current_year
            if years_until <= 2:
                expansion_timeline = f"Critical: Expansion needed within {years_until} years"
            elif years_until <= 5:
                expansion_timeline = f"Planning: Begin expansion planning for {expansion_year}"
            else:
                expansion_timeline = f"Monitor: Review capacity needs by {expansion_year - 2}"
        else:
            expansion_timeline = None

        return DemandForecast(
            asset_id=asset_id,
            asset_type=asset_type,
            region=region,
            current_usage=current_usage,
            forecasts=forecasts,
            peak_demand_year=peak_year,
            requires_expansion=requires_expansion,
            expansion_timeline=expansion_timeline
        )

    def get_capacity_gap(
        self,
        asset_id: str,
        asset_type: str,
        region: str,
        current_usage: float,
        current_capacity: float
    ) -> CapacityGap:
        """
        Analyze capacity vs demand gap.

        Args:
            asset_id: Asset identifier
            asset_type: Asset type
            region: Region code
            current_usage: Current usage
            current_capacity: Current capacity

        Returns:
            CapacityGap analysis
        """
        # Current utilization
        utilization = current_usage / current_capacity if current_capacity > 0 else 1.0

        # 5-year forecast
        forecast = self.forecast_demand(
            asset_id, asset_type, region, current_usage, current_capacity, 5
        )

        # Get 5-year projected demand
        year_5 = forecast.forecasts[-1] if forecast.forecasts else {"demand": current_usage}
        projected_demand = year_5["demand"]
        projected_gap = projected_demand - current_capacity

        # Determine severity
        projected_util = projected_demand / current_capacity if current_capacity > 0 else 1.0

        if projected_util <= 0.7:
            severity = "None"
            action = "No action needed; capacity adequate"
        elif projected_util <= 0.85:
            severity = "Minor"
            action = "Monitor usage trends; begin preliminary planning"
        elif projected_util <= 0.95:
            severity = "Moderate"
            action = "Initiate capacity study; consider optimization measures"
        elif projected_util <= 1.1:
            severity = "Severe"
            action = "Begin expansion design; implement demand management"
        else:
            severity = "Critical"
            action = "Emergency expansion required; immediate intervention needed"

        return CapacityGap(
            asset_id=asset_id,
            current_capacity=current_capacity,
            current_demand=current_usage,
            utilization_pct=round(utilization * 100, 1),
            projected_demand_5yr=round(projected_demand, 0),
            projected_gap_5yr=round(max(0, projected_gap), 0),
            gap_severity=severity,
            recommended_action=action
        )

    def identify_bottlenecks(
        self,
        assets: List[Dict],
        region: str,
        population: int = 1_000_000
    ) -> List[Bottleneck]:
        """
        Identify infrastructure bottlenecks in a region.

        Args:
            assets: List of asset dicts with usage and capacity
            region: Region code
            population: Regional population

        Returns:
            List of Bottleneck identifications, sorted by priority
        """
        bottlenecks = []

        for asset in assets:
            asset_id = asset.get("id", "unknown")
            asset_name = asset.get("name", "Unknown Asset")
            asset_type = asset.get("type", "Other")
            current_usage = asset.get("daily_usage", 0)
            current_capacity = asset.get("capacity", current_usage * 1.5)
            condition = asset.get("condition_score", 70)

            # Calculate utilization
            utilization = current_usage / current_capacity if current_capacity > 0 else 0

            # Check for capacity bottleneck
            if utilization > 0.85:
                severity = min(1.0, (utilization - 0.85) / 0.15)
                affected = int(current_usage * 0.5)  # Simplified

                bottlenecks.append(Bottleneck(
                    asset_id=asset_id,
                    asset_name=asset_name,
                    region=region,
                    bottleneck_type="Capacity",
                    severity=round(severity, 3),
                    affected_population=affected,
                    impact_description=f"Operating at {utilization*100:.0f}% capacity; service degradation likely",
                    resolution_priority=1 if severity > 0.7 else 2
                ))

            # Check for condition bottleneck
            if condition < 50:
                severity = (50 - condition) / 50
                affected = int(current_usage * 0.3)

                bottlenecks.append(Bottleneck(
                    asset_id=asset_id,
                    asset_name=asset_name,
                    region=region,
                    bottleneck_type="Condition",
                    severity=round(severity, 3),
                    affected_population=affected,
                    impact_description=f"Poor condition ({condition}/100); reliability concerns",
                    resolution_priority=1 if condition < 30 else 2
                ))

        # Sort by severity then priority
        bottlenecks.sort(key=lambda b: (-b.severity, b.resolution_priority))

        return bottlenecks

    def calculate_anticipatory_score(
        self,
        assets: List[Dict],
        planned_maintenance: List[Dict],
        planned_expansions: List[Dict]
    ) -> Dict:
        """
        Calculate anticipatory vs reactive score.

        Higher score = more proactive planning.

        Args:
            assets: List of assets with condition/capacity
            planned_maintenance: List of planned maintenance actions
            planned_expansions: List of planned capacity expansions

        Returns:
            Dict with score and breakdown
        """
        total_assets = len(assets)
        if total_assets == 0:
            return {"score": 0, "status": "No assets"}

        # Count proactive vs reactive
        proactive_maintenance = 0
        reactive_maintenance = 0
        proactive_expansion = 0
        reactive_expansion = 0

        for asset in assets:
            condition = asset.get("condition_score", 70)
            utilization = asset.get("utilization", 0.5)
            asset_id = asset.get("id")

            # Check if maintenance is planned before critical
            has_planned_maint = any(
                m.get("asset_id") == asset_id for m in planned_maintenance
            )

            if condition < 40:
                # Asset already critical
                if has_planned_maint:
                    reactive_maintenance += 1  # Too late, it's reactive
                else:
                    reactive_maintenance += 1
            elif condition < 60 and has_planned_maint:
                proactive_maintenance += 1  # Good, planned before critical

            # Check capacity expansion
            has_planned_expansion = any(
                e.get("asset_id") == asset_id for e in planned_expansions
            )

            if utilization > 0.95:
                # Already at capacity
                reactive_expansion += 1
            elif utilization > 0.75 and has_planned_expansion:
                proactive_expansion += 1

        # Calculate score
        total_proactive = proactive_maintenance + proactive_expansion
        total_reactive = reactive_maintenance + reactive_expansion
        total_actions = total_proactive + total_reactive

        if total_actions == 0:
            score = 0.5  # Neutral
        else:
            score = total_proactive / total_actions

        # Status label
        if score >= 0.8:
            status = "Highly Proactive"
        elif score >= 0.6:
            status = "Mostly Proactive"
        elif score >= 0.4:
            status = "Mixed"
        elif score >= 0.2:
            status = "Mostly Reactive"
        else:
            status = "Reactive"

        return {
            "score": round(score, 3),
            "score_pct": round(score * 100, 1),
            "status": status,
            "proactive_maintenance": proactive_maintenance,
            "reactive_maintenance": reactive_maintenance,
            "proactive_expansion": proactive_expansion,
            "reactive_expansion": reactive_expansion,
            "total_assets": total_assets
        }


# Convenience functions using singleton
_demand_model = None

def _get_model() -> DemandModel:
    global _demand_model
    if _demand_model is None:
        _demand_model = DemandModel()
    return _demand_model

def forecast_demand(
    asset_id: str,
    asset_type: str,
    region: str,
    current_usage: float,
    current_capacity: float,
    horizon_years: int = 10
) -> DemandForecast:
    """Convenience function to forecast demand."""
    return _get_model().forecast_demand(
        asset_id, asset_type, region, current_usage,
        current_capacity, horizon_years
    )

def get_capacity_gap(
    asset_id: str,
    asset_type: str,
    region: str,
    current_usage: float,
    current_capacity: float
) -> CapacityGap:
    """Convenience function to get capacity gap."""
    return _get_model().get_capacity_gap(
        asset_id, asset_type, region, current_usage, current_capacity
    )

def identify_bottlenecks(
    assets: List[Dict],
    region: str,
    population: int = 1_000_000
) -> List[Bottleneck]:
    """Convenience function to identify bottlenecks."""
    return _get_model().identify_bottlenecks(assets, region, population)
