"""
AccessBridge Agent State Definition

Defines the state schema for the AccessBridge LangGraph agent.
This agent helps users prepare applications by:
1. Processing multimodal inputs (text, OCR, voice)
2. Extracting relevant information
3. Identifying gaps and asking follow-up questions
4. Generating multiple output formats (form data, email, meeting prep)
"""

from typing import TypedDict, List, Annotated, Optional, Dict, Any, Literal
import operator


class ExtractedField(TypedDict, total=False):
    """A field extracted from user-provided documents/input."""
    key: str                    # Field name (e.g., "full_name", "income")
    value: Any                  # Extracted value
    source: str                 # Where it came from: "document", "voice", "text", "follow_up"
    confidence: float           # 0.0-1.0 confidence score
    requires_verification: bool # Whether human should verify


class InformationGap(TypedDict, total=False):
    """A piece of information that is missing but needed."""
    field: str                  # Missing field name
    question: str               # Human-friendly question to ask
    why_needed: str             # Explanation of why this is needed
    priority: Literal["critical", "important", "optional"]


class AccessBridgeState(TypedDict):
    """
    State schema for the AccessBridge LangGraph agent.

    The agent performs intelligent intake assistance through these steps:
    1. process_input      - Process OCR, STT, and text inputs
    2. retrieve_program   - Fetch program requirements from knowledge base
    3. extract_info       - Extract structured fields from combined inputs
    4. analyze_gaps       - Identify missing information and generate questions
    5. process_follow_up  - Process user answers to gap questions
    6. generate_outputs   - Create form data, email draft, meeting prep

    Accumulator fields (using operator.add):
    - trace_log: Appends thinking steps from each node
    - document_texts, audio_transcripts: Accumulate processed inputs
    - follow_up_answers: Accumulate answers to gap questions
    """

    # =========================================================================
    # Input Data (Accumulators)
    # =========================================================================

    # Text extracted from uploaded documents via OCR
    document_texts: Annotated[List[str], operator.add]

    # Text transcribed from voice recordings via STT
    audio_transcripts: Annotated[List[str], operator.add]

    # Raw text input from user
    raw_text_input: str

    # User's stated goal/purpose (e.g., "write email to CRA about disability EI")
    user_intent: str

    # File metadata for uploaded files
    uploaded_files: Annotated[List[Dict[str, str]], operator.add]  # [{filename, file_type, size}]

    # =========================================================================
    # Context Parameters
    # =========================================================================

    # Type of government program (e.g., "immigration", "benefits", "general")
    program_type: str

    # Retrieved context about program requirements
    program_context: str

    # Required fields for the program (from form template or hardcoded)
    required_fields: List[str]

    # User's preferred language for output (final results like email, meeting prep)
    language: str  # "en", "fr", "de", "it", "ja"

    # UI language for gap questions (what language to ask questions in)
    ui_language: str  # "en", "fr", "de", "it", "ja" - defaults to language if not provided

    # Uploaded PDF form template (optional - drives form-based extraction)
    # Format: {pdfBase64, formName, fields: [{name, type, label, ...}]}
    form_template: Optional[Dict[str, Any]]

    # Selected output modes (which outputs to generate)
    # Options: "form", "email", "meeting" - defaults to all if None/empty
    selected_modes: List[str]

    # =========================================================================
    # Processing State
    # =========================================================================

    # Fields extracted from all inputs
    extracted_fields: List[Dict[str, Any]]  # List of ExtractedField dicts

    # Identified gaps in information
    information_gaps: List[Dict[str, Any]]  # List of InformationGap dicts

    # Generated follow-up questions for gaps
    follow_up_questions: List[str]

    # User's answers to follow-up questions (accumulated)
    follow_up_answers: Annotated[List[Dict[str, str]], operator.add]  # [{field: answer}]

    # =========================================================================
    # Agent Control
    # =========================================================================

    # Current pipeline step name
    current_step: str

    # Safety counter for loops
    loop_count: int

    # Whether there are critical gaps requiring user input
    has_critical_gaps: bool

    # Agent thinking process (for UI display)
    trace_log: Annotated[List[str], operator.add]

    # =========================================================================
    # Output
    # =========================================================================

    # Structured form data ready for prefilling
    form_data: Optional[Dict[str, Any]]

    # Generated email draft
    email_draft: Optional[str]

    # Meeting preparation summary
    meeting_prep: Optional[str]

    # Overall confidence score (0.0-1.0)
    overall_confidence: float

    # Status of the intake process
    completion_status: Literal["incomplete", "needs_input", "ready_for_review", "complete"]


def create_initial_state(
    raw_text_input: str = "",
    program_type: str = "general",
    language: str = "en",
    ui_language: Optional[str] = None,
    follow_up_answers: Optional[List[Dict[str, str]]] = None,
    form_template: Optional[Dict[str, Any]] = None,
    selected_modes: Optional[List[str]] = None,
) -> AccessBridgeState:
    """
    Create an initial state for the AccessBridge agent.

    Args:
        raw_text_input: User's raw text input (document content, notes, etc.)
        program_type: Type of government program
        language: User's preferred language for outputs ("en", "fr", "de", "it", "ja")
        ui_language: Language for gap questions (defaults to language if not provided)
        follow_up_answers: Pre-supplied answers to gap questions (for resumption)
        form_template: Uploaded PDF form with extracted fields (optional)
        selected_modes: Which outputs to generate (form, email, meeting). Defaults to all.

    Returns:
        AccessBridgeState: Initialized state for the agent
    """
    if follow_up_answers is None:
        follow_up_answers = []
    if selected_modes is None:
        selected_modes = ["form", "email", "meeting"]  # Default: all modes
    if ui_language is None:
        ui_language = language  # Default UI language to output language

    return AccessBridgeState(
        # Input (start empty, will be populated)
        document_texts=[],
        audio_transcripts=[],
        raw_text_input=raw_text_input,
        user_intent="",  # Will be detected from raw_text_input
        uploaded_files=[],

        # Context
        program_type=program_type,
        program_context="",
        required_fields=[],
        language=language,
        ui_language=ui_language,
        form_template=form_template,
        selected_modes=selected_modes,

        # Processing (start empty)
        extracted_fields=[],
        information_gaps=[],
        follow_up_questions=[],
        follow_up_answers=follow_up_answers,

        # Control
        current_step="process_input",
        loop_count=1 if follow_up_answers else 0,
        has_critical_gaps=False,
        trace_log=[],

        # Output (None until computed)
        form_data=None,
        email_draft=None,
        meeting_prep=None,
        overall_confidence=0.0,
        completion_status="incomplete",
    )
