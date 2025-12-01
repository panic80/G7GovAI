"""
GovAI Configuration Module

Centralized configuration values for the application.
"""

from .thresholds import (
    SALARY_THRESHOLDS,
    CAPACITY_THRESHOLDS,
    get_salary_thresholds_prompt,
)

__all__ = [
    "SALARY_THRESHOLDS",
    "CAPACITY_THRESHOLDS",
    "get_salary_thresholds_prompt",
]
