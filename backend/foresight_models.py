import enum
from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Date,
    DateTime,
    ForeignKey,
    JSON,
    Numeric,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# Reference tables


class Region(Base):
    __tablename__ = "regions"
    region_code = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    parent_code = Column(String, nullable=True)


class Source(Base):
    __tablename__ = "sources"
    source_id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    doc_url = Column(String, nullable=True)
    retrieved_at = Column(DateTime, default=datetime.utcnow)


class IngestJob(Base):
    __tablename__ = "ingest_jobs"
    job_id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(String, ForeignKey("sources.source_id"), nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="pending")
    rows_written = Column(Integer, default=0)
    error_log = Column(Text, nullable=True)

    source = relationship("Source")


# Core asset domain


class AssetType(str, enum.Enum):
    BRIDGE = "Bridge"
    HIGHWAY = "Highway Segment"
    WATER = "Water Main"
    BUILDING = "Public Building"
    HOSPITAL = "Hospital"
    OTHER = "Other"


class Asset(Base):
    __tablename__ = "assets"

    asset_id = Column(String, primary_key=True)  # e.g., "AST-1001"
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # store enum value
    region = Column(
        String, ForeignKey("regions.region_code"), nullable=True, index=True
    )
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    owner = Column(String, nullable=True)
    design_life = Column(Integer, nullable=True)
    install_date = Column(Date, nullable=True)
    tags = Column(JSON, nullable=True)
    # Convenience baseline attributes for planning
    daily_usage = Column(Integer, nullable=True)
    population_growth_rate = Column(Float, nullable=True)
    replacement_cost = Column(Float, nullable=True)

    capacities = relationship(
        "Capacity", back_populates="asset", cascade="all, delete-orphan"
    )
    metrics = relationship(
        "MetricTS", back_populates="asset", cascade="all, delete-orphan"
    )
    incidents = relationship(
        "Incident", back_populates="asset", cascade="all, delete-orphan"
    )
    forecasts = relationship(
        "Forecast", back_populates="asset", cascade="all, delete-orphan"
    )
    allocations = relationship(
        "Allocation", back_populates="asset", cascade="all, delete-orphan"
    )
    condition_scores = relationship(
        "ConditionScore", back_populates="asset", cascade="all, delete-orphan"
    )


class Capacity(Base):
    __tablename__ = "capacities"
    __table_args__ = (
        Index(
            "idx_cap_asset_effective", "asset_id", "effective_start", "effective_end"
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(String, ForeignKey("assets.asset_id"), nullable=False)
    capacity_type = Column(String, nullable=False)  # beds, vehicles/day, etc.
    capacity_value = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    effective_start = Column(Date, nullable=False)
    effective_end = Column(Date, nullable=True)
    source_id = Column(String, ForeignKey("sources.source_id"), nullable=True)
    version = Column(String, nullable=True)

    asset = relationship("Asset", back_populates="capacities")
    source = relationship("Source")


class MetricTS(Base):
    __tablename__ = "metrics_ts"
    __table_args__ = (
        Index("idx_metrics_asset_type_ts", "asset_id", "metric_type", "ts"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(String, ForeignKey("assets.asset_id"), nullable=False)
    ts = Column(DateTime, nullable=False, default=datetime.utcnow)
    metric_type = Column(String, nullable=False)  # utilization, traffic_count, etc.
    value = Column(Float, nullable=False)
    unit = Column(String, nullable=True)
    source_id = Column(String, ForeignKey("sources.source_id"), nullable=True)
    ingest_job_id = Column(Integer, ForeignKey("ingest_jobs.job_id"), nullable=True)

    asset = relationship("Asset", back_populates="metrics")
    source = relationship("Source")
    ingest_job = relationship("IngestJob")


class ConditionScore(Base):
    __tablename__ = "condition_scores"
    __table_args__ = (Index("idx_condition_asset_date", "asset_id", "observed_date"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(String, ForeignKey("assets.asset_id"), nullable=False)
    observed_date = Column(Date, nullable=False)
    condition_score = Column(Float, nullable=False)
    inspector = Column(String, nullable=True)
    method = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    asset = relationship("Asset", back_populates="condition_scores")


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (Index("idx_incident_asset_start", "asset_id", "start_ts"),)

    incident_id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(String, ForeignKey("assets.asset_id"), nullable=False)
    start_ts = Column(DateTime, nullable=False)
    end_ts = Column(DateTime, nullable=True)
    severity = Column(String, nullable=True)
    incident_type = Column(String, nullable=False)  # weather, outage, maintenance
    impact_desc = Column(Text, nullable=True)
    capacity_delta_pct = Column(Float, nullable=True)
    source_id = Column(String, ForeignKey("sources.source_id"), nullable=True)

    asset = relationship("Asset", back_populates="incidents")
    source = relationship("Source")


# Supply chain topology


class SupplyNode(Base):
    __tablename__ = "supply_nodes"
    node_id = Column(String, primary_key=True)  # e.g., WH-Main
    type = Column(String, nullable=False)
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    status = Column(String, nullable=True)

    outgoing_routes = relationship(
        "SupplyRoute", foreign_keys="SupplyRoute.source_id", back_populates="source"
    )
    incoming_routes = relationship(
        "SupplyRoute", foreign_keys="SupplyRoute.target_id", back_populates="target"
    )


class SupplyRoute(Base):
    __tablename__ = "supply_routes"
    route_id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(String, ForeignKey("supply_nodes.node_id"), nullable=False)
    target_id = Column(String, ForeignKey("supply_nodes.node_id"), nullable=False)
    distance_km = Column(Float, nullable=True)
    base_time_min = Column(Float, nullable=True)

    source = relationship(
        "SupplyNode", foreign_keys=[source_id], back_populates="outgoing_routes"
    )
    target = relationship(
        "SupplyNode", foreign_keys=[target_id], back_populates="incoming_routes"
    )


# Scenarios, forecasts, allocations


class Scenario(Base):
    __tablename__ = "scenarios"
    scenario_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    run_type = Column(String, nullable=False)  # CapitalPlan / EmergencySim
    event_type = Column(String, nullable=True)
    params = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, nullable=True)
    status = Column(String, default="completed")

    forecasts = relationship(
        "Forecast", back_populates="scenario", cascade="all, delete-orphan"
    )
    allocations = relationship(
        "Allocation", back_populates="scenario", cascade="all, delete-orphan"
    )
    runs = relationship(
        "SimulationRun", back_populates="scenario", cascade="all, delete-orphan"
    )


class Forecast(Base):
    __tablename__ = "forecasts"
    __table_args__ = (
        Index(
            "idx_forecast_scenario_asset_horizon",
            "scenario_id",
            "asset_id",
            "horizon_ts",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.scenario_id"), nullable=False)
    asset_id = Column(String, ForeignKey("assets.asset_id"), nullable=False)
    horizon_ts = Column(DateTime, nullable=False)
    metric_type = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String, nullable=True)
    model_version = Column(String, nullable=True)
    source_id = Column(String, ForeignKey("sources.source_id"), nullable=True)

    scenario = relationship("Scenario", back_populates="forecasts")
    asset = relationship("Asset", back_populates="forecasts")
    source = relationship("Source")


class Allocation(Base):
    __tablename__ = "allocations"
    __table_args__ = (
        Index("idx_allocation_scenario_asset", "scenario_id", "asset_id"),
    )

    allocation_id = Column(Integer, primary_key=True, autoincrement=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.scenario_id"), nullable=False)
    asset_id = Column(String, ForeignKey("assets.asset_id"), nullable=False)
    budget_assigned = Column(Float, nullable=False)
    rationale = Column(Text, nullable=True)
    constraints = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    scenario = relationship("Scenario", back_populates="allocations")
    asset = relationship("Asset", back_populates="allocations")


class SimulationRun(Base):
    __tablename__ = "simulation_runs"
    run_id = Column(Integer, primary_key=True, autoincrement=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.scenario_id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    inputs = Column(JSON, nullable=True)
    results = Column(JSON, nullable=True)  # Snapshot for auditability

    scenario = relationship("Scenario", back_populates="runs")


# === MULTI-RESOURCE SCHEMA ===
# Supports allocation of people, money, and tools/equipment


class ResourceType(str, enum.Enum):
    """Types of resources that can be allocated."""
    MONEY = "money"           # Budget/funding
    PERSONNEL = "personnel"   # Staff, workers, contractors
    EQUIPMENT = "equipment"   # Tools, machinery, vehicles


class ResourcePool(Base):
    """
    Available resource pools (budgets, staff pools, equipment inventories).
    Represents the total resources available for allocation.
    """
    __tablename__ = "resource_pools"
    __table_args__ = (
        UniqueConstraint("pool_id", "effective_start", name="uq_pool_effective"),
        Index("idx_pool_type_region", "resource_type", "region"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    pool_id = Column(String, nullable=False)  # e.g., "BUDGET-2024-Q1", "STAFF-ENGINEERS"
    name = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)  # money, personnel, equipment
    total_quantity = Column(Float, nullable=False)
    available_quantity = Column(Float, nullable=False)  # What's currently unallocated
    unit = Column(String, nullable=False)  # "CAD", "FTE", "units"
    region = Column(String, ForeignKey("regions.region_code"), nullable=True)
    effective_start = Column(Date, nullable=False)
    effective_end = Column(Date, nullable=True)
    pool_metadata = Column(JSON, nullable=True)  # Additional attributes (skill_types, equipment_specs)
    created_at = Column(DateTime, default=datetime.utcnow)


class ResourceRequirement(Base):
    """
    Resource requirements for assets/projects.
    Defines what resources are needed for maintenance, repairs, or operations.
    """
    __tablename__ = "resource_requirements"
    __table_args__ = (
        Index("idx_req_asset_type", "asset_id", "resource_type"),
        Index("idx_req_priority", "priority_level"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    requirement_id = Column(String, nullable=False, unique=True)  # e.g., "REQ-AST1001-REPAIR"
    asset_id = Column(String, ForeignKey("assets.asset_id"), nullable=False)
    resource_type = Column(String, nullable=False)  # money, personnel, equipment
    quantity_needed = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    priority_level = Column(Integer, default=3)  # 1=critical, 2=high, 3=medium, 4=low
    skill_requirements = Column(JSON, nullable=True)  # For personnel: ["civil_engineer", "welder"]
    equipment_specs = Column(JSON, nullable=True)  # For equipment: {"type": "crane", "capacity": 50}
    earliest_start = Column(Date, nullable=True)
    latest_finish = Column(Date, nullable=True)
    duration_days = Column(Integer, nullable=True)
    dependencies = Column(JSON, nullable=True)  # List of requirement_ids that must complete first
    created_at = Column(DateTime, default=datetime.utcnow)

    asset = relationship("Asset")


class ResourceAllocation(Base):
    """
    Actual allocations of resources to requirements.
    Tracks what resources have been assigned to which projects.
    """
    __tablename__ = "resource_allocations"
    __table_args__ = (
        Index("idx_alloc_scenario_req", "scenario_id", "requirement_id"),
        Index("idx_alloc_pool", "pool_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    allocation_id = Column(String, nullable=False, unique=True)  # e.g., "ALLOC-2024-001"
    scenario_id = Column(Integer, ForeignKey("scenarios.scenario_id"), nullable=False)
    requirement_id = Column(String, ForeignKey("resource_requirements.requirement_id"), nullable=False)
    pool_id = Column(String, nullable=False)  # Reference to resource pool
    resource_type = Column(String, nullable=False)
    quantity_allocated = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    allocation_status = Column(String, default="proposed")  # proposed, confirmed, in_progress, completed
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    utilization_pct = Column(Float, nullable=True)  # How efficiently the resource is used
    cost_estimate = Column(Float, nullable=True)  # For non-money resources, estimated cost
    rationale = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    scenario = relationship("Scenario")
    requirement = relationship("ResourceRequirement")


class ResourceConstraint(Base):
    """
    Constraints on resource allocation (skill matching, availability windows, etc.).
    """
    __tablename__ = "resource_constraints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    constraint_id = Column(String, nullable=False, unique=True)
    constraint_type = Column(String, nullable=False)  # skill_match, availability, max_concurrent, etc.
    resource_type = Column(String, nullable=True)  # Which resource type this applies to
    pool_id = Column(String, nullable=True)  # Specific pool this applies to
    region = Column(String, ForeignKey("regions.region_code"), nullable=True)
    parameters = Column(JSON, nullable=False)  # Constraint-specific parameters
    is_hard = Column(Integer, default=1)  # 1=hard constraint (must satisfy), 0=soft (penalized)
    penalty_weight = Column(Float, default=1.0)  # Weight for soft constraint violation
    effective_start = Column(Date, nullable=True)
    effective_end = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
