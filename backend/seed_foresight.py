"""
Dev seeding script for ForesightOps structured DB.
Creates tables and populates with sample data from existing mock generators.
"""

import datetime
from typing import List

from sqlalchemy.exc import IntegrityError

from sql_db import engine, get_session_factory
from foresight_models import (
    Base,
    Asset,
    Capacity,
    MetricTS,
    ConditionScore,
    Incident,
    SupplyNode,
    SupplyRoute,
    Source,
    Region,
    ResourcePool,
    ResourceRequirement,
    ResourceConstraint,
)
from foresight import generate_infrastructure_data, generate_supply_chain_data


def seed_assets(session) -> None:
    if session.query(Asset).count() > 0:
        return

    assets = generate_infrastructure_data(20)
    today = datetime.date.today()

    for a in assets:
        asset = Asset(
            asset_id=a["id"],
            name=a["name"],
            type=a["type"],
            region=a["region"],
            lat=None,
            lon=None,
            owner=None,
            design_life=None,
            install_date=None,
            tags=None,
            daily_usage=a.get("daily_usage"),
            population_growth_rate=a.get("population_growth_rate"),
            replacement_cost=a.get("replacement_cost"),
        )
        session.add(asset)

        # Add sample capacity (use replacement_cost as proxy for capacity placeholder)
        cap = Capacity(
            asset_id=a["id"],
            capacity_type="throughput",
            capacity_value=max(1, a.get("daily_usage", 1)),
            unit="units/day",
            effective_start=today,
            effective_end=None,
            source_id=None,
            version="seed-1",
        )
        session.add(cap)

        # Add sample metric/condition
        session.add(
            MetricTS(
                asset_id=a["id"],
                ts=datetime.datetime.utcnow(),
                metric_type="utilization",
                value=min(
                    1.0, a.get("daily_usage", 0) / max(1, a.get("daily_usage", 1))
                ),
                unit="ratio",
                source_id=None,
            )
        )
        session.add(
            ConditionScore(
                asset_id=a["id"],
                observed_date=today,
                condition_score=a.get("condition_score", 50),
                inspector="seed",
                method="mock",
            )
        )


def seed_supply_chain(session) -> None:
    if session.query(SupplyNode).count() > 0:
        return

    data = generate_supply_chain_data()
    for node in data["nodes"]:
        session.add(
            SupplyNode(
                node_id=node["id"],
                type=node["type"],
                lat=node.get("lat"),
                lon=node.get("lng"),
                status=node.get("status"),
            )
        )
    for route in data["routes"]:
        session.add(
            SupplyRoute(
                source_id=route["source"],
                target_id=route["target"],
                distance_km=route.get("distance_km"),
                base_time_min=route.get("base_time_min"),
            )
        )


def seed_regions(session) -> None:
    """Seed Canadian regions for demo."""
    if session.query(Region).count() > 0:
        return

    regions = [
        # Provinces
        {"region_code": "ON", "name": "Ontario", "parent_code": None},
        {"region_code": "QC", "name": "Quebec", "parent_code": None},
        {"region_code": "BC", "name": "British Columbia", "parent_code": None},
        {"region_code": "AB", "name": "Alberta", "parent_code": None},
        # Planning regions (map to mock data)
        {"region_code": "North", "name": "North Region", "parent_code": "ON"},
        {"region_code": "East", "name": "East Region", "parent_code": "ON"},
        {"region_code": "West", "name": "West Region", "parent_code": "ON"},
        {"region_code": "Central", "name": "Central Region", "parent_code": "ON"},
    ]

    for r in regions:
        session.add(Region(**r))


def seed_resource_pools(session) -> None:
    """Seed demo resource pools (money, personnel, equipment)."""
    if session.query(ResourcePool).count() > 0:
        return

    today = datetime.date.today()
    fiscal_year_end = datetime.date(today.year + 1, 3, 31)

    pools = [
        # === MONEY POOLS ===
        {
            "pool_id": "BUDGET-FY2025-CAPITAL",
            "name": "FY2025 Capital Budget",
            "resource_type": "money",
            "total_quantity": 50_000_000,
            "available_quantity": 45_000_000,
            "unit": "CAD",
            "region": None,  # Province-wide
            "effective_start": today,
            "effective_end": fiscal_year_end,
            "pool_metadata": {"source": "Treasury Board", "approval_date": str(today)},
        },
        {
            "pool_id": "BUDGET-FY2025-MAINTENANCE",
            "name": "FY2025 Maintenance Budget",
            "resource_type": "money",
            "total_quantity": 15_000_000,
            "available_quantity": 12_000_000,
            "unit": "CAD",
            "region": None,
            "effective_start": today,
            "effective_end": fiscal_year_end,
            "pool_metadata": {"source": "Operating Fund"},
        },
        {
            "pool_id": "BUDGET-EMERGENCY-RESERVE",
            "name": "Emergency Reserve Fund",
            "resource_type": "money",
            "total_quantity": 10_000_000,
            "available_quantity": 10_000_000,
            "unit": "CAD",
            "region": None,
            "effective_start": today,
            "effective_end": None,
            "pool_metadata": {"source": "Contingency", "restricted": True},
        },

        # === PERSONNEL POOLS ===
        {
            "pool_id": "STAFF-CIVIL-ENG",
            "name": "Civil Engineering Staff",
            "resource_type": "personnel",
            "total_quantity": 25.0,
            "available_quantity": 18.5,
            "unit": "FTE",
            "region": None,
            "effective_start": today,
            "effective_end": None,
            "pool_metadata": {
                "skills": ["civil_engineering", "project_management", "inspection"],
                "certifications": ["PEng", "PMP"],
            },
        },
        {
            "pool_id": "STAFF-TRADES",
            "name": "Skilled Trades Workers",
            "resource_type": "personnel",
            "total_quantity": 50.0,
            "available_quantity": 35.0,
            "unit": "FTE",
            "region": None,
            "effective_start": today,
            "effective_end": None,
            "pool_metadata": {
                "skills": ["welding", "electrical", "plumbing", "concrete", "heavy_equipment"],
                "union": "LIUNA Local 183",
            },
        },
        {
            "pool_id": "STAFF-INSPECTORS",
            "name": "Infrastructure Inspectors",
            "resource_type": "personnel",
            "total_quantity": 12.0,
            "available_quantity": 8.0,
            "unit": "FTE",
            "region": None,
            "effective_start": today,
            "effective_end": None,
            "pool_metadata": {
                "skills": ["bridge_inspection", "structural_assessment", "NDT"],
                "certifications": ["OSIM", "BIRM"],
            },
        },
        {
            "pool_id": "CONTRACTOR-GENERAL",
            "name": "Pre-Qualified General Contractors",
            "resource_type": "personnel",
            "total_quantity": 100.0,  # Equivalent FTE capacity
            "available_quantity": 75.0,
            "unit": "FTE",
            "region": None,
            "effective_start": today,
            "effective_end": None,
            "pool_metadata": {
                "type": "external",
                "skills": ["general_construction", "civil_works"],
                "rate_per_fte": 95000,  # Annual equivalent
            },
        },

        # === EQUIPMENT POOLS ===
        {
            "pool_id": "EQUIP-HEAVY-MACHINERY",
            "name": "Heavy Machinery Fleet",
            "resource_type": "equipment",
            "total_quantity": 30,
            "available_quantity": 22,
            "unit": "units",
            "region": None,
            "effective_start": today,
            "effective_end": None,
            "pool_metadata": {
                "equipment_type": "heavy_machinery",
                "includes": ["excavator", "bulldozer", "crane", "grader", "loader"],
                "rental_rate_per_day": 1500,
            },
        },
        {
            "pool_id": "EQUIP-VEHICLES",
            "name": "Service Vehicles",
            "resource_type": "equipment",
            "total_quantity": 75,
            "available_quantity": 60,
            "unit": "units",
            "region": None,
            "effective_start": today,
            "effective_end": None,
            "pool_metadata": {
                "equipment_type": "vehicles",
                "includes": ["pickup_truck", "dump_truck", "service_van"],
                "rental_rate_per_day": 200,
            },
        },
        {
            "pool_id": "EQUIP-INSPECTION",
            "name": "Inspection Equipment",
            "resource_type": "equipment",
            "total_quantity": 15,
            "available_quantity": 12,
            "unit": "units",
            "region": None,
            "effective_start": today,
            "effective_end": None,
            "pool_metadata": {
                "equipment_type": "inspection",
                "includes": ["drone", "GPR", "ultrasonic_tester", "thermal_camera"],
                "rental_rate_per_day": 500,
            },
        },
        {
            "pool_id": "EQUIP-EMERGENCY",
            "name": "Emergency Response Equipment",
            "resource_type": "equipment",
            "total_quantity": 20,
            "available_quantity": 20,
            "unit": "units",
            "region": None,
            "effective_start": today,
            "effective_end": None,
            "pool_metadata": {
                "equipment_type": "emergency",
                "includes": ["pump", "generator", "barrier", "lighting"],
                "restricted": True,
            },
        },
    ]

    for pool in pools:
        session.add(ResourcePool(**pool))


def seed_resource_requirements(session) -> None:
    """Seed demo resource requirements for existing assets."""
    if session.query(ResourceRequirement).count() > 0:
        return

    # Get existing assets
    assets = session.query(Asset).all()
    if not assets:
        return

    today = datetime.date.today()
    requirements = []

    for i, asset in enumerate(assets):
        condition = asset.replacement_cost or 1_000_000
        base_cost = condition * 0.15  # 15% of replacement cost for maintenance

        # Assign priority based on condition (fetched earlier via seed_assets)
        priority = 3  # default medium
        if i < 5:
            priority = 1  # Critical
        elif i < 10:
            priority = 2  # High

        # Money requirement
        requirements.append({
            "requirement_id": f"REQ-{asset.asset_id}-MONEY",
            "asset_id": asset.asset_id,
            "resource_type": "money",
            "quantity_needed": round(base_cost, 2),
            "unit": "CAD",
            "priority_level": priority,
            "skill_requirements": None,
            "equipment_specs": None,
            "earliest_start": today,
            "latest_finish": datetime.date(today.year + 1, 3, 31),
            "duration_days": 90,
            "dependencies": None,
        })

        # Personnel requirement (based on asset type)
        if asset.type == "Bridge":
            fte_needed = 4.5
            skills = ["civil_engineering", "bridge_inspection", "welding"]
        elif asset.type == "Highway Segment":
            fte_needed = 6.0
            skills = ["civil_engineering", "heavy_equipment", "concrete"]
        elif asset.type == "Water Main":
            fte_needed = 3.0
            skills = ["plumbing", "excavation"]
        else:  # Public Building
            fte_needed = 2.0
            skills = ["general_construction", "electrical"]

        requirements.append({
            "requirement_id": f"REQ-{asset.asset_id}-STAFF",
            "asset_id": asset.asset_id,
            "resource_type": "personnel",
            "quantity_needed": fte_needed,
            "unit": "FTE",
            "priority_level": priority,
            "skill_requirements": skills,
            "equipment_specs": None,
            "earliest_start": today,
            "latest_finish": datetime.date(today.year + 1, 3, 31),
            "duration_days": 60,
            "dependencies": [f"REQ-{asset.asset_id}-MONEY"],  # Funding first
        })

        # Equipment requirement
        if asset.type in ["Bridge", "Highway Segment"]:
            equip_count = 3
            equip_type = "heavy_machinery"
        else:
            equip_count = 1
            equip_type = "vehicles"

        requirements.append({
            "requirement_id": f"REQ-{asset.asset_id}-EQUIP",
            "asset_id": asset.asset_id,
            "resource_type": "equipment",
            "quantity_needed": equip_count,
            "unit": "units",
            "priority_level": priority,
            "skill_requirements": None,
            "equipment_specs": {"type": equip_type},
            "earliest_start": today,
            "latest_finish": datetime.date(today.year + 1, 3, 31),
            "duration_days": 45,
            "dependencies": [f"REQ-{asset.asset_id}-STAFF"],  # Staff assigned first
        })

    for req in requirements:
        session.add(ResourceRequirement(**req))


def seed_resource_constraints(session) -> None:
    """Seed demo resource constraints."""
    if session.query(ResourceConstraint).count() > 0:
        return

    constraints = [
        {
            "constraint_id": "CONST-BUDGET-CAP",
            "constraint_type": "budget_cap",
            "resource_type": "money",
            "pool_id": None,
            "region": None,
            "parameters": {
                "max_per_project": 15_000_000,
                "max_per_region": 20_000_000,
            },
            "is_hard": 1,
            "penalty_weight": 1.0,
        },
        {
            "constraint_id": "CONST-SKILL-MATCH",
            "constraint_type": "skill_match",
            "resource_type": "personnel",
            "pool_id": None,
            "region": None,
            "parameters": {
                "required_match_pct": 0.8,  # 80% of skills must match
            },
            "is_hard": 0,  # Soft constraint
            "penalty_weight": 2.0,
        },
        {
            "constraint_id": "CONST-EQUIP-AVAIL",
            "constraint_type": "availability_window",
            "resource_type": "equipment",
            "pool_id": "EQUIP-HEAVY-MACHINERY",
            "region": None,
            "parameters": {
                "max_concurrent_usage_pct": 0.7,  # Keep 30% reserve
                "maintenance_days_per_month": 3,
            },
            "is_hard": 1,
            "penalty_weight": 1.0,
        },
        {
            "constraint_id": "CONST-REGIONAL-EQUITY",
            "constraint_type": "regional_equity",
            "resource_type": "money",
            "pool_id": None,
            "region": None,
            "parameters": {
                "min_allocation_pct_per_region": 0.15,  # At least 15% per region
            },
            "is_hard": 0,
            "penalty_weight": 1.5,
        },
        {
            "constraint_id": "CONST-EMERGENCY-RESERVE",
            "constraint_type": "reserve",
            "resource_type": "equipment",
            "pool_id": "EQUIP-EMERGENCY",
            "region": None,
            "parameters": {
                "min_reserve_pct": 0.5,  # Keep 50% for emergencies
                "trigger_events": ["flood", "earthquake", "ice_storm"],
            },
            "is_hard": 1,
            "penalty_weight": 1.0,
        },
    ]

    for const in constraints:
        session.add(ResourceConstraint(**const))


def main():
    # Create tables
    Base.metadata.create_all(bind=engine)
    session_factory = get_session_factory()
    session = session_factory()
    try:
        # Core data
        print("Seeding regions...")
        seed_regions(session)
        session.commit()

        print("Seeding assets...")
        seed_assets(session)
        session.commit()

        print("Seeding supply chain...")
        seed_supply_chain(session)
        session.commit()

        # Multi-resource data
        print("Seeding resource pools (money, personnel, equipment)...")
        seed_resource_pools(session)
        session.commit()

        print("Seeding resource requirements...")
        seed_resource_requirements(session)
        session.commit()

        print("Seeding resource constraints...")
        seed_resource_constraints(session)
        session.commit()

        print("ForesightOps seed complete.")
        print(f"  - Regions: {session.query(Region).count()}")
        print(f"  - Assets: {session.query(Asset).count()}")
        print(f"  - Resource Pools: {session.query(ResourcePool).count()}")
        print(f"  - Requirements: {session.query(ResourceRequirement).count()}")
        print(f"  - Constraints: {session.query(ResourceConstraint).count()}")
    except IntegrityError as e:
        session.rollback()
        print(f"Seed failed due to integrity error: {e}")
    except Exception as e:
        session.rollback()
        print(f"Seed failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()


if __name__ == "__main__":
    main()
