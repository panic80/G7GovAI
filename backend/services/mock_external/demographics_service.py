"""
Mock Demographics Service
=========================
Simulates Statistics Canada population projections for hackathon demo.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional
import random
import math

random.seed(42)


@dataclass
class PopulationProjection:
    """Population projection for a region."""
    region: str
    base_year: int
    projections: List[Dict]  # [{year, population, growth_rate}]
    confidence_interval: float  # +/- percentage


@dataclass
class DemographicTrends:
    """Demographic trends for demand forecasting."""
    region: str
    median_age: float
    population_density: float  # per km²
    urban_pct: float
    age_distribution: Dict[str, float]  # age_group -> percentage
    growth_drivers: List[str]
    infrastructure_demand_index: float  # 0-1, higher = more demand


@dataclass
class PopulationByAge:
    """Age distribution for a region."""
    region: str
    year: int
    age_groups: Dict[str, int]  # age_group -> count


@dataclass
class DemandForecast:
    """Infrastructure demand forecast based on demographics."""
    region: str
    year: int
    hospital_beds_needed: int
    school_capacity_needed: int
    transit_ridership_index: float
    water_demand_ml_day: float
    road_capacity_index: float


class DemographicsService:
    """
    Mock demographics service for demo purposes.

    In production, would integrate with:
    - Statistics Canada Census data
    - Provincial demographic databases
    - Municipal planning data
    """

    # Base population data (2024 estimates, thousands)
    REGIONAL_POPULATIONS = {
        "ON-Toronto": {"pop_2024": 2930, "growth_rate": 1.8, "density": 4334},
        "ON-Ottawa": {"pop_2024": 1017, "growth_rate": 1.5, "density": 365},
        "QC-Montreal": {"pop_2024": 1780, "growth_rate": 1.2, "density": 4662},
        "BC-Vancouver": {"pop_2024": 675, "growth_rate": 2.0, "density": 5493},
        "AB-Calgary": {"pop_2024": 1336, "growth_rate": 2.5, "density": 1672},
        "AB-Edmonton": {"pop_2024": 1010, "growth_rate": 2.2, "density": 1360},
        "SK-Regina": {"pop_2024": 228, "growth_rate": 1.0, "density": 1217},
        "MB-Winnipeg": {"pop_2024": 758, "growth_rate": 1.3, "density": 1519},
        "NS-Halifax": {"pop_2024": 465, "growth_rate": 2.1, "density": 73},
        "NB-Fredericton": {"pop_2024": 64, "growth_rate": 0.8, "density": 441},
        "default": {"pop_2024": 500, "growth_rate": 1.2, "density": 500},
    }

    # Age distribution templates
    AGE_PROFILES = {
        "growing_urban": {
            "0-14": 0.15, "15-24": 0.13, "25-44": 0.32,
            "45-64": 0.24, "65-79": 0.12, "80+": 0.04
        },
        "aging_urban": {
            "0-14": 0.12, "15-24": 0.10, "25-44": 0.26,
            "45-64": 0.28, "65-79": 0.17, "80+": 0.07
        },
        "balanced": {
            "0-14": 0.16, "15-24": 0.12, "25-44": 0.28,
            "45-64": 0.26, "65-79": 0.13, "80+": 0.05
        },
    }

    REGION_AGE_PROFILE = {
        "ON-Toronto": "growing_urban",
        "BC-Vancouver": "growing_urban",
        "AB-Calgary": "growing_urban",
        "AB-Edmonton": "growing_urban",
        "QC-Montreal": "aging_urban",
        "ON-Ottawa": "balanced",
        "NS-Halifax": "growing_urban",
        "default": "balanced",
    }

    def __init__(self):
        pass

    def get_population_projection(
        self,
        region: str,
        years_ahead: int = 10
    ) -> PopulationProjection:
        """
        Get population projection for a region.

        Args:
            region: Region code
            years_ahead: Number of years to project

        Returns:
            PopulationProjection with yearly estimates
        """
        data = self.REGIONAL_POPULATIONS.get(region, self.REGIONAL_POPULATIONS["default"])
        base_pop = data["pop_2024"] * 1000  # Convert to actual population
        growth_rate = data["growth_rate"] / 100  # Convert to decimal

        projections = []
        current_year = 2024

        for i in range(years_ahead + 1):
            year = current_year + i

            # Add some variance to growth rate over time
            yearly_rate = growth_rate * (1 + random.gauss(0, 0.1))

            # Compound growth with slight decay over time (regression to mean)
            decay_factor = 1 - (i * 0.02)  # Growth slows slightly each year
            population = base_pop * math.pow(1 + yearly_rate * decay_factor, i)

            projections.append({
                "year": year,
                "population": int(population),
                "growth_rate": round(yearly_rate * decay_factor * 100, 2)
            })

        return PopulationProjection(
            region=region,
            base_year=current_year,
            projections=projections,
            confidence_interval=2.5 + (years_ahead * 0.5)  # Wider CI for longer projections
        )

    def get_demographic_trends(self, region: str) -> DemographicTrends:
        """
        Get demographic trends for a region.

        Args:
            region: Region code

        Returns:
            DemographicTrends with demand indicators
        """
        data = self.REGIONAL_POPULATIONS.get(region, self.REGIONAL_POPULATIONS["default"])
        profile_name = self.REGION_AGE_PROFILE.get(region, "balanced")
        age_dist = self.AGE_PROFILES[profile_name]

        # Calculate median age based on distribution
        if profile_name == "growing_urban":
            median_age = 35.5 + random.gauss(0, 1)
        elif profile_name == "aging_urban":
            median_age = 42.0 + random.gauss(0, 1)
        else:
            median_age = 38.5 + random.gauss(0, 1)

        # Urban percentage
        urban_pct = 0.9 if data["density"] > 1000 else (0.7 if data["density"] > 300 else 0.5)

        # Growth drivers
        growth_rate = data["growth_rate"]
        drivers = []
        if growth_rate > 2.0:
            drivers.append("Immigration and interprovincial migration")
            drivers.append("Strong job market")
        elif growth_rate > 1.0:
            drivers.append("Natural population growth")
            drivers.append("Economic development")
        else:
            drivers.append("Stable employment base")

        if profile_name == "growing_urban":
            drivers.append("Young professional attraction")

        # Infrastructure demand index (higher = more pressure on infrastructure)
        demand_index = (
            data["growth_rate"] / 3.0 * 0.4 +  # Growth component
            data["density"] / 5000 * 0.3 +      # Density component
            (1 - age_dist["65-79"] - age_dist["80+"]) * 0.3  # Working age component
        )
        demand_index = min(1.0, max(0.0, demand_index))

        return DemographicTrends(
            region=region,
            median_age=round(median_age, 1),
            population_density=data["density"],
            urban_pct=round(urban_pct, 2),
            age_distribution=age_dist,
            growth_drivers=drivers,
            infrastructure_demand_index=round(demand_index, 3)
        )

    def get_population_by_age(
        self,
        region: str,
        year: int = 2024
    ) -> PopulationByAge:
        """
        Get population breakdown by age group.

        Args:
            region: Region code
            year: Target year

        Returns:
            PopulationByAge with counts per group
        """
        projection = self.get_population_projection(region, max(0, year - 2024))

        # Find the right year's population
        pop_data = next(
            (p for p in projection.projections if p["year"] == year),
            projection.projections[-1]
        )
        total_pop = pop_data["population"]

        profile_name = self.REGION_AGE_PROFILE.get(region, "balanced")
        age_dist = self.AGE_PROFILES[profile_name]

        # Adjust age distribution for future years (aging population)
        years_ahead = year - 2024
        adjusted_dist = {}
        for group, pct in age_dist.items():
            if group in ["65-79", "80+"]:
                # Older groups grow slightly faster
                adjusted_dist[group] = pct * (1 + 0.01 * years_ahead)
            elif group in ["0-14", "15-24"]:
                # Younger groups shrink slightly
                adjusted_dist[group] = pct * (1 - 0.005 * years_ahead)
            else:
                adjusted_dist[group] = pct

        # Normalize to sum to 1
        total = sum(adjusted_dist.values())
        adjusted_dist = {k: v/total for k, v in adjusted_dist.items()}

        age_groups = {
            group: int(total_pop * pct)
            for group, pct in adjusted_dist.items()
        }

        return PopulationByAge(
            region=region,
            year=year,
            age_groups=age_groups
        )

    def forecast_infrastructure_demand(
        self,
        region: str,
        year: int
    ) -> DemandForecast:
        """
        Forecast infrastructure demand based on demographics.

        Args:
            region: Region code
            year: Target year

        Returns:
            DemandForecast with service level needs
        """
        pop_by_age = self.get_population_by_age(region, year)
        trends = self.get_demographic_trends(region)
        total_pop = sum(pop_by_age.age_groups.values())

        # Hospital beds: ~2.5 beds per 1000, higher for aging populations
        elderly_pop = pop_by_age.age_groups.get("65-79", 0) + pop_by_age.age_groups.get("80+", 0)
        hospital_beds = int(total_pop * 0.0025 + elderly_pop * 0.01)

        # School capacity: school-age population + buffer
        school_age = pop_by_age.age_groups.get("0-14", 0) * 0.7  # Not all 0-14 are school age
        school_age += pop_by_age.age_groups.get("15-24", 0) * 0.3  # Some 15-24 in school
        school_capacity = int(school_age * 1.1)  # 10% buffer

        # Transit: index based on density and working population
        working_pop = (
            pop_by_age.age_groups.get("25-44", 0) +
            pop_by_age.age_groups.get("45-64", 0) * 0.8
        )
        transit_index = min(1.0, (trends.population_density / 3000) * (working_pop / total_pop) * 2)

        # Water demand: ~250 L/person/day residential, higher for commercial
        water_demand = total_pop * 0.00025 * (1 + trends.urban_pct * 0.3)  # ML/day

        # Road capacity: based on total vehicles expected
        vehicles_per_capita = 0.5 if trends.population_density > 2000 else 0.7
        road_index = min(1.0, (total_pop * vehicles_per_capita / 1000000) * trends.infrastructure_demand_index * 1.5)

        return DemandForecast(
            region=region,
            year=year,
            hospital_beds_needed=hospital_beds,
            school_capacity_needed=school_capacity,
            transit_ridership_index=round(transit_index, 3),
            water_demand_ml_day=round(water_demand, 2),
            road_capacity_index=round(road_index, 3)
        )


# Singleton instance
_demographics_service = None

def get_demographics_service() -> DemographicsService:
    """Get the singleton demographics service instance."""
    global _demographics_service
    if _demographics_service is None:
        _demographics_service = DemographicsService()
    return _demographics_service
