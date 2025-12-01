"""
Agent Streaming Endpoints

Unified streaming endpoints for all LangGraph agents.
Uses shared streaming infrastructure from agent.core.
"""

from fastapi import APIRouter
import json
import logging

logger = logging.getLogger(__name__)

from api.schemas import (
    AgentSearchRequest,
    GovLensAgentRequest,
    ForesightAgentRequest,
    AccessBridgeRequest,
)
from agent.lexgraph.graph import app_graph
from agent.lexgraph.state import LegalResearchState
from agent.govlens.graph import govlens_graph
from agent.govlens.state import GovLensState
from agent.foresight.graph import foresight_graph
from agent.foresight.state import create_initial_state as create_foresight_state
from agent.accessbridge.graph import accessbridge_graph
from agent.accessbridge.state import create_initial_state as create_accessbridge_state
from agent.core import (
    create_agent_stream,
    LEXGRAPH_NODES,
    GOVLENS_NODES,
    FORESIGHT_NODES,
    ACCESSBRIDGE_NODES,
)

router = APIRouter()


# =============================================================================
# State Factories
# =============================================================================

def create_lexgraph_state(request: AgentSearchRequest) -> LegalResearchState:
    """Create initial state for LexGraph agent."""
    return {
        "query": request.query,
        "language": request.language,
        "effective_date": request.effective_date,
        "generated_queries": [],
        "documents": [],
        "citations_found": [],
        "trace_log": [],
        "loop_count": 0,
        "final_answer": "",
        "eligible": None,
        "decision_trace": None,
        "extracted_rules": None,
        "resolved_rules": None,
        # Legislative source integration
        "legislative_excerpts": None,
        "decision_tree": None,
        "legislation_map": None,
    }


def create_govlens_state(request: GovLensAgentRequest) -> GovLensState:
    """Create initial state for GovLens agent."""
    return {
        "query": request.query,
        "language": request.language,
        "search_strategy": "simple",
        "categories": request.categories,
        "themes": request.themes,
        "generated_queries": [],
        "documents": [],
        "trace_log": [],
        "loop_count": 0,
        "final_answer": "",
        "answer_text": None,
        "citations": None,
        "bullets": None,
        "confidence": None,
        "abstained": None,
    }


# =============================================================================
# Error Handlers
# =============================================================================

def govlens_error_handler(error: Exception, last_state: dict) -> dict:
    """Custom error handler for GovLens that maintains response structure."""
    # Log full error server-side only
    logger.error(f"GovLens agent error: {type(error).__name__}: {error}")
    return {
        "query": last_state.get("query", ""),
        "language": last_state.get("language", "en"),
        "search_strategy": last_state.get("search_strategy", "simple"),
        "generated_queries": last_state.get("generated_queries", []),
        "documents": last_state.get("documents", []),
        "trace_log": last_state.get("trace_log", []) + ["An error occurred during processing"],
        "loop_count": last_state.get("loop_count", 0),
        "final_answer": json.dumps({
            "answer": "An error occurred while processing your request. Please try again.",
            "lang": last_state.get("language", "en"),
            "bullets": [],
            "citations": [],
            "confidence": 0.0,
            "abstained": True,
        }),
    }


def foresight_error_handler(error: Exception, last_state: dict) -> dict:
    """Custom error handler for ForesightOps."""
    # Log full error server-side only
    logger.error(f"ForesightOps agent error: {type(error).__name__}: {error}")
    return {
        "trace_log": ["An error occurred during processing"],
        "recommendations": "An error occurred while processing your request. Please try again.",
        "confidence_score": 0.0,
    }


def accessbridge_error_handler(error: Exception, last_state: dict) -> dict:
    """Custom error handler for AccessBridge."""
    # Log full error server-side only
    logger.error(f"AccessBridge agent error: {type(error).__name__}: {error}")
    return {
        "trace_log": ["An error occurred during processing"],
        "completion_status": "incomplete",
        "overall_confidence": 0.0,
    }


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/agent/lexgraph/stream")
async def stream_lexgraph_agent(request: AgentSearchRequest):
    """Stream LexGraph agent execution for legislative rule evaluation."""
    logger.info("Starting LexGraph agent")
    initial_state = create_lexgraph_state(request)
    return create_agent_stream(app_graph, initial_state, LEXGRAPH_NODES)


@router.post("/agent/govlens/stream")
async def stream_govlens_agent(request: GovLensAgentRequest):
    """Stream GovLens agent execution for semantic Q&A."""
    logger.info("Starting GovLens agent")
    initial_state = create_govlens_state(request)
    return create_agent_stream(
        govlens_graph,
        initial_state,
        GOVLENS_NODES,
        on_error=govlens_error_handler
    )


@router.post("/agent/foresight/stream")
async def stream_foresight_agent(request: ForesightAgentRequest):
    """Stream ForesightOps agent execution for resource allocation."""
    logger.info("Starting ForesightOps agent")
    initial_state = create_foresight_state(
        query=request.query,
        language=request.language,
        budget_total=request.budget_total,
        planning_horizon_years=request.planning_horizon_years,
        weights=request.weights,
        region_filter=request.region_filter,
        asset_type_filter=request.asset_type_filter,
        include_scenarios=request.include_scenarios,
        enforce_equity=request.enforce_equity,
    )
    return create_agent_stream(
        foresight_graph,
        initial_state,
        FORESIGHT_NODES,
        on_error=foresight_error_handler
    )


@router.post("/agent/accessbridge/stream")
async def stream_accessbridge_agent(request: AccessBridgeRequest):
    """Stream AccessBridge agent execution for intake assistance."""
    logger.info(f"Starting AccessBridge agent for program: {request.program_type}")
    initial_state = create_accessbridge_state(
        raw_text_input=request.raw_text_input,
        program_type=request.program_type,
        language=request.language,
        ui_language=request.ui_language,  # UI language for gap questions
        follow_up_answers=request.follow_up_answers or [],
        form_template=request.form_template,  # Pass uploaded form template
        selected_modes=request.selected_modes,  # Pass selected output modes
    )

    # Add pre-processed inputs if provided
    if request.document_texts:
        initial_state["document_texts"] = request.document_texts
    if request.audio_transcripts:
        initial_state["audio_transcripts"] = request.audio_transcripts

    return create_agent_stream(
        accessbridge_graph,
        initial_state,
        ACCESSBRIDGE_NODES,
        on_error=accessbridge_error_handler
    )
