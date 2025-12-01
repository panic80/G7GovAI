"""
Infrastructure Deterioration Forecasting
========================================
Predicts asset condition over time using decay models.
"""

from dataclasses import dataclass
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
import math
import random

random.seed(42)


@dataclass
class ForecastPoint:
    """Single point in a condition forecast."""
    date: date
    predicted_condition: float  # 0-100
    confidence_lower: float
    confidence_upper: float
    failure_probability: float  # 0-1
    maintenance_recommended: bool


@dataclass
class ConditionForecast:
    """Complete condition forecast for an asset."""
    asset_id: str
    asset_type: str
    current_condition: float
    forecast_points: List[ForecastPoint]
    expected_failure_date: Optional[date]
    years_to_failure: Optional[float]
    deterioration_rate: float  # condition points per year
    weather_impact_factor: float
    usage_impact_factor: float


@dataclass
class MaintenanceWindow:
    """Optimal maintenance window recommendation."""
    asset_id: str
    recommended_start: date
    recommended_end: date
    urgency: str  # Critical, High, Medium, Low
    estimated_cost: float
    risk_if_delayed: str
    condition_at_window: float


class DeteriorationModel:
    """
    Infrastructure deterioration prediction model.

    Uses exponential decay with adjustments for:
    - Asset type (bridges deteriorate differently than water mains)
    - Age
    - Weather exposure
    - Usage intensity
    """

    # Decay rates (lambda) by asset type - higher = faster decay
    DECAY_RATES = {
        "Bridge": 0.025,  # ~2.5% per year base
        "Highway Segment": 0.035,  # ~3.5% per year
        "Water Main": 0.020,  # ~2% per year
        "Public Building": 0.015,  # ~1.5% per year
        "Hospital": 0.012,  # ~1.2% per year (better maintained)
        "Other": 0.025,
    }

    # Critical condition thresholds
    CRITICAL_THRESHOLD = 40  # Below this is critical
    MAINTENANCE_THRESHOLD = 60  # Below this needs maintenance

    def __init__(self):
        pass

    def predict_condition(
        self,
        asset_id: str,
        asset_type: str,
        current_condition: float,
        age_years: int,
        horizon_years: int = 10,
        weather_factor: float = 1.0,
        usage_factor: float = 1.0
    ) -> ConditionForecast:
        """
        Predict asset condition over time.

        Args:
            asset_id: Asset identifier
            asset_type: Type of asset (Bridge, Highway, etc.)
            current_condition: Current condition score (0-100)
            age_years: Current age of asset
            horizon_years: Years to forecast
            weather_factor: Weather impact multiplier (1.0 = normal)
            usage_factor: Usage intensity multiplier (1.0 = normal)

        Returns:
            ConditionForecast with predictions
        """
        base_lambda = self.DECAY_RATES.get(asset_type, self.DECAY_RATES["Other"])

        # Adjust decay rate based on factors
        adjusted_lambda = base_lambda * weather_factor * usage_factor

        # Age acceleration: older assets deteriorate faster
        age_factor = 1 + (age_years / 100)  # 1% increase per year of age
        adjusted_lambda *= age_factor

        forecast_points = []
        today = date.today()
        expected_failure_date = None

        for year in range(horizon_years + 1):
            forecast_date = today + timedelta(days=365 * year)

            # Exponential decay: C(t) = C0 * exp(-lambda * t)
            predicted = current_condition * math.exp(-adjusted_lambda * year)

            # Add uncertainty that grows with time
            uncertainty = 2 + (year * 1.5)  # Wider bands for further forecasts
            lower = max(0, predicted - uncertainty)
            upper = min(100, predicted + uncertainty)

            # Failure probability using Weibull-like distribution
            # Higher when condition is low and asset is old
            failure_prob = self._calculate_failure_probability(
                predicted, age_years + year, asset_type
            )

            # Maintenance recommendation
            needs_maintenance = (
                predicted < self.MAINTENANCE_THRESHOLD or
                failure_prob > 0.3
            )

            forecast_points.append(ForecastPoint(
                date=forecast_date,
                predicted_condition=round(predicted, 1),
                confidence_lower=round(lower, 1),
                confidence_upper=round(upper, 1),
                failure_probability=round(failure_prob, 3),
                maintenance_recommended=needs_maintenance
            ))

            # Track expected failure date
            if expected_failure_date is None and predicted < self.CRITICAL_THRESHOLD:
                expected_failure_date = forecast_date

        # Calculate years to failure
        years_to_failure = None
        if expected_failure_date:
            years_to_failure = (expected_failure_date - today).days / 365

        # Calculate average deterioration rate
        if len(forecast_points) >= 2:
            start_cond = forecast_points[0].predicted_condition
            end_cond = forecast_points[-1].predicted_condition
            deterioration_rate = (start_cond - end_cond) / horizon_years
        else:
            deterioration_rate = current_condition * adjusted_lambda

        return ConditionForecast(
            asset_id=asset_id,
            asset_type=asset_type,
            current_condition=current_condition,
            forecast_points=forecast_points,
            expected_failure_date=expected_failure_date,
            years_to_failure=round(years_to_failure, 1) if years_to_failure else None,
            deterioration_rate=round(deterioration_rate, 2),
            weather_impact_factor=weather_factor,
            usage_impact_factor=usage_factor
        )

    def _calculate_failure_probability(
        self,
        condition: float,
        age: int,
        asset_type: str
    ) -> float:
        """Calculate probability of failure within the year."""
        # Base probability from condition
        # P(fail) increases exponentially as condition decreases
        condition_factor = math.exp(-condition / 25) if condition > 0 else 1.0

        # Age factor using Weibull-like shape
        # Most infrastructure has "bathtub" curve
        if age < 5:
            # Early life failures (rare)
            age_factor = 0.1
        elif age < 30:
            # Normal operating period
            age_factor = 0.3 + (age - 5) * 0.02
        else:
            # Wear-out period
            age_factor = 0.8 + (age - 30) * 0.03

        # Asset type adjustment
        type_factors = {
            "Bridge": 1.0,
            "Highway Segment": 0.8,
            "Water Main": 1.2,  # Underground, harder to inspect
            "Public Building": 0.7,
            "Hospital": 0.6,
        }
        type_factor = type_factors.get(asset_type, 1.0)

        # Combine factors
        probability = condition_factor * age_factor * type_factor

        # Clamp to [0, 1]
        return max(0, min(1, probability))

    def estimate_failure_probability(
        self,
        asset_id: str,
        asset_type: str,
        current_condition: float,
        age_years: int,
        target_date: date,
        weather_factor: float = 1.0,
        usage_factor: float = 1.0
    ) -> Tuple[float, str]:
        """
        Estimate failure probability by a target date.

        Returns:
            Tuple of (probability, risk_level)
        """
        today = date.today()
        years_ahead = (target_date - today).days / 365

        if years_ahead < 0:
            return 0.0, "N/A"

        # Get forecast at target date
        forecast = self.predict_condition(
            asset_id, asset_type, current_condition, age_years,
            horizon_years=int(years_ahead) + 1,
            weather_factor=weather_factor,
            usage_factor=usage_factor
        )

        # Find the point closest to target date
        closest_point = min(
            forecast.forecast_points,
            key=lambda p: abs((p.date - target_date).days)
        )

        prob = closest_point.failure_probability

        # Determine risk level
        if prob > 0.7:
            risk = "Critical"
        elif prob > 0.5:
            risk = "High"
        elif prob > 0.3:
            risk = "Medium"
        else:
            risk = "Low"

        return prob, risk

    def get_maintenance_window(
        self,
        asset_id: str,
        asset_type: str,
        current_condition: float,
        age_years: int,
        replacement_cost: float = 1_000_000
    ) -> MaintenanceWindow:
        """
        Determine optimal maintenance window.

        Returns:
            MaintenanceWindow with recommendations
        """
        today = date.today()

        # Forecast to find when maintenance is needed
        forecast = self.predict_condition(
            asset_id, asset_type, current_condition, age_years,
            horizon_years=10
        )

        # Find first point where maintenance is recommended
        maintenance_point = next(
            (p for p in forecast.forecast_points if p.maintenance_recommended),
            forecast.forecast_points[-1]  # Default to end if none found
        )

        # Window should start slightly before that point
        days_until_needed = (maintenance_point.date - today).days
        buffer_days = max(30, days_until_needed // 4)  # 25% buffer, min 30 days

        start_date = maintenance_point.date - timedelta(days=buffer_days)
        end_date = maintenance_point.date + timedelta(days=30)

        # Urgency based on current state
        if current_condition < self.CRITICAL_THRESHOLD:
            urgency = "Critical"
            start_date = today  # Immediate
            end_date = today + timedelta(days=30)
        elif current_condition < self.MAINTENANCE_THRESHOLD:
            urgency = "High"
            start_date = today + timedelta(days=30)
            end_date = today + timedelta(days=90)
        elif maintenance_point.failure_probability > 0.5:
            urgency = "Medium"
        else:
            urgency = "Low"

        # Estimate maintenance cost (simplified)
        # Major rehab costs ~20-30% of replacement
        if current_condition < 40:
            cost_pct = 0.30
        elif current_condition < 60:
            cost_pct = 0.15
        else:
            cost_pct = 0.08

        estimated_cost = replacement_cost * cost_pct

        # Risk if delayed
        if urgency == "Critical":
            risk = "Asset failure imminent; service disruption and safety risk"
        elif urgency == "High":
            risk = "Rapid deterioration; costs will increase significantly"
        elif urgency == "Medium":
            risk = "Continued deterioration; minor service impacts possible"
        else:
            risk = "Gradual deterioration; routine monitoring sufficient"

        return MaintenanceWindow(
            asset_id=asset_id,
            recommended_start=start_date,
            recommended_end=end_date,
            urgency=urgency,
            estimated_cost=round(estimated_cost, 2),
            risk_if_delayed=risk,
            condition_at_window=maintenance_point.predicted_condition
        )


# Convenience functions using singleton
_deterioration_model = None

def _get_model() -> DeteriorationModel:
    global _deterioration_model
    if _deterioration_model is None:
        _deterioration_model = DeteriorationModel()
    return _deterioration_model

def predict_condition(
    asset_id: str,
    asset_type: str,
    current_condition: float,
    age_years: int,
    horizon_years: int = 10,
    weather_factor: float = 1.0,
    usage_factor: float = 1.0
) -> ConditionForecast:
    """Convenience function to predict condition."""
    return _get_model().predict_condition(
        asset_id, asset_type, current_condition, age_years,
        horizon_years, weather_factor, usage_factor
    )

def estimate_failure_probability(
    asset_id: str,
    asset_type: str,
    current_condition: float,
    age_years: int,
    target_date: date,
    weather_factor: float = 1.0,
    usage_factor: float = 1.0
) -> Tuple[float, str]:
    """Convenience function to estimate failure probability."""
    return _get_model().estimate_failure_probability(
        asset_id, asset_type, current_condition, age_years,
        target_date, weather_factor, usage_factor
    )

def get_maintenance_window(
    asset_id: str,
    asset_type: str,
    current_condition: float,
    age_years: int,
    replacement_cost: float = 1_000_000
) -> MaintenanceWindow:
    """Convenience function to get maintenance window."""
    return _get_model().get_maintenance_window(
        asset_id, asset_type, current_condition, age_years,
        replacement_cost
    )
