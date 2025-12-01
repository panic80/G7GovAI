"""
AccessBridge Agent Nodes

Implements the core logic for each step in the AccessBridge intake pipeline.
Each node takes the current state and returns updates to be merged into the state.

Pipeline:
1. process_input      - Combine all input sources (OCR, STT, text)
2. retrieve_program   - Fetch program requirements from knowledge base
3. extract_info       - Extract structured fields using LLM
4. analyze_gaps       - Identify missing info and generate questions
5. process_follow_up  - Merge follow-up answers into extracted fields
6. generate_outputs   - Create form data, email draft, meeting prep
"""

import json
import base64
import logging
from typing import Dict, Any, List, Optional
import google.generativeai as genai

logger = logging.getLogger(__name__)

from .state import AccessBridgeState
from agent.core import (
    get_llm_response,
    get_language_instruction,
    clean_json_response,
)
from core.model_state import model_config


# =============================================================================
# Helper Functions
# =============================================================================

def get_vision_response(image_data: bytes, prompt: str, mime_type: str = "image/png") -> str:
    """Get OCR/vision response from Gemini Vision model."""
    try:
        model = genai.GenerativeModel(model_config.get_model("vision"))

        # Create image part
        image_part = {
            "mime_type": mime_type,
            "data": image_data
        }

        response = model.generate_content([prompt, image_part])
        return response.text
    except Exception as e:
        logger.error(f"Vision Error: {type(e).__name__}")
        return ""


# =============================================================================
# NODE 1: PROCESS INPUT
# =============================================================================

def process_input_node(state: AccessBridgeState) -> Dict[str, Any]:
    """
    Process and combine all input sources.

    This node:
    - Detects user's stated intent/goal from text input
    - Auto-detects program type from content
    - Combines raw text input with any pre-processed OCR/STT results
    - Validates that there is some input to work with
    - Prepares the combined text for extraction
    """
    logger.debug("--- PROCESS INPUT ---")

    trace_messages = []
    combined_texts = []
    user_intent = ""
    detected_program_type = state.get("program_type", "general")

    # Collect raw text input
    raw_text = state.get("raw_text_input", "")
    if raw_text.strip():
        # Detect user's intent AND program type from their text input
        intent_prompt = f"""Analyze this user input and identify their communication intent and the type of government program.

User input: "{raw_text}"

The user is using AccessBridge to communicate with government officials.
Identify:
1. Their stated PURPOSE/GOAL - what do they want to accomplish?
2. The PROGRAM TYPE based on keywords and context:
   - "immigration" - work permits, LMIA, visas, PR, citizenship, immigration status
   - "benefits" - EI, Employment Insurance, disability benefits, CPP, OAS, welfare, social assistance, ROE, Record of Employment
   - "housing" - housing assistance, rent subsidy, affordable housing, shelter
   - "general" - other government inquiries, documents, taxes, permits
3. Any DOCUMENT CONTENT they're providing (personal info, copied text from documents, etc.)

Return JSON:
{{
    "user_intent": "A clear, concise description of what the user wants to accomplish. If they don't state a clear intent, return empty string.",
    "program_type": "One of: immigration, benefits, housing, general",
    "document_content": "Any personal info or document content extracted from their input. If none, return empty string."
}}

Only return JSON, no other text."""

        try:
            intent_response = get_llm_response(intent_prompt, temperature=0.1, json_mode=True)
            parsed_intent = json.loads(clean_json_response(intent_response))
            user_intent = parsed_intent.get("user_intent", "")
            detected_program_type = parsed_intent.get("program_type", "general")
            document_content = parsed_intent.get("document_content", "")

            if user_intent:
                trace_messages.append(f"Detected user intent: {user_intent}")
            trace_messages.append(f"Auto-detected program type: {detected_program_type}")

            # Use document content if detected, otherwise use raw text
            text_to_add = document_content if document_content else raw_text
            if text_to_add.strip():
                combined_texts.append(f"[User Input]\n{text_to_add}")

        except Exception as e:
            logger.warning(f"Intent detection error: {type(e).__name__}")
            # Fall back to using raw text as-is
            combined_texts.append(f"[User Input]\n{raw_text}")

        trace_messages.append(f"Received text input ({len(raw_text)} characters)")

    # Collect OCR results (pre-processed by /ocr endpoint)
    document_texts = state.get("document_texts", [])
    for i, doc_text in enumerate(document_texts):
        if doc_text.strip():
            combined_texts.append(f"[Document {i+1}]\n{doc_text}")
    if document_texts:
        trace_messages.append(f"Processed {len(document_texts)} document(s) via OCR")

    # Collect STT results (pre-processed by /stt endpoint)
    audio_transcripts = state.get("audio_transcripts", [])
    for i, transcript in enumerate(audio_transcripts):
        if transcript.strip():
            combined_texts.append(f"[Voice Recording {i+1}]\n{transcript}")
    if audio_transcripts:
        trace_messages.append(f"Processed {len(audio_transcripts)} voice recording(s)")

    # Check if we have any input
    if not combined_texts:
        trace_messages.append("No input provided. Please provide text, upload a document, or record audio.")
        return {
            "current_step": "process_input",
            "trace_log": trace_messages,
            "completion_status": "incomplete",
        }

    # Store combined text for later processing
    combined_input = "\n\n---\n\n".join(combined_texts)
    trace_messages.append(f"Combined all inputs: {len(combined_input)} total characters")

    # Re-run intent detection with full context if raw_text was weak/general but we have documents
    if (not user_intent or detected_program_type == "general") and (document_texts or audio_transcripts):
        trace_messages.append("Refining intent detection using document/audio context...")
        
        # Create a context snippet from documents/audio (max 1000 chars)
        context_snippet = combined_input[:1000] + ("..." if len(combined_input) > 1000 else "")
        
        intent_prompt = f"""Analyze this user input and identifying their communication intent and the type of government program.

User Input / Context:
"{context_snippet}"

The user is using AccessBridge to communicate with government officials.
Identify:
1. Their stated PURPOSE/GOAL - what do they want to accomplish?
2. The PROGRAM TYPE based on keywords and context:
   - "immigration" - work permits, LMIA, visas, PR, citizenship, immigration status
   - "benefits" - EI, Employment Insurance, disability benefits, CPP, OAS, welfare, social assistance, ROE, Record of Employment
   - "housing" - housing assistance, rent subsidy, affordable housing, shelter
   - "general" - other government inquiries, documents, taxes, permits
3. Any DOCUMENT CONTENT they're providing (personal info, copied text from documents, etc.)

Return JSON:
{{
    "user_intent": "A clear, concise description of what the user wants to accomplish.",
    "program_type": "One of: immigration, benefits, housing, general",
    "document_content": ""
}}

Only return JSON, no other text."""

        try:
            intent_response = get_llm_response(intent_prompt, temperature=0.1, json_mode=True)
            parsed_intent = json.loads(clean_json_response(intent_response))
            user_intent = parsed_intent.get("user_intent", "")
            detected_program_type = parsed_intent.get("program_type", "general")
            
            if user_intent:
                trace_messages.append(f"Detected intent from context: {user_intent}")
            trace_messages.append(f"Detected program type from context: {detected_program_type}")
            
        except Exception as e:
            logger.warning(f"Context intent detection error: {type(e).__name__}")

    return {
        "current_step": "retrieve_program",
        "raw_text_input": combined_input,  # Update with combined version
        "user_intent": user_intent,  # User's stated goal/purpose
        "program_type": detected_program_type,  # Auto-detected program type
        "trace_log": trace_messages,
    }


# =============================================================================
# NODE 2: RETRIEVE PROGRAM CONTEXT
# =============================================================================

def retrieve_program_context_node(state: AccessBridgeState) -> Dict[str, Any]:
    """
    Fetch program requirements from the knowledge base.

    This node:
    - Queries ChromaDB for relevant program information
    - Identifies required fields based on program type
    - Provides context for the extraction step
    """
    logger.debug("--- RETRIEVE PROGRAM CONTEXT ---")

    trace_messages = []
    program_type = state.get("program_type", "general")
    language = state.get("language", "en")

    # Try to retrieve from ChromaDB
    program_context = ""
    required_fields = []

    try:
        # Import here to avoid circular imports
        from database import get_collection
        from embeddings import get_embedding

        collection = get_collection()

        # Search for program-related documents
        query = f"{program_type} program application requirements eligibility"
        query_embedding = get_embedding(query)

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=5,
            where={"language": language} if language else None,
            include=["documents", "metadatas"]
        )

        if results and results.get("documents") and results["documents"][0]:
            docs = results["documents"][0]
            program_context = "\n\n".join(docs[:3])  # Top 3 most relevant
            trace_messages.append(f"Retrieved {len(docs)} relevant program documents")
        else:
            trace_messages.append("No specific program context found, using general extraction")

    except Exception as e:
        logger.error(f"Context retrieval error: {type(e).__name__}")
        trace_messages.append(f"Using general extraction (context retrieval unavailable)")

    # Check if a form template was uploaded - if so, use form field labels as required_fields
    form_template = state.get("form_template")

    if form_template and (form_template.get("fields") or form_template.get("field_groups")):
        required_fields = []

        # FORM-DRIVEN: Use standalone field labels
        form_fields = form_template.get("fields", [])
        for f in form_fields:
            if f.get("type") not in ["button", "signature"]:
                required_fields.append(f.get("label") or f.get("name", "Unknown Field"))

        # FORM-DRIVEN: Use group labels (NOT individual options)
        # This ensures we ask "What is your marital status?" instead of separate questions for each option
        field_groups = form_template.get("field_groups", [])
        for g in field_groups:
            group_label = g.get("group_label") or g.get("group_name", "Unknown Group")
            required_fields.append(group_label)

        trace_messages.append(f"Using {len(required_fields)} fields from uploaded form: {form_template.get('formName', 'Unknown Form')}")
        if field_groups:
            trace_messages.append(f"Including {len(field_groups)} grouped fields (checkboxes/radios/dropdowns)")
    else:
        # FALLBACK: Use hardcoded fields based on program type
        common_fields = {
            "general": ["full_name", "date_of_birth", "address", "phone", "email"],
            "immigration": ["full_name", "date_of_birth", "country_of_birth", "passport_number",
                           "current_status", "employer", "job_title", "salary", "work_location"],
            "benefits": ["full_name", "date_of_birth", "social_insurance_number", "employment_status",
                        "income", "dependents", "address"],
            "housing": ["full_name", "household_size", "monthly_income", "current_rent",
                       "employment_status", "address"],
        }
        required_fields = common_fields.get(program_type, common_fields["general"])
        trace_messages.append(f"Identified {len(required_fields)} required fields for {program_type} program")

    return {
        "current_step": "extract_info",
        "program_context": program_context,
        "required_fields": required_fields,
        "trace_log": trace_messages,
    }


# =============================================================================
# NODE 3: EXTRACT INFORMATION
# =============================================================================

def extract_information_node(state: AccessBridgeState) -> Dict[str, Any]:
    """
    Extract structured fields from combined inputs using LLM.

    This node:
    - Uses Gemini to identify and extract key fields
    - Assigns confidence scores to each extraction
    - Identifies the source of each piece of information
    """
    logger.debug("--- EXTRACT INFORMATION ---")

    trace_messages = []
    language = state.get("language", "en")
    combined_input = state.get("raw_text_input", "")
    required_fields = state.get("required_fields", [])
    program_context = state.get("program_context", "")

    # Include any previous follow-up answers
    follow_up_answers = state.get("follow_up_answers", [])
    if follow_up_answers:
        answers_text = "\n".join([f"- {k}: {v}" for fa in follow_up_answers for k, v in fa.items()])
        combined_input += f"\n\n[Additional Information Provided]\n{answers_text}"

    lang_instruction = get_language_instruction(language)

    prompt = f"""You are extracting information from user input for a government application.

{lang_instruction}

CRITICAL ANTI-HALLUCINATION RULES:
1. ONLY extract information that is EXPLICITLY and LITERALLY stated in the input below
2. DO NOT infer, assume, guess, or make up ANY values
3. DO NOT use common knowledge or typical values - only what is written
4. If a field is not DIRECTLY stated in the input, DO NOT include it
5. An empty "fields" array is completely acceptable if nothing relevant is found
6. When in doubt, DO NOT extract - it's better to ask the user than to guess

FIELDS TO LOOK FOR (extract ONLY if explicitly mentioned):
{json.dumps(required_fields)}

USER INPUT TO EXTRACT FROM:
---
{combined_input}
---

For each piece of information you extract:
- key: The field name (snake_case, matching the fields above if possible)
- value: The EXACT value as stated in the input (do not reformat or clean up)
- source: Where found ("text", "document", "voice", "follow_up")
- confidence: Your confidence (0.0-1.0) - use lower confidence if value seems incomplete
- requires_verification: true if unclear or partial

Return JSON:
{{
    "fields": [
        {{"key": "full_name", "value": "John Smith", "source": "text", "confidence": 0.95, "requires_verification": false}},
        ...
    ],
    "extraction_summary": "Brief summary of what was found"
}}

REMEMBER: Empty "fields": [] is better than hallucinated data!
Only return JSON, no other text."""

    try:
        response = get_llm_response(prompt, temperature=0.0, json_mode=True)

        # Parse response using shared utilities
        parsed = json.loads(clean_json_response(response))
        extracted_fields = parsed.get("fields", [])
        summary = parsed.get("extraction_summary", "Extraction completed")

        trace_messages.append(f"Extracted {len(extracted_fields)} fields: {summary}")

        return {
            "current_step": "analyze_gaps",
            "extracted_fields": extracted_fields,
            "trace_log": trace_messages,
        }

    except Exception as e:
        logger.error(f"Extraction error: {type(e).__name__}")
        trace_messages.append(f"Extraction error: {str(e)}")

        return {
            "current_step": "analyze_gaps",
            "extracted_fields": [],
            "trace_log": trace_messages,
        }


# =============================================================================
# NODE 4: ANALYZE GAPS
# =============================================================================

def analyze_gaps_node(state: AccessBridgeState) -> Dict[str, Any]:
    """
    Identify missing information and generate follow-up questions.

    This node:
    - Compares extracted fields against required fields
    - Identifies critical vs optional gaps
    - Generates human-friendly questions for missing info
    - Includes input_type and options for grouped fields (checkbox/radio/dropdown)
    """
    logger.debug("--- ANALYZE GAPS ---")

    trace_messages = []
    # Use UI language for gap questions (falls back to output language if not set)
    ui_language = state.get("ui_language") or state.get("language", "en")
    required_fields = state.get("required_fields", [])
    extracted_fields = state.get("extracted_fields", [])
    loop_count = state.get("loop_count", 0)
    form_template = state.get("form_template", {})

    # Build a lookup of grouped fields for enriching gaps with input_type and options
    grouped_fields_lookup: Dict[str, Dict] = {}
    field_groups = form_template.get("field_groups", []) if form_template else []
    for g in field_groups:
        group_label = g.get("group_label") or g.get("group_name", "")
        if group_label:
            grouped_fields_lookup[group_label.lower()] = {
                "input_type": g.get("group_type", "text"),  # "radio", "checkbox", "dropdown"
                "options": [opt.get("label", opt.get("name", "")) for opt in g.get("options", [])]
            }

    # Get set of extracted field keys
    extracted_keys = {f.get("key", "").lower() for f in extracted_fields}

    # Find missing fields
    missing_fields = [f for f in required_fields if f.lower() not in extracted_keys]

    if not missing_fields:
        trace_messages.append("All required fields have been extracted")
        return {
            "current_step": "generate_outputs",
            "information_gaps": [],
            "follow_up_questions": [],
            "has_critical_gaps": False,
            "trace_log": trace_messages,
        }

    # Generate questions for missing fields using LLM
    lang_instruction = get_language_instruction(ui_language)

    # Include grouped field info in the prompt so LLM knows about options
    grouped_info = []
    for field in missing_fields:
        field_lower = field.lower()
        if field_lower in grouped_fields_lookup:
            info = grouped_fields_lookup[field_lower]
            grouped_info.append({
                "field": field,
                "type": info["input_type"],
                "options": info["options"]
            })

    grouped_hint = ""
    if grouped_info:
        grouped_hint = f"""

GROUPED FIELDS (these have predefined options - phrase questions appropriately):
{json.dumps(grouped_info, indent=2)}

For grouped fields:
- For "radio" type: Ask user to select ONE option
- For "checkbox" type: Ask user to select ALL that apply
- For "dropdown" type: Ask user to choose from the list
"""

    prompt = f"""You are AccessBridge, helping users complete government applications.

{lang_instruction}

TASK: Generate friendly follow-up questions for missing information.

MISSING FIELDS:
{json.dumps(missing_fields)}

ALREADY EXTRACTED:
{json.dumps([f.get("key") for f in extracted_fields])}{grouped_hint}

For each missing field, create:
1. A clear, friendly question in the user's language
2. An explanation of why this information is needed
3. Priority level: "critical" (must have), "important" (strongly recommended), or "optional"

Return JSON:
{{
    "gaps": [
        {{
            "field": "social_insurance_number",
            "question": "What is your Social Insurance Number (SIN)?",
            "why_needed": "Required for government benefit applications and tax purposes",
            "priority": "critical"
        }},
        ...
    ]
}}

Only return the JSON, no other text."""

    try:
        response = get_llm_response(prompt, temperature=0.1, json_mode=True)

        # Parse response using shared utilities
        parsed = json.loads(clean_json_response(response))
        gaps = parsed.get("gaps", [])

        # Enrich gaps with input_type and options from form template
        for gap in gaps:
            field_lower = gap.get("field", "").lower()
            if field_lower in grouped_fields_lookup:
                info = grouped_fields_lookup[field_lower]
                gap["input_type"] = info["input_type"]
                gap["options"] = info["options"]
            else:
                # Default to text input for non-grouped fields
                gap["input_type"] = "text"

        # Extract just the questions for display
        questions = [g.get("question", "") for g in gaps]

        # Check if there are critical gaps
        critical_gaps = [g for g in gaps if g.get("priority") == "critical"]
        has_critical = len(critical_gaps) > 0

        trace_messages.append(f"Identified {len(gaps)} missing fields ({len(critical_gaps)} critical)")

        # If we've already done one round of follow-up, proceed to outputs anyway
        if loop_count >= 1:
            trace_messages.append("Proceeding with available information after follow-up")
            return {
                "current_step": "generate_outputs",
                "information_gaps": gaps,
                "follow_up_questions": questions,
                "has_critical_gaps": False,  # Force proceed
                "loop_count": loop_count + 1,
                "trace_log": trace_messages,
            }

        return {
            "current_step": "generate_outputs" if not has_critical else "analyze_gaps",
            "information_gaps": gaps,
            "follow_up_questions": questions,
            "has_critical_gaps": has_critical,
            "completion_status": "needs_input" if has_critical else "ready_for_review",
            "loop_count": loop_count + 1,
            "trace_log": trace_messages,
        }

    except Exception as e:
        logger.error(f"Gap analysis error: {type(e).__name__}")
        trace_messages.append(f"Gap analysis error: {str(e)}")

        return {
            "current_step": "generate_outputs",
            "information_gaps": [],
            "follow_up_questions": [],
            "has_critical_gaps": False,
            "trace_log": trace_messages,
        }


# =============================================================================
# NODE 5: PROCESS FOLLOW-UP
# =============================================================================

def process_follow_up_node(state: AccessBridgeState) -> Dict[str, Any]:
    """
    Process user's answers to follow-up questions.

    This node:
    - Merges follow-up answers into extracted fields
    - Re-triggers extraction if significant new info provided
    """
    logger.debug("--- PROCESS FOLLOW-UP ---")

    trace_messages = []
    follow_up_answers = state.get("follow_up_answers", [])
    extracted_fields = state.get("extracted_fields", [])

    if not follow_up_answers:
        trace_messages.append("No follow-up answers provided")
        return {
            "current_step": "generate_outputs",
            "trace_log": trace_messages,
        }

    # Convert follow-up answers to extracted fields format
    new_fields = []
    for answer_dict in follow_up_answers:
        for field_key, value in answer_dict.items():
            if value and value.strip():
                new_fields.append({
                    "key": field_key,
                    "value": value,
                    "source": "follow_up",
                    "confidence": 1.0,  # User-provided, high confidence
                    "requires_verification": False,
                })

    # Merge with existing fields (new values override old ones)
    existing_keys = {f.get("key"): f for f in extracted_fields}
    for new_field in new_fields:
        existing_keys[new_field["key"]] = new_field

    merged_fields = list(existing_keys.values())

    trace_messages.append(f"Processed {len(new_fields)} follow-up answers, total fields: {len(merged_fields)}")

    return {
        "current_step": "analyze_gaps",  # Re-check for remaining gaps
        "extracted_fields": merged_fields,
        "trace_log": trace_messages,
    }


# =============================================================================
# NODE 6: GENERATE OUTPUTS
# =============================================================================

def generate_outputs_node(state: AccessBridgeState) -> Dict[str, Any]:
    """
    Generate output formats based on user's selected modes.

    This node:
    - Structures extracted fields into form-ready JSON (if 'form' mode selected)
    - Generates a professional email draft (if 'email' mode selected)
    - Creates a meeting preparation summary (if 'meeting' mode selected)
    """
    logger.debug("--- GENERATE OUTPUTS ---")

    trace_messages = []
    language = state.get("language", "en")
    program_type = state.get("program_type", "general")
    extracted_fields = state.get("extracted_fields", [])
    information_gaps = state.get("information_gaps", [])
    user_intent = state.get("user_intent", "")
    selected_modes = state.get("selected_modes", ["form", "email", "meeting"])  # Default: all modes

    # Calculate overall confidence
    if extracted_fields:
        confidences = [f.get("confidence", 0.5) for f in extracted_fields]
        overall_confidence = sum(confidences) / len(confidences)
    else:
        overall_confidence = 0.0

    # 1. Generate Form Data (structured JSON) - only if 'form' mode selected
    form_data = {}
    if "form" in selected_modes:
        for field in extracted_fields:
            key = field.get("key", "")
            value = field.get("value", "")
            if key and value:
                form_data[key] = {
                    "value": value,
                    "confidence": field.get("confidence", 0.5),
                    "source": field.get("source", "unknown"),
                }
        trace_messages.append(f"Generated form data with {len(form_data)} fields")
    else:
        trace_messages.append("Skipped form data generation (not selected)")

    # 2. Generate Email Draft - only if 'email' mode selected
    email_draft = ""
    if "email" in selected_modes:
        lang_instruction = get_language_instruction(language)

        email_prompt = f"""You are AccessBridge, helping users communicate with government officials.

{lang_instruction}

USER'S REQUEST OR GOAL: {user_intent if user_intent else "General inquiry about " + program_type + " services"}

PROGRAM TYPE: {program_type}

APPLICANT'S INFORMATION (from their documents):
{json.dumps(extracted_fields, indent=2)}

INFORMATION STILL NEEDED:
{json.dumps([g.get("field") for g in information_gaps])}

TASK: Write a professional email to a government representative. Determine the email type based on the user's request.

TYPE A - QUESTION: If the user is asking a question (e.g., "what documents do I need?", "am I eligible?", "how do I apply?"):
- Subject line should reflect their specific question
- Body should introduce the applicant briefly, then ASK their question clearly
- Request specific guidance or a list of requirements

TYPE B - APPLICATION: If the user wants to apply or submit something (e.g., "I want to apply for EI", "submit my work permit application"):
- Subject line should be about their application intent
- Body should introduce the applicant with relevant details from their documents
- State what they are applying for and request next steps or confirmation

CRITICAL RULES:
1. NEVER invent or hallucinate personal information.
2. Use ONLY actual values from the APPLICANT'S INFORMATION provided above.
3. If a piece of information (like Name, Address, Phone) is MISSING from APPLICANT'S INFORMATION, use a clear, generic placeholder (e.g., "[Your Full Name]", "[Your Address]", "[Your Phone Number]", "[Your Social Insurance Number]").
4. The subject line MUST be specific to their actual request.
5. Write the email in the FIRST PERSON (use "I", "me", "my") as if you are the applicant.
6. Write a COMPLETE email ready to copy and send (with placeholders where needed).

IMPORTANT: Output ONLY the email itself. Do NOT include any introduction, preamble, or explanation like "Here is the email" or "Of course". Start directly with "To:" or "Subject:"."""

        try:
            email_draft = get_llm_response(email_prompt, temperature=0.3)
            trace_messages.append("Generated email draft")
        except Exception as e:
            email_draft = f"[Email draft generation failed: {e}]"
            trace_messages.append(f"Email generation error: {e}")
    else:
        trace_messages.append("Skipped email draft generation (not selected)")

    # 3. Generate Meeting Prep Summary - only if 'meeting' mode selected
    meeting_prep = ""
    if "meeting" in selected_modes:
        lang_instruction = get_language_instruction(language) if "email" not in selected_modes else lang_instruction

        meeting_prompt = f"""You are AccessBridge, helping users prepare for meetings with government officials.

{lang_instruction}

USER'S REQUEST OR GOAL: {user_intent if user_intent else "General inquiry about " + program_type + " services"}

PROGRAM TYPE: {program_type}

APPLICANT'S INFORMATION:
{json.dumps(extracted_fields, indent=2)}

INFORMATION GAPS:
{json.dumps(information_gaps, indent=2)}

TASK: Create a meeting preparation document tailored to their specific request.

CRITICAL RULES:
1. NEVER use placeholder text like "[Replace This]", "[Your Topic]", etc.
2. Use ONLY actual values from the applicant's information
3. If info is missing, say "to be confirmed" or simply omit
4. Be SPECIFIC to their actual request - if they asked about "Disability EI documents", the prep should be about that

FORMAT: Use plain text only. No markdown. Use ALL CAPS for section headers, simple dashes for bullet points.

Create a structured document with these sections:

MEETING OBJECTIVE
(What the user wants to accomplish - state their specific goal)

KEY POINTS TO DISCUSS
(3-5 bullet points directly relevant to their request)

DOCUMENTS TO BRING
(Based on {program_type} program and their specific request - be specific, e.g., "ROE from employer", "Medical certificate for disability claim")

QUESTIONS TO ASK THE OFFICER
(2-3 questions that will help them achieve their goal)

INFORMATION TO PREPARE
(Any gaps they should be ready to fill in)

Make this actionable and specific to their situation.

IMPORTANT: Output ONLY the meeting preparation document. Do NOT include any introduction, preamble, or explanation. Start directly with the first section header."""

        try:
            meeting_prep = get_llm_response(meeting_prompt, temperature=0.3)
            trace_messages.append("Generated meeting preparation summary")
        except Exception as e:
            meeting_prep = f"[Meeting prep generation failed: {e}]"
            trace_messages.append(f"Meeting prep error: {e}")
    else:
        trace_messages.append("Skipped meeting prep generation (not selected)")

    # Determine completion status
    critical_gaps = [g for g in information_gaps if g.get("priority") == "critical"]
    if not information_gaps:
        completion_status = "complete"
    elif not critical_gaps:
        completion_status = "ready_for_review"
    else:
        completion_status = "needs_input"

    trace_messages.append(f"Output generation complete. Status: {completion_status}")

    return {
        "current_step": "complete",
        "form_data": form_data,
        "email_draft": email_draft,
        "meeting_prep": meeting_prep,
        "overall_confidence": round(overall_confidence, 2),
        "completion_status": completion_status,
        "trace_log": trace_messages,
    }
