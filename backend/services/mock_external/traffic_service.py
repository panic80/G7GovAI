"""
Mock Traffic & Transport Service
================================
Simulates real-time traffic and logistics data for hackathon demo.
"""

from dataclasses import dataclass
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
import random
import math

random.seed(42)


@dataclass
class TrafficCondition:
    """Current traffic condition for a route."""
    route_id: str
    timestamp: datetime
    congestion_level: float  # 0-1, 0=free flow, 1=gridlock
    average_speed_kmh: float
    travel_time_min: float
    baseline_time_min: float
    delay_min: float
    incidents: List[str]


@dataclass
class TrafficForecast:
    """Traffic forecast for a route."""
    route_id: str
    forecasts: List[Dict]  # [{time, congestion_level, expected_speed}]
    peak_hours: List[int]
    recommended_departure: Optional[datetime]


@dataclass
class CongestionRisk:
    """Congestion risk assessment for a region."""
    region: str
    time_of_day: int
    day_of_week: int
    congestion_probability: float
    expected_delay_factor: float
    high_risk_routes: List[str]


@dataclass
class ShippingEstimate:
    """Shipping time and cost estimate."""
    origin: str
    destination: str
    distance_km: float
    baseline_hours: float
    current_estimate_hours: float
    delay_factor: float
    cost_estimate_cad: float
    carrier_availability: str  # High, Medium, Low


@dataclass
class LogisticsStatus:
    """Overall logistics status for a region."""
    region: str
    timestamp: datetime
    port_congestion: float  # 0-1
    warehouse_capacity_pct: float
    trucking_availability: float  # 0-1
    rail_status: str  # Normal, Delayed, Disrupted
    overall_status: str  # Green, Yellow, Red


class TrafficService:
    """
    Mock traffic and logistics service for demo purposes.

    In production, would integrate with:
    - Google Maps Traffic API
    - Provincial DOT feeds
    - Freight tracking APIs
    - Port authority data
    """

    # Route baseline data (distance in km, time in minutes)
    ROUTES = {
        "RT-001": {"name": "Hwy 401 - Toronto to London", "distance": 200, "baseline_min": 120},
        "RT-002": {"name": "Hwy 401 - Toronto to Ottawa", "distance": 450, "baseline_min": 270},
        "RT-003": {"name": "Hwy 417 - Ottawa Downtown", "distance": 25, "baseline_min": 30},
        "RT-004": {"name": "Trans-Canada - Calgary to Vancouver", "distance": 1050, "baseline_min": 660},
        "RT-005": {"name": "Hwy 2 - Calgary to Edmonton", "distance": 300, "baseline_min": 180},
        "RT-006": {"name": "QEW - Toronto to Hamilton", "distance": 70, "baseline_min": 50},
        "RT-007": {"name": "Hwy 20 - Montreal to Quebec City", "distance": 250, "baseline_min": 150},
        "RT-008": {"name": "Hwy 1 - Vancouver Downtown", "distance": 30, "baseline_min": 40},
    }

    # Peak hour patterns (congestion multiplier by hour)
    PEAK_PATTERNS = {
        "urban": {
            7: 1.8, 8: 2.2, 9: 1.6,  # Morning peak
            16: 1.7, 17: 2.0, 18: 1.8,  # Evening peak
        },
        "highway": {
            7: 1.3, 8: 1.5, 9: 1.2,
            16: 1.4, 17: 1.6, 18: 1.4,
            12: 1.1, 13: 1.1,  # Lunch slight bump
        },
        "freight": {
            6: 1.2, 10: 1.3, 14: 1.2, 22: 1.1,  # Freight moves off-peak
        },
    }

    ROUTE_TYPES = {
        "RT-001": "highway",
        "RT-002": "highway",
        "RT-003": "urban",
        "RT-004": "highway",
        "RT-005": "highway",
        "RT-006": "urban",
        "RT-007": "highway",
        "RT-008": "urban",
    }

    # Regional logistics profiles
    LOGISTICS_PROFILES = {
        "ON-Toronto": {"port_base": 0.3, "warehouse_base": 75, "trucking_base": 0.8},
        "BC-Vancouver": {"port_base": 0.4, "warehouse_base": 70, "trucking_base": 0.75},
        "QC-Montreal": {"port_base": 0.25, "warehouse_base": 80, "trucking_base": 0.82},
        "AB-Calgary": {"port_base": 0.1, "warehouse_base": 85, "trucking_base": 0.85},
        "default": {"port_base": 0.2, "warehouse_base": 80, "trucking_base": 0.8},
    }

    def __init__(self):
        pass

    def get_current_traffic(
        self,
        route_id: str,
        timestamp: Optional[datetime] = None
    ) -> TrafficCondition:
        """
        Get current traffic conditions for a route.

        Args:
            route_id: Route identifier
            timestamp: Optional timestamp (defaults to now)

        Returns:
            TrafficCondition with current state
        """
        if timestamp is None:
            timestamp = datetime.now()

        route = self.ROUTES.get(route_id, self.ROUTES["RT-001"])
        route_type = self.ROUTE_TYPES.get(route_id, "highway")
        peaks = self.PEAK_PATTERNS.get(route_type, self.PEAK_PATTERNS["highway"])

        hour = timestamp.hour
        day_of_week = timestamp.weekday()

        # Base congestion
        base_congestion = 0.2

        # Add peak hour effect
        peak_multiplier = peaks.get(hour, 1.0)
        congestion = base_congestion * peak_multiplier

        # Weekend reduction
        if day_of_week >= 5:
            congestion *= 0.6

        # Add randomness
        congestion += random.gauss(0, 0.05)
        congestion = max(0, min(1, congestion))

        # Calculate speeds and times
        free_flow_speed = route["distance"] / (route["baseline_min"] / 60)
        current_speed = free_flow_speed * (1 - congestion * 0.6)  # Max 60% reduction
        travel_time = route["distance"] / current_speed * 60
        delay = travel_time - route["baseline_min"]

        # Random incidents
        incidents = []
        if random.random() < 0.1:
            incidents.append("Minor fender-bender reported")
        if congestion > 0.7 and random.random() < 0.3:
            incidents.append("Heavy congestion causing slowdowns")

        return TrafficCondition(
            route_id=route_id,
            timestamp=timestamp,
            congestion_level=round(congestion, 3),
            average_speed_kmh=round(current_speed, 1),
            travel_time_min=round(travel_time, 1),
            baseline_time_min=route["baseline_min"],
            delay_min=round(max(0, delay), 1),
            incidents=incidents
        )

    def get_traffic_forecast(
        self,
        route_id: str,
        hours_ahead: int = 24
    ) -> TrafficForecast:
        """
        Get traffic forecast for a route.

        Args:
            route_id: Route identifier
            hours_ahead: Hours to forecast

        Returns:
            TrafficForecast with hourly predictions
        """
        route = self.ROUTES.get(route_id, self.ROUTES["RT-001"])
        route_type = self.ROUTE_TYPES.get(route_id, "highway")
        peaks = self.PEAK_PATTERNS.get(route_type, self.PEAK_PATTERNS["highway"])

        now = datetime.now()
        forecasts = []
        peak_hours = []
        best_time = None
        best_congestion = 1.0

        for i in range(hours_ahead):
            forecast_time = now + timedelta(hours=i)
            hour = forecast_time.hour
            day_of_week = forecast_time.weekday()

            # Calculate expected congestion
            base = 0.2
            multiplier = peaks.get(hour, 1.0)
            congestion = base * multiplier

            if day_of_week >= 5:
                congestion *= 0.6

            # Add uncertainty that grows with time
            uncertainty = min(0.15, i * 0.01)
            congestion += random.gauss(0, uncertainty)
            congestion = max(0, min(1, congestion))

            free_flow = route["distance"] / (route["baseline_min"] / 60)
            expected_speed = free_flow * (1 - congestion * 0.6)

            forecasts.append({
                "time": forecast_time.isoformat(),
                "hour": hour,
                "congestion_level": round(congestion, 3),
                "expected_speed_kmh": round(expected_speed, 1),
                "confidence": round(1 - uncertainty, 2)
            })

            if congestion > 0.5:
                peak_hours.append(hour)

            if congestion < best_congestion:
                best_congestion = congestion
                best_time = forecast_time

        return TrafficForecast(
            route_id=route_id,
            forecasts=forecasts,
            peak_hours=list(set(peak_hours)),
            recommended_departure=best_time
        )

    def get_congestion_risk(
        self,
        region: str,
        time_of_day: int,
        day_of_week: int = 0
    ) -> CongestionRisk:
        """
        Get congestion risk for a region at a specific time.

        Args:
            region: Region code
            time_of_day: Hour (0-23)
            day_of_week: Day of week (0=Monday)

        Returns:
            CongestionRisk assessment
        """
        # Find routes in region
        region_routes = {
            "ON-Toronto": ["RT-001", "RT-002", "RT-006"],
            "ON-Ottawa": ["RT-002", "RT-003"],
            "QC-Montreal": ["RT-007"],
            "BC-Vancouver": ["RT-004", "RT-008"],
            "AB-Calgary": ["RT-004", "RT-005"],
            "AB-Edmonton": ["RT-005"],
        }
        routes = region_routes.get(region, ["RT-001"])

        # Calculate average congestion probability
        total_prob = 0
        high_risk = []

        for route_id in routes:
            condition = self.get_current_traffic(
                route_id,
                datetime.now().replace(hour=time_of_day)
            )
            total_prob += condition.congestion_level
            if condition.congestion_level > 0.5:
                high_risk.append(route_id)

        avg_prob = total_prob / len(routes)

        # Weekend adjustment
        if day_of_week >= 5:
            avg_prob *= 0.6

        # Delay factor
        delay_factor = 1 + avg_prob * 1.5

        return CongestionRisk(
            region=region,
            time_of_day=time_of_day,
            day_of_week=day_of_week,
            congestion_probability=round(avg_prob, 3),
            expected_delay_factor=round(delay_factor, 2),
            high_risk_routes=high_risk
        )

    def get_shipping_estimate(
        self,
        origin: str,
        destination: str,
        weight_kg: float = 1000
    ) -> ShippingEstimate:
        """
        Get shipping time and cost estimate.

        Args:
            origin: Origin region
            destination: Destination region
            weight_kg: Shipment weight

        Returns:
            ShippingEstimate with time and cost
        """
        # Distance matrix (simplified)
        distances = {
            ("ON-Toronto", "ON-Ottawa"): 450,
            ("ON-Toronto", "QC-Montreal"): 540,
            ("ON-Toronto", "BC-Vancouver"): 4400,
            ("ON-Toronto", "AB-Calgary"): 3400,
            ("AB-Calgary", "AB-Edmonton"): 300,
            ("AB-Calgary", "BC-Vancouver"): 1050,
            ("QC-Montreal", "NS-Halifax"): 1250,
        }

        # Try both directions
        key = (origin, destination)
        reverse_key = (destination, origin)
        distance = distances.get(key, distances.get(reverse_key, 1000))

        # Baseline: 80 km/h average for trucking
        baseline_hours = distance / 80

        # Current conditions
        logistics_origin = self.LOGISTICS_PROFILES.get(origin, self.LOGISTICS_PROFILES["default"])
        logistics_dest = self.LOGISTICS_PROFILES.get(destination, self.LOGISTICS_PROFILES["default"])

        delay_factor = 1.0
        delay_factor += logistics_origin["port_base"] * 0.2
        delay_factor += (1 - logistics_dest["trucking_base"]) * 0.3
        delay_factor += random.gauss(0, 0.05)

        current_hours = baseline_hours * delay_factor

        # Cost estimate: ~$2/km base + weight factor
        cost_per_km = 2.0 + (weight_kg / 10000)
        cost = distance * cost_per_km

        # Availability based on trucking capacity
        avg_trucking = (logistics_origin["trucking_base"] + logistics_dest["trucking_base"]) / 2
        if avg_trucking > 0.8:
            availability = "High"
        elif avg_trucking > 0.6:
            availability = "Medium"
        else:
            availability = "Low"

        return ShippingEstimate(
            origin=origin,
            destination=destination,
            distance_km=distance,
            baseline_hours=round(baseline_hours, 1),
            current_estimate_hours=round(current_hours, 1),
            delay_factor=round(delay_factor, 2),
            cost_estimate_cad=round(cost, 2),
            carrier_availability=availability
        )

    def get_logistics_status(self, region: str) -> LogisticsStatus:
        """
        Get overall logistics status for a region.

        Args:
            region: Region code

        Returns:
            LogisticsStatus with supply chain health
        """
        profile = self.LOGISTICS_PROFILES.get(region, self.LOGISTICS_PROFILES["default"])

        # Add daily variance
        port_congestion = profile["port_base"] + random.gauss(0, 0.1)
        port_congestion = max(0, min(1, port_congestion))

        warehouse_pct = profile["warehouse_base"] + random.gauss(0, 5)
        warehouse_pct = max(50, min(100, warehouse_pct))

        trucking = profile["trucking_base"] + random.gauss(0, 0.05)
        trucking = max(0.5, min(1, trucking))

        # Rail status
        rail_random = random.random()
        if rail_random > 0.95:
            rail = "Disrupted"
        elif rail_random > 0.8:
            rail = "Delayed"
        else:
            rail = "Normal"

        # Overall status
        issues = 0
        if port_congestion > 0.5:
            issues += 1
        if warehouse_pct > 90:
            issues += 1
        if trucking < 0.7:
            issues += 1
        if rail != "Normal":
            issues += 1

        if issues >= 3:
            overall = "Red"
        elif issues >= 1:
            overall = "Yellow"
        else:
            overall = "Green"

        return LogisticsStatus(
            region=region,
            timestamp=datetime.now(),
            port_congestion=round(port_congestion, 3),
            warehouse_capacity_pct=round(warehouse_pct, 1),
            trucking_availability=round(trucking, 3),
            rail_status=rail,
            overall_status=overall
        )


# Singleton instance
_traffic_service = None

def get_traffic_service() -> TrafficService:
    """Get the singleton traffic service instance."""
    global _traffic_service
    if _traffic_service is None:
        _traffic_service = TrafficService()
    return _traffic_service
