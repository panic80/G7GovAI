"""
AccessBridge LangGraph Workflow

Defines the state graph for multimodal intake assistance.
Pipeline:
1. PROCESS INPUT       → Combine OCR, STT, and text inputs
2. RETRIEVE PROGRAM    → Fetch program requirements from knowledge base
3. EXTRACT INFO        → Extract structured fields using LLM
4. ANALYZE GAPS        → Identify missing info and generate questions
5. PROCESS FOLLOW-UP   → Merge user's answers (optional, user-triggered)
6. GENERATE OUTPUTS    → Create form data, email draft, meeting prep
"""

from langgraph.graph import StateGraph, END
from typing import Literal

from .state import AccessBridgeState
from .nodes import (
    process_input_node,
    retrieve_program_context_node,
    extract_information_node,
    analyze_gaps_node,
    process_follow_up_node,
    generate_outputs_node,
)


# =============================================================================
# Conditional Routing Functions
# =============================================================================

def route_after_gaps(state: AccessBridgeState) -> Literal["generate_outputs", "wait_for_input"]:
    """
    Determine whether to proceed to output generation or wait for user input.

    If there are critical gaps and this is the first pass, wait for user input.
    Otherwise, proceed to generate outputs with available information.
    """
    has_critical_gaps = state.get("has_critical_gaps", False)
    loop_count = state.get("loop_count", 0)

    # If we've already done one follow-up round, proceed regardless
    if loop_count >= 2:
        return "generate_outputs"

    # If there are critical gaps, pause for user input
    if has_critical_gaps:
        return "wait_for_input"

    return "generate_outputs"


def route_after_extract(state: AccessBridgeState) -> Literal["analyze_gaps", "process_follow_up"]:
    """
    Determine whether to process follow-up answers before analyzing gaps.

    If follow_up_answers are provided, merge them first via process_follow_up.
    Otherwise, proceed directly to analyze_gaps.
    """
    follow_up_answers = state.get("follow_up_answers", [])

    if follow_up_answers and len(follow_up_answers) > 0:
        return "process_follow_up"

    return "analyze_gaps"


# =============================================================================
# Build the AccessBridge Workflow Graph
# =============================================================================

workflow = StateGraph(AccessBridgeState)

# Add Nodes
workflow.add_node("process_input", process_input_node)
workflow.add_node("retrieve_program", retrieve_program_context_node)
workflow.add_node("extract_info", extract_information_node)
workflow.add_node("analyze_gaps", analyze_gaps_node)
workflow.add_node("process_follow_up", process_follow_up_node)
workflow.add_node("generate_outputs", generate_outputs_node)

# Define Edges

# Main sequential pipeline
workflow.set_entry_point("process_input")
workflow.add_edge("process_input", "retrieve_program")
workflow.add_edge("retrieve_program", "extract_info")

# After extraction, check if we have follow-up answers to merge
workflow.add_conditional_edges(
    "extract_info",
    route_after_extract,
    {
        "analyze_gaps": "analyze_gaps",
        "process_follow_up": "process_follow_up",
    }
)

# Follow-up processing then goes to analyze_gaps
workflow.add_edge("process_follow_up", "analyze_gaps")

# Conditional routing after gap analysis
# - If critical gaps: END (wait for user to provide follow-up answers)
# - If no critical gaps: proceed to generate outputs
workflow.add_conditional_edges(
    "analyze_gaps",
    route_after_gaps,
    {
        "generate_outputs": "generate_outputs",
        "wait_for_input": END,  # Pause here; user provides follow-up answers
    }
)

# Final output generation
workflow.add_edge("generate_outputs", END)

# Compile the graph
accessbridge_graph = workflow.compile()


# =============================================================================
# Convenience Functions
# =============================================================================

def run_intake(
    raw_text_input: str = "",
    program_type: str = "general",
    language: str = "en",
    follow_up_answers: list = None,
) -> dict:
    """
    Run the AccessBridge intake pipeline synchronously.

    Args:
        raw_text_input: User's raw text input
        program_type: Type of government program
        language: User's preferred language ("en" or "fr")
        follow_up_answers: Pre-supplied answers to gap questions

    Returns:
        Final state with form_data, email_draft, and meeting_prep
    """
    from .state import create_initial_state

    initial_state = create_initial_state(
        raw_text_input=raw_text_input,
        program_type=program_type,
        language=language,
        follow_up_answers=follow_up_answers or [],
    )

    final_state = accessbridge_graph.invoke(initial_state)
    return final_state


async def astream_intake(
    raw_text_input: str = "",
    program_type: str = "general",
    language: str = "en",
    document_texts: list = None,
    audio_transcripts: list = None,
    follow_up_answers: list = None,
):
    """
    Stream the AccessBridge intake pipeline asynchronously.

    Yields state updates as each node completes.

    Args:
        raw_text_input: User's raw text input
        program_type: Type of government program
        language: User's preferred language ("en" or "fr")
        document_texts: Pre-processed OCR results
        audio_transcripts: Pre-processed STT results
        follow_up_answers: Pre-supplied answers to gap questions

    Yields:
        State updates from each node
    """
    from .state import create_initial_state

    initial_state = create_initial_state(
        raw_text_input=raw_text_input,
        program_type=program_type,
        language=language,
        follow_up_answers=follow_up_answers or [],
    )

    # Add pre-processed inputs if provided
    if document_texts:
        initial_state["document_texts"] = document_texts
    if audio_transcripts:
        initial_state["audio_transcripts"] = audio_transcripts

    # Stream the graph execution
    async for event in accessbridge_graph.astream(initial_state):
        yield event
