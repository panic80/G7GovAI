"""
Mock Weather Service
====================
Simulates Environment Canada / NOAA weather data for hackathon demo.
"""

from dataclasses import dataclass
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
import random
import math

# Seed for reproducibility in demo
random.seed(42)


@dataclass
class WeatherDay:
    """Single day weather data."""
    date: date
    temp_high_c: float
    temp_low_c: float
    precipitation_mm: float
    humidity_pct: float
    wind_speed_kmh: float
    conditions: str  # Clear, Cloudy, Rain, Snow, Storm


@dataclass
class WeatherForecast:
    """Multi-day weather forecast."""
    region: str
    generated_at: datetime
    days: List[WeatherDay]


@dataclass
class ExtremeWeatherRisk:
    """Risk assessment for extreme weather events."""
    region: str
    month: int
    flood_risk: float  # 0-1
    snowstorm_risk: float  # 0-1
    heatwave_risk: float  # 0-1
    wildfire_risk: float  # 0-1
    overall_risk: str  # Low, Medium, High, Critical


@dataclass
class WeatherImpact:
    """Weather impact on infrastructure."""
    asset_id: str
    impact_type: str  # deterioration_acceleration, capacity_reduction
    impact_factor: float  # 1.0 = no impact, >1.0 = accelerated deterioration
    reason: str


class WeatherService:
    """
    Mock weather service for demo purposes.

    In production, would integrate with:
    - Environment Canada API
    - NOAA Weather Service
    - OpenWeatherMap API
    """

    # Regional climate profiles (mock data)
    CLIMATE_PROFILES = {
        "ON-Toronto": {"summer_high": 27, "winter_low": -10, "annual_precip": 831, "snow_days": 45},
        "ON-Ottawa": {"summer_high": 26, "winter_low": -15, "annual_precip": 943, "snow_days": 55},
        "QC-Montreal": {"summer_high": 26, "winter_low": -14, "annual_precip": 1000, "snow_days": 60},
        "BC-Vancouver": {"summer_high": 22, "winter_low": 2, "annual_precip": 1189, "snow_days": 11},
        "AB-Calgary": {"summer_high": 23, "winter_low": -15, "annual_precip": 419, "snow_days": 58},
        "AB-Edmonton": {"summer_high": 23, "winter_low": -17, "annual_precip": 476, "snow_days": 65},
        "SK-Regina": {"summer_high": 26, "winter_low": -20, "annual_precip": 390, "snow_days": 52},
        "MB-Winnipeg": {"summer_high": 26, "winter_low": -21, "annual_precip": 521, "snow_days": 57},
        "NS-Halifax": {"summer_high": 23, "winter_low": -8, "annual_precip": 1468, "snow_days": 44},
        "NB-Fredericton": {"summer_high": 25, "winter_low": -14, "annual_precip": 1131, "snow_days": 55},
        "default": {"summer_high": 25, "winter_low": -10, "annual_precip": 800, "snow_days": 40},
    }

    # Seasonal extreme weather probabilities by month
    EXTREME_WEATHER_PROBS = {
        1: {"flood": 0.05, "snowstorm": 0.35, "heatwave": 0.0, "wildfire": 0.0},
        2: {"flood": 0.05, "snowstorm": 0.30, "heatwave": 0.0, "wildfire": 0.0},
        3: {"flood": 0.15, "snowstorm": 0.20, "heatwave": 0.0, "wildfire": 0.0},
        4: {"flood": 0.25, "snowstorm": 0.05, "heatwave": 0.0, "wildfire": 0.05},
        5: {"flood": 0.20, "snowstorm": 0.0, "heatwave": 0.05, "wildfire": 0.10},
        6: {"flood": 0.15, "snowstorm": 0.0, "heatwave": 0.15, "wildfire": 0.15},
        7: {"flood": 0.10, "snowstorm": 0.0, "heatwave": 0.25, "wildfire": 0.25},
        8: {"flood": 0.10, "snowstorm": 0.0, "heatwave": 0.20, "wildfire": 0.30},
        9: {"flood": 0.15, "snowstorm": 0.0, "heatwave": 0.05, "wildfire": 0.15},
        10: {"flood": 0.20, "snowstorm": 0.05, "heatwave": 0.0, "wildfire": 0.05},
        11: {"flood": 0.15, "snowstorm": 0.15, "heatwave": 0.0, "wildfire": 0.0},
        12: {"flood": 0.05, "snowstorm": 0.30, "heatwave": 0.0, "wildfire": 0.0},
    }

    def __init__(self):
        pass

    def get_weather_forecast(
        self,
        region: str,
        days_ahead: int = 14
    ) -> WeatherForecast:
        """
        Get weather forecast for a region.

        Args:
            region: Region code (e.g., "ON-Toronto", "BC-Vancouver")
            days_ahead: Number of days to forecast (max 14)

        Returns:
            WeatherForecast with daily predictions
        """
        profile = self.CLIMATE_PROFILES.get(region, self.CLIMATE_PROFILES["default"])
        today = date.today()

        days = []
        for i in range(min(days_ahead, 14)):
            day_date = today + timedelta(days=i)
            month = day_date.month

            # Calculate seasonal temperature
            seasonal_factor = math.cos((month - 7) * math.pi / 6)  # Peak in July
            base_temp = (profile["summer_high"] + profile["winter_low"]) / 2
            temp_range = (profile["summer_high"] - profile["winter_low"]) / 2

            temp_high = base_temp + temp_range * seasonal_factor + random.gauss(0, 3)
            temp_low = temp_high - random.uniform(5, 12)

            # Precipitation
            daily_precip_avg = profile["annual_precip"] / 365
            precip = max(0, random.expovariate(1/daily_precip_avg)) if random.random() > 0.6 else 0

            # Conditions based on precip and temp
            if precip > 10:
                conditions = "Snow" if temp_high < 0 else "Rain"
            elif precip > 0:
                conditions = "Snow" if temp_high < 0 else "Cloudy"
            else:
                conditions = "Clear" if random.random() > 0.4 else "Cloudy"

            days.append(WeatherDay(
                date=day_date,
                temp_high_c=round(temp_high, 1),
                temp_low_c=round(temp_low, 1),
                precipitation_mm=round(precip, 1),
                humidity_pct=round(random.uniform(40, 80), 0),
                wind_speed_kmh=round(random.uniform(5, 40), 0),
                conditions=conditions
            ))

        return WeatherForecast(
            region=region,
            generated_at=datetime.now(),
            days=days
        )

    def get_historical_weather(
        self,
        region: str,
        start_date: date,
        end_date: date
    ) -> List[WeatherDay]:
        """
        Get historical weather data for a region.

        Args:
            region: Region code
            start_date: Start date
            end_date: End date

        Returns:
            List of WeatherDay objects
        """
        profile = self.CLIMATE_PROFILES.get(region, self.CLIMATE_PROFILES["default"])
        days = []

        current = start_date
        while current <= end_date:
            month = current.month

            seasonal_factor = math.cos((month - 7) * math.pi / 6)
            base_temp = (profile["summer_high"] + profile["winter_low"]) / 2
            temp_range = (profile["summer_high"] - profile["winter_low"]) / 2

            temp_high = base_temp + temp_range * seasonal_factor + random.gauss(0, 2)
            temp_low = temp_high - random.uniform(5, 12)

            daily_precip_avg = profile["annual_precip"] / 365
            precip = max(0, random.expovariate(1/daily_precip_avg)) if random.random() > 0.7 else 0

            if precip > 10:
                conditions = "Snow" if temp_high < 0 else "Rain"
            elif precip > 0:
                conditions = "Cloudy"
            else:
                conditions = "Clear"

            days.append(WeatherDay(
                date=current,
                temp_high_c=round(temp_high, 1),
                temp_low_c=round(temp_low, 1),
                precipitation_mm=round(precip, 1),
                humidity_pct=round(random.uniform(40, 80), 0),
                wind_speed_kmh=round(random.uniform(5, 30), 0),
                conditions=conditions
            ))
            current += timedelta(days=1)

        return days

    def get_extreme_weather_risk(
        self,
        region: str,
        month: int
    ) -> ExtremeWeatherRisk:
        """
        Get extreme weather risk assessment for a region and month.

        Args:
            region: Region code
            month: Month number (1-12)

        Returns:
            ExtremeWeatherRisk with probabilities
        """
        base_probs = self.EXTREME_WEATHER_PROBS.get(month, self.EXTREME_WEATHER_PROBS[1])

        # Regional adjustments
        region_adjustments = {
            "BC-Vancouver": {"flood": 1.3, "wildfire": 1.5},
            "AB-Calgary": {"flood": 1.2, "snowstorm": 1.1},
            "MB-Winnipeg": {"flood": 1.4, "snowstorm": 1.2},
            "ON-Toronto": {"flood": 0.9, "heatwave": 1.2},
            "QC-Montreal": {"snowstorm": 1.2, "flood": 1.1},
            "NS-Halifax": {"flood": 1.3, "snowstorm": 0.9},
        }

        adjustments = region_adjustments.get(region, {})

        flood_risk = min(1.0, base_probs["flood"] * adjustments.get("flood", 1.0))
        snowstorm_risk = min(1.0, base_probs["snowstorm"] * adjustments.get("snowstorm", 1.0))
        heatwave_risk = min(1.0, base_probs["heatwave"] * adjustments.get("heatwave", 1.0))
        wildfire_risk = min(1.0, base_probs["wildfire"] * adjustments.get("wildfire", 1.0))

        # Overall risk
        max_risk = max(flood_risk, snowstorm_risk, heatwave_risk, wildfire_risk)
        if max_risk > 0.4:
            overall = "Critical"
        elif max_risk > 0.25:
            overall = "High"
        elif max_risk > 0.1:
            overall = "Medium"
        else:
            overall = "Low"

        return ExtremeWeatherRisk(
            region=region,
            month=month,
            flood_risk=round(flood_risk, 3),
            snowstorm_risk=round(snowstorm_risk, 3),
            heatwave_risk=round(heatwave_risk, 3),
            wildfire_risk=round(wildfire_risk, 3),
            overall_risk=overall
        )

    def get_weather_impact_on_assets(
        self,
        asset_ids: List[str],
        asset_types: Dict[str, str],
        region: str,
        forecast: Optional[WeatherForecast] = None
    ) -> List[WeatherImpact]:
        """
        Calculate weather impact on infrastructure assets.

        Args:
            asset_ids: List of asset IDs to analyze
            asset_types: Mapping of asset_id -> asset_type
            region: Region code
            forecast: Optional weather forecast (will generate if not provided)

        Returns:
            List of WeatherImpact assessments
        """
        if forecast is None:
            forecast = self.get_weather_forecast(region, 14)

        impacts = []

        # Analyze forecast for impact factors
        avg_temp = sum(d.temp_high_c for d in forecast.days) / len(forecast.days)
        total_precip = sum(d.precipitation_mm for d in forecast.days)
        freeze_thaw_cycles = sum(
            1 for d in forecast.days
            if d.temp_high_c > 0 and d.temp_low_c < 0
        )

        for asset_id in asset_ids:
            asset_type = asset_types.get(asset_id, "Other")

            # Calculate impact based on asset type and weather
            impact_factor = 1.0
            reasons = []

            if asset_type == "Bridge":
                if freeze_thaw_cycles > 5:
                    impact_factor += 0.2 * (freeze_thaw_cycles / 7)
                    reasons.append(f"{freeze_thaw_cycles} freeze-thaw cycles accelerate deck deterioration")
                if total_precip > 50:
                    impact_factor += 0.1
                    reasons.append("High precipitation increases corrosion risk")

            elif asset_type == "Highway Segment":
                if freeze_thaw_cycles > 5:
                    impact_factor += 0.15 * (freeze_thaw_cycles / 7)
                    reasons.append("Freeze-thaw cycles create potholes")
                if total_precip > 100:
                    impact_factor += 0.1
                    reasons.append("Heavy precipitation causes surface erosion")

            elif asset_type == "Water Main":
                if avg_temp < -5:
                    impact_factor += 0.25
                    reasons.append("Cold temperatures increase pipe stress and break risk")

            elif asset_type == "Public Building":
                if avg_temp > 30 or avg_temp < -15:
                    impact_factor += 0.1
                    reasons.append("Extreme temperatures strain HVAC systems")

            elif asset_type == "Hospital":
                if total_precip > 75:
                    impact_factor += 0.05
                    reasons.append("High precipitation may cause water intrusion")

            if impact_factor > 1.0:
                impacts.append(WeatherImpact(
                    asset_id=asset_id,
                    impact_type="deterioration_acceleration",
                    impact_factor=round(impact_factor, 3),
                    reason="; ".join(reasons)
                ))

        return impacts


# Singleton instance for easy access
_weather_service = None

def get_weather_service() -> WeatherService:
    """Get the singleton weather service instance."""
    global _weather_service
    if _weather_service is None:
        _weather_service = WeatherService()
    return _weather_service
