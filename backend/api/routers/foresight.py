"""
Foresight router - Capital planning and emergency simulation endpoints.
"""

import logging
from fastapi import APIRouter, HTTPException

from api.schemas import CapitalPlanRequest, EmergencySimRequest
from foresight import run_capital_planning, simulate_emergency_response

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/foresight/capital-plan")
async def get_capital_plan(req: CapitalPlanRequest):
    """
    Run capital planning optimization based on budget and priorities.
    """
    try:
        return run_capital_planning(req.budget, req.priorities)
    except Exception as e:
        logger.exception("Capital planning error occurred")
        raise HTTPException(
            status_code=500,
            detail="An error occurred during capital planning. Please try again."
        )


@router.post("/foresight/emergency-sim")
async def get_emergency_sim(req: EmergencySimRequest):
    """
    Simulate emergency response for the specified event type.
    """
    try:
        return simulate_emergency_response(req.event_type)
    except Exception as e:
        logger.exception("Emergency simulation error occurred")
        raise HTTPException(
            status_code=500,
            detail="An error occurred during emergency simulation. Please try again."
        )
