"""
Mock External Data Services
===========================
Simulated external APIs for hackathon demo.
In production, these would integrate with real data sources.
"""

from .weather_service import WeatherService
from .demographics_service import DemographicsService
from .traffic_service import TrafficService

__all__ = ["WeatherService", "DemographicsService", "TrafficService"]
