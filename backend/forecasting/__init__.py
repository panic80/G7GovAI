"""
Forecasting Module for ForesightOps
===================================
Predictive models for infrastructure deterioration and demand.
"""

from .deterioration import (
    DeteriorationModel,
    ForecastPoint,
    ConditionForecast,
    MaintenanceWindow,
    predict_condition,
    estimate_failure_probability,
    get_maintenance_window,
)

from .demand import (
    DemandModel,
    DemandForecast,
    CapacityGap,
    Bottleneck,
    forecast_demand,
    get_capacity_gap,
    identify_bottlenecks,
)

__all__ = [
    # Deterioration
    "DeteriorationModel",
    "ForecastPoint",
    "ConditionForecast",
    "MaintenanceWindow",
    "predict_condition",
    "estimate_failure_probability",
    "get_maintenance_window",
    # Demand
    "DemandModel",
    "DemandForecast",
    "CapacityGap",
    "Bottleneck",
    "forecast_demand",
    "get_capacity_gap",
    "identify_bottlenecks",
]
