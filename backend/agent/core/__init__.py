"""
Agent Core Module - exports LLM service utilities.
"""

import re
import json
import logging
from typing import Dict, Any, Set, Optional, Callable, List
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

from .llm import get_llm, get_llm_response, LLMService
from core.model_state import model_config


# Node constants for each agent type
LEXGRAPH_NODES = {"retrieve", "extract_rules", "resolve_thresholds", "map_legislation", "extract_facts", "evaluate"}
GOVLENS_NODES = {"retrieve", "generate"}
FORESIGHT_NODES = {"route", "retrieve", "forecast", "analyze", "evaluate", "refine", "synthesize"}
ACCESSBRIDGE_NODES = {"process_input", "retrieve_program", "extract_info", "analyze_gaps", "process_follow_up", "generate_outputs"}


def get_language_instruction(language: str = "en") -> str:
    """Get instruction string for LLM language output."""
    language_map = {
        "en": "Respond in English.",
        "fr": "Respond in French (Français).",
        "de": "Respond in German (Deutsch).",
        "it": "Respond in Italian (Italiano).",
        "ja": "Respond in Japanese (日本語).",
    }
    return language_map.get(language, "Respond in English.")


def clean_json_response(response: str) -> str:
    """
    Clean LLM response to extract valid JSON.
    Removes markdown code blocks and other formatting.
    """
    import re

    if not response:
        return "{}"

    # Remove markdown code blocks
    cleaned = re.sub(r'```(?:json)?\s*', '', response)
    cleaned = re.sub(r'```', '', cleaned)
    cleaned = cleaned.strip()

    # Try to find JSON object
    json_match = re.search(r'\{[\s\S]*\}', cleaned)
    if json_match:
        return json_match.group(0)

    return cleaned


def parse_govlens_response(raw_json: str, language: str = "en") -> Dict[str, Any]:
    """
    Parse and validate GovLens LLM response JSON.
    Handles common JSON parsing issues and provides fallback structure.
    """
    fallback = {
        "answer": "Unable to parse response" if language == "en" else "Impossible d'analyser la réponse",
        "abstained": True,
        "citations": [],
        "bullets": []
    }

    if not raw_json or not raw_json.strip():
        return fallback

    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError:
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', raw_json)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
            except json.JSONDecodeError:
                return fallback
        else:
            json_match = re.search(r'\{[\s\S]*\}', raw_json)
            if json_match:
                try:
                    data = json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    return fallback
            else:
                return fallback

    # Ensure required fields exist
    if "answer" not in data:
        data["answer"] = raw_json[:500] if len(raw_json) > 500 else raw_json
    if "abstained" not in data:
        data["abstained"] = False
    if "citations" not in data:
        data["citations"] = []
    if "bullets" not in data:
        data["bullets"] = []

    # Deduplicate citations
    seen_citations = set()
    unique_citations = []
    for citation in data.get("citations", []):
        citation_key = str(citation) if isinstance(citation, dict) else citation
        if citation_key not in seen_citations:
            seen_citations.add(citation_key)
            unique_citations.append(citation)
    data["citations"] = unique_citations

    return data


def create_agent_stream(
    graph: Any,
    initial_state: Dict[str, Any],
    node_names: Set[str],
    on_error: Optional[Callable[[Exception], Dict[str, Any]]] = None
) -> StreamingResponse:
    """Create a streaming response for LangGraph agent execution."""

    async def event_generator():
        # Check if API key is configured
        if not model_config.is_configured():
            language = initial_state.get("language", "en")
            if language == "fr":
                message = "Veuillez configurer votre clé API Gemini dans la page Gouvernance pour utiliser cette fonctionnalité."
            else:
                message = "Please configure your Gemini API key in the Governance page to use this feature."

            yield json.dumps({
                "node": "error",
                "state": {
                    "error": "api_key_required",
                    "message": message,
                    "final_answer": json.dumps({
                        "answer": message,
                        "abstained": True,
                        "citations": [],
                        "bullets": []
                    })
                }
            }) + "\n"
            yield json.dumps({"node": "complete", "state": {}}) + "\n"
            return

        try:
            async for event in graph.astream(initial_state):
                for node_name, output in event.items():
                    if node_name in node_names:
                        # Format: { node, state } - matching frontend expectation
                        yield json.dumps({
                            "node": node_name,
                            "state": _serialize_output(output)
                        }) + "\n"
            yield json.dumps({"node": "complete", "state": {}}) + "\n"
        except Exception as e:
            logger.error(f"Agent stream error: {type(e).__name__}: {e}")
            error_state = {"error": "An error occurred during processing"}
            if on_error:
                error_state["recovery"] = on_error(e, initial_state)
            yield json.dumps({"node": "error", "state": error_state}) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")


def _serialize_output(output: Any) -> Any:
    """Serialize output for JSON streaming."""
    if hasattr(output, "model_dump"):
        return output.model_dump()
    if isinstance(output, dict):
        return {k: _serialize_output(v) for k, v in output.items()}
    if isinstance(output, list):
        return [_serialize_output(item) for item in output]
    return output


__all__ = [
    "get_llm",
    "get_llm_response",
    "LLMService",
    "get_language_instruction",
    "clean_json_response",
    "parse_govlens_response",
    "create_agent_stream",
    "LEXGRAPH_NODES",
    "GOVLENS_NODES",
    "FORESIGHT_NODES",
    "ACCESSBRIDGE_NODES",
]
