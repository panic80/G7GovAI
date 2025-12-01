"""
Threshold Configuration

Immigration salary thresholds and capacity planning thresholds.
These values are used by the LexGraph rules engine and ForesightOps planning.
"""

from typing import Dict, Any


# Immigration Salary Thresholds by Country/Category
# These are used in LLM prompts for rule extraction
SALARY_THRESHOLDS: Dict[str, Dict[str, Any]] = {
    "canada_software": {
        "min": 66000,
        "currency": "CAD",
        "description": "Canada software engineer",
    },
    "canada_general": {
        "min": 35000,
        "currency": "CAD",
        "description": "Canada general worker",
    },
    "uk_skilled": {
        "min": 38700,
        "currency": "GBP",
        "description": "UK skilled worker",
    },
    "usa_h1b": {
        "min": 60000,
        "currency": "USD",
        "description": "USA H-1B visa",
    },
}


# Capacity/Utilization Thresholds for ForesightOps
CAPACITY_THRESHOLDS: Dict[str, float] = {
    "warning": 0.75,   # Yellow zone - approaching capacity
    "critical": 0.90,  # Red zone - at/over capacity
}


# Demand Elasticity by Asset Type
DEMAND_ELASTICITY: Dict[str, float] = {
    "Bridge": 1.2,
    "Highway Segment": 1.3,
    "Water Main": 0.9,
    "Public Building": 1.0,
    "Hospital": 1.1,
}


def get_salary_thresholds_prompt() -> str:
    """
    Generate the salary thresholds section for LLM prompts.

    Returns:
        Formatted string for inclusion in extraction prompts.
    """
    lines = ["SALARY THRESHOLDS (use these):"]
    for key, config in SALARY_THRESHOLDS.items():
        lines.append(
            f"- {config['description']}: salary_offer >= {config['min']} {config['currency']}"
        )
    return "\n".join(lines)
