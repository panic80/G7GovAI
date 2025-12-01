"""
API Request/Response schemas with comprehensive input validation.

All user-facing request models include:
- Length constraints to prevent DoS attacks
- Pattern validation for structured fields
- Range validation for numeric fields
- Enum validation for categorical fields
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional, Any, Literal
import re
from core.config import LLM_FAST_MODEL, TTS_MODEL

# =============================================================================
# Constants for validation
# =============================================================================

MAX_QUERY_LENGTH = 2000
MAX_PROMPT_LENGTH = 100000  # Increased for summarization of multiple documents
MAX_TEXT_LENGTH = 50000  # For OCR/STT results
MIN_QUERY_LENGTH = 1
SUPPORTED_LANGUAGES = ("en", "fr")
DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"


# =============================================================================
# Model Configuration
# =============================================================================

class ModelConfigUpdate(BaseModel):
    """Update LLM model configuration."""
    fast: Optional[str] = Field(None, max_length=100)
    reasoning: Optional[str] = Field(None, max_length=100)
    vision: Optional[str] = Field(None, max_length=100)
    audio: Optional[str] = Field(None, max_length=100)
    tts: Optional[str] = Field(None, max_length=100)


class ApiKeyUpdate(BaseModel):
    """Update custom API key (empty string to clear)."""
    api_key: str = Field("", max_length=200)


# =============================================================================
# Search Schemas
# =============================================================================

class SearchRequest(BaseModel):
    """Request schema for semantic search."""
    query: str = Field(
        ...,
        min_length=MIN_QUERY_LENGTH,
        max_length=MAX_QUERY_LENGTH,
        description="Search query text"
    )
    language: Literal["en", "fr"] = Field(
        default="en",
        description="Response language"
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Maximum number of results"
    )
    reference_date: Optional[str] = Field(
        default=None,
        pattern=DATE_PATTERN,
        description="Filter by date (YYYY-MM-DD)"
    )
    strategy: Literal["relevance", "diverse"] = Field(
        default="relevance",
        description="Search strategy"
    )
    diversity_lambda: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Diversity weight for MMR (0=pure relevance, 1=max diversity)"
    )
    categories: Optional[List[str]] = Field(
        default=None,
        max_length=10,
        description="Filter by document categories"
    )
    themes: Optional[List[str]] = Field(
        default=None,
        max_length=20,
        description="Filter by themes (partial match)"
    )

    @field_validator('categories', 'themes', mode='before')
    @classmethod
    def validate_string_lists(cls, v):
        if v is not None:
            # Limit individual string lengths
            return [str(item)[:100] for item in v]
        return v


class SearchResult(BaseModel):
    """Search result item."""
    id: str
    content: str
    source_title: str
    score: float
    rerank_score: Optional[float] = None
    metadata: dict


class FilterOptionsResponse(BaseModel):
    """Available filter options for search."""
    categories: List[str]
    themes: List[str]


# =============================================================================
# Agent Request Schemas
# =============================================================================

class AgentSearchRequest(BaseModel):
    """Request schema for LexGraph rules agent."""
    query: str = Field(
        ...,
        min_length=MIN_QUERY_LENGTH,
        max_length=MAX_QUERY_LENGTH,
        description="User scenario for eligibility evaluation"
    )
    language: Literal["en", "fr"] = Field(default="en")
    effective_date: str = Field(
        ...,
        pattern=DATE_PATTERN,
        description="Reference date for rule evaluation (YYYY-MM-DD)"
    )


class GovLensAgentRequest(BaseModel):
    """Request schema for GovLens search agent."""
    query: str = Field(
        ...,
        min_length=MIN_QUERY_LENGTH,
        max_length=MAX_QUERY_LENGTH,
        description="Natural language search query"
    )
    language: Literal["en", "fr"] = Field(default="en")
    categories: Optional[List[str]] = Field(
        default=None,
        max_length=10,
        description="Filter by document categories"
    )
    themes: Optional[List[str]] = Field(
        default=None,
        max_length=20,
        description="Filter by themes"
    )

    @field_validator('categories', 'themes', mode='before')
    @classmethod
    def validate_string_lists(cls, v):
        if v is not None:
            return [str(item)[:100] for item in v]
        return v


# =============================================================================
# ForesightOps Schemas
# =============================================================================

class CapitalPlanRequest(BaseModel):
    """Request schema for capital planning."""
    budget: float = Field(
        ...,
        gt=0,
        le=1_000_000_000_000,  # 1 trillion max
        description="Total budget allocation"
    )
    priorities: Dict[str, float] = Field(
        ...,
        description="Priority weights (must sum to ~1.0)"
    )

    @field_validator('priorities')
    @classmethod
    def validate_priorities(cls, v):
        if not v:
            raise ValueError("priorities cannot be empty")
        if len(v) > 20:
            raise ValueError("Too many priority keys (max 20)")
        for key, val in v.items():
            if not isinstance(val, (int, float)) or val < 0 or val > 1:
                raise ValueError(f"Priority '{key}' must be between 0 and 1")
        return v


class EmergencySimRequest(BaseModel):
    """Request schema for emergency simulation."""
    event_type: Literal["Snowstorm", "Flood", "Earthquake", "Fire", "None"] = Field(
        ...,
        description="Type of emergency event to simulate"
    )


class ForesightAgentRequest(BaseModel):
    """Request schema for ForesightOps optimization agent."""
    query: str = Field(
        default="",
        max_length=MAX_QUERY_LENGTH,
        description="Optional natural language query"
    )
    language: Literal["en", "fr"] = Field(default="en")
    budget_total: float = Field(
        default=10_000_000,
        gt=0,
        le=1_000_000_000_000,
        description="Total budget for optimization"
    )
    planning_horizon_years: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Planning horizon in years"
    )
    weights: Dict[str, float] = Field(
        default={"risk": 0.6, "coverage": 0.4},
        description="Optimization weights"
    )
    region_filter: Optional[List[str]] = Field(
        default=None,
        max_length=50,
        description="Filter by region codes"
    )
    asset_type_filter: Optional[List[str]] = Field(
        default=None,
        max_length=20,
        description="Filter by asset types"
    )
    include_scenarios: bool = Field(default=False)
    enforce_equity: bool = Field(
        default=False,
        description="Enforce regional equity constraints"
    )

    @field_validator('weights')
    @classmethod
    def validate_weights(cls, v):
        if not v:
            return {"risk": 0.6, "coverage": 0.4}
        if len(v) > 10:
            raise ValueError("Too many weight keys (max 10)")
        for key, val in v.items():
            if not isinstance(val, (int, float)) or val < 0 or val > 1:
                raise ValueError(f"Weight '{key}' must be between 0 and 1")
        return v


# =============================================================================
# Generation Schemas
# =============================================================================

class GenerateRequest(BaseModel):
    """Request schema for LLM generation."""
    prompt: str = Field(
        ...,
        min_length=1,
        max_length=MAX_PROMPT_LENGTH,
        description="Generation prompt"
    )
    history: Optional[List[Dict[str, str]]] = Field(
        default=[],
        max_length=50,
        description="Conversation history"
    )
    context: Optional[str] = Field(
        default="",
        max_length=MAX_PROMPT_LENGTH,
        description="Additional context"
    )
    response_schema: Optional[Dict[str, Any]] = Field(
        default=None,
        description="JSON schema for structured output",
        alias="schema"  # Accept "schema" in input for backward compatibility
    )
    model_name: str = Field(
        default=LLM_FAST_MODEL,
        max_length=100
    )
    temperature: float = Field(
        default=0.1,
        ge=0.0,
        le=2.0,
        description="Sampling temperature"
    )


class TTSRequest(BaseModel):
    """Request schema for text-to-speech."""
    text: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Text to convert to speech"
    )
    language: Literal["en", "fr"] = Field(default="en")
    model_name: str = Field(
        default=TTS_MODEL,
        max_length=100
    )


# =============================================================================
# Audit Schemas
# =============================================================================

class AuditLog(BaseModel):
    """Audit log entry."""
    timestamp: str
    module: str = Field(..., max_length=100)
    action: str = Field(..., max_length=100)
    duration_ms: int = Field(..., ge=0)
    status: str = Field(..., max_length=50)
    metadata: Dict[str, Any]


# =============================================================================
# Document Schemas
# =============================================================================

class DocumentMetadata(BaseModel):
    """Document metadata for knowledge base."""
    source_title: str = Field(..., max_length=500)
    source_id: str = Field(..., max_length=100)
    doc_type: str = Field(..., max_length=50)
    category: str = Field(..., max_length=100)
    themes: str = Field(..., max_length=500)
    chunk_count: int = Field(..., ge=0)
    updated_at: str


# =============================================================================
# AccessBridge Schemas
# =============================================================================

class AccessBridgeRequest(BaseModel):
    """Request schema for AccessBridge intake agent."""
    raw_text_input: str = Field(
        default="",
        max_length=MAX_TEXT_LENGTH,
        description="User's raw text input"
    )
    program_type: Literal["auto", "general", "immigration", "benefits", "housing", "disability"] = Field(
        default="general",
        description="Type of government program ('auto' for auto-detection)"
    )
    language: Literal["en", "fr", "de", "it", "ja"] = Field(
        default="en",
        description="Output language for final results (email, meeting prep)"
    )
    ui_language: Optional[Literal["en", "fr", "de", "it", "ja"]] = Field(
        default=None,
        description="UI language for gap questions. Defaults to language if not provided."
    )
    document_texts: Optional[List[str]] = Field(
        default=None,
        max_length=20,
        description="Pre-processed OCR results"
    )
    audio_transcripts: Optional[List[str]] = Field(
        default=None,
        max_length=10,
        description="Pre-processed STT results"
    )
    follow_up_answers: Optional[List[Dict[str, str]]] = Field(
        default=None,
        max_length=50,
        description="Answers to gap questions"
    )
    form_template: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Uploaded PDF form template with extracted fields: {pdfBase64, formName, fields}"
    )
    selected_modes: Optional[List[Literal["form", "email", "meeting"]]] = Field(
        default=None,
        max_length=3,
        description="Selected output modes. If None, generates all outputs."
    )

    @field_validator('document_texts', mode='before')
    @classmethod
    def validate_document_texts(cls, v):
        if v is not None:
            # Limit individual document lengths
            return [str(doc)[:MAX_TEXT_LENGTH] for doc in v]
        return v

    @field_validator('audio_transcripts', mode='before')
    @classmethod
    def validate_audio_transcripts(cls, v):
        if v is not None:
            return [str(t)[:MAX_TEXT_LENGTH] for t in v]
        return v


class OcrRequest(BaseModel):
    """Request schema for OCR processing."""
    file_base64: str = Field(
        ...,
        min_length=1,
        max_length=50_000_000,  # ~37MB after base64 encoding
        description="Base64-encoded file content"
    )
    file_type: Literal["pdf", "png", "jpg", "jpeg"] = Field(
        default="pdf",
        description="File type"
    )
    language: Literal["en", "fr"] = Field(default="en")


class SttRequest(BaseModel):
    """Request schema for Speech-to-Text processing."""
    audio_base64: str = Field(
        ...,
        min_length=1,
        max_length=100_000_000,  # ~75MB after base64 encoding
        description="Base64-encoded audio content"
    )
    audio_format: Literal["wav", "mp3", "webm", "ogg", "m4a"] = Field(
        default="wav",
        description="Audio format"
    )
    language: Literal["en", "fr"] = Field(default="en")


class TranslateRequest(BaseModel):
    """Request schema for text translation."""
    texts: List[str] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of texts to translate"
    )
    target_language: str = Field(
        ...,
        min_length=2,
        max_length=10,
        description="Target language code (ISO 639-1)"
    )
    source_language: str = Field(
        default="en",
        min_length=2,
        max_length=10,
        description="Source language code (ISO 639-1)"
    )

    @field_validator('texts', mode='before')
    @classmethod
    def validate_texts(cls, v):
        if v is not None:
            # Limit individual text lengths
            return [str(text)[:5000] for text in v]
        return v


# =============================================================================
# PDF Form Filling Schemas
# =============================================================================

class FormExtractRequest(BaseModel):
    """Request schema for extracting fields from a PDF form."""
    pdf_base64: str = Field(
        ...,
        min_length=1,
        max_length=50_000_000,  # ~37MB after base64 encoding
        description="Base64-encoded PDF file content"
    )
    language: Literal["en", "fr"] = Field(default="en")


class FormFillRequest(BaseModel):
    """Request schema for filling a PDF form with values."""
    pdf_base64: str = Field(
        ...,
        min_length=1,
        max_length=50_000_000,
        description="Base64-encoded PDF file content"
    )
    field_values: Dict[str, str] = Field(
        ...,
        description="Mapping of field names to values"
    )
    flatten: bool = Field(
        default=False,
        description="Whether to flatten the form (make non-editable)"
    )

    @field_validator('field_values')
    @classmethod
    def validate_field_values(cls, v):
        if len(v) > 500:
            raise ValueError("Too many field values (max 500)")
        # Limit value lengths
        return {k[:200]: str(val)[:5000] for k, val in v.items()}


class FormAutoFillRequest(BaseModel):
    """Request schema for auto-filling a PDF form with extracted data."""
    pdf_base64: str = Field(
        ...,
        min_length=1,
        max_length=50_000_000,
        description="Base64-encoded PDF file content"
    )
    extracted_data: Dict[str, Any] = Field(
        ...,
        description="Extracted data with values and confidence scores"
    )
    language: Literal["en", "fr"] = Field(default="en")

    @field_validator('extracted_data')
    @classmethod
    def validate_extracted_data(cls, v):
        if len(v) > 200:
            raise ValueError("Too many extracted fields (max 200)")
        return v
