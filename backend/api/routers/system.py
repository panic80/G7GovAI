"""
System router - Health checks, model configuration, and utility endpoints.
"""

import logging
import base64
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict
import google.generativeai as genai

from services.llm_service import LLMService
from api.schemas import GenerateRequest, TTSRequest, AuditLog, OcrRequest, SttRequest, TranslateRequest, ModelConfigUpdate, ApiKeyUpdate
from core.model_state import model_config
from core.config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

# Configure Gemini at startup if API key available
model_config.ensure_configured()

router = APIRouter()
script_dir = Path(__file__).resolve().parent.parent.parent  # backend/


def get_llm_service():
    return LLMService()


@router.get("/health")
def health_check():
    """Health check endpoint - publicly accessible."""
    return {"status": "ok", "service": "GovAI RAG Backend"}


@router.get("/config/models")
def get_model_config():
    """Get current LLM model configuration."""
    return model_config.get_all()


@router.get("/config/available-models")
def get_available_models(model_type: str = "all"):
    """
    Fetch available Gemini models from the API.

    Args:
        model_type: "reasoning" (pro/flash), "fast" (flash only), or "all"
    """
    try:
        models = []
        for m in genai.list_models():
            model_id = m.name.replace("models/", "")

            # Skip non-gemini or old versions
            if not model_id.startswith("gemini-"):
                continue

            # Skip unwanted models (nano, image, experimental variants)
            skip_keywords = ["nano", "image", "embedding", "aqa", "exp-", "-exp", "thinking"]
            if any(kw in model_id.lower() for kw in skip_keywords):
                continue

            # Only include models that support generateContent
            if "generateContent" not in m.supported_generation_methods:
                continue

            # Filter based on model_type
            if model_type == "fast":
                # Fast: only 2.5 flash models
                if "2.5-flash" not in model_id:
                    continue
            elif model_type == "reasoning":
                # Reasoning: 2.5-pro, 3-pro, or 2.5-flash (no lite, no nano)
                valid = any(v in model_id for v in ["2.5-pro", "3-pro", "2.5-flash"])
                if not valid or "lite" in model_id:
                    continue
            else:
                # All: gemini 2.0, 2.5, 3 only
                if not any(v in model_id for v in ["gemini-2.0", "gemini-2.5", "gemini-3"]):
                    continue

            models.append({
                "id": model_id,
                "displayName": getattr(m, "display_name", model_id)
            })

        # Sort by version (newest first)
        models.sort(key=lambda x: x["id"], reverse=True)
        return {"models": models}
    except Exception as e:
        logger.exception("Failed to fetch available models")
        # Fallback to hardcoded list based on type
        if model_type == "fast":
            return {"models": [
                {"id": "gemini-2.5-flash-lite", "displayName": "Gemini 2.5 Flash-Lite"},
                {"id": "gemini-2.5-flash", "displayName": "Gemini 2.5 Flash"},
            ]}
        elif model_type == "reasoning":
            return {"models": [
                {"id": "gemini-3-pro-preview", "displayName": "Gemini 3 Pro Preview"},
                {"id": "gemini-2.5-pro", "displayName": "Gemini 2.5 Pro"},
                {"id": "gemini-2.5-flash", "displayName": "Gemini 2.5 Flash"},
            ]}
        return {"models": [
            {"id": "gemini-3-pro-preview", "displayName": "Gemini 3 Pro Preview"},
            {"id": "gemini-2.5-pro", "displayName": "Gemini 2.5 Pro"},
            {"id": "gemini-2.5-flash", "displayName": "Gemini 2.5 Flash"},
            {"id": "gemini-2.5-flash-lite", "displayName": "Gemini 2.5 Flash-Lite"},
        ]}


@router.post("/config/models")
def update_model_config(config: ModelConfigUpdate):
    """Update LLM model configuration."""
    if config.fast:
        model_config.set_model("fast", config.fast)
    if config.reasoning:
        model_config.set_model("reasoning", config.reasoning)
    if config.vision:
        model_config.set_model("vision", config.vision)
    if config.audio:
        model_config.set_model("audio", config.audio)
    if config.tts:
        model_config.set_model("tts", config.tts)
    return {"status": "updated", "config": model_config.get_all()}


@router.get("/config/api-key")
def get_api_key_status():
    """Check if an API key is configured (custom or default)."""
    return {
        "api_key_configured": model_config.is_configured(),
        "has_custom_key": model_config.has_custom_api_key(),
        "key_preview": model_config.get_api_key()[:8] + "..." if model_config.get_api_key() else None
    }


@router.post("/config/api-key")
def update_api_key(config: ApiKeyUpdate):
    """Set a custom API key (empty string to clear and use default)."""
    model_config.set_api_key(config.api_key if config.api_key else None)
    # Reconfigure genai with the new key
    model_config.ensure_configured()
    return {
        "status": "updated",
        "api_key_configured": model_config.is_configured(),
        "has_custom_key": model_config.has_custom_api_key()
    }


@router.post("/audit")
async def log_audit(log: AuditLog):
    """Log an audit entry."""
    try:
        log_entry = log.model_dump_json()
        audit_file = script_dir / "audit_logs.jsonl"
        with open(audit_file, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
        return {"status": "logged"}
    except Exception as e:
        logger.exception("Audit logging error")
        return {"status": "error", "detail": "Failed to write audit log"}


@router.post("/generate")
async def generate_content(
    req: GenerateRequest,
    service: LLMService = Depends(get_llm_service)
):
    """Generate content using LLM."""
    try:
        text = service.generate_content(
            prompt=req.prompt,
            model_name=req.model_name,
            temperature=req.temperature,
            schema=req.response_schema,
            history=req.history,
            context=req.context
        )
        return {"text": text}
    except Exception as e:
        logger.exception("Content generation error")
        raise HTTPException(
            status_code=500,
            detail="An error occurred during content generation."
        )


@router.post("/tts")
async def generate_speech(
    req: TTSRequest,
    service: LLMService = Depends(get_llm_service)
):
    """Generate speech from text using TTS."""
    try:
        audio_b64 = service.generate_speech(
            text=req.text,
            language=req.language,
            model_name=req.model_name
        )
        return {"audio_base64": audio_b64}
    except Exception as e:
        logger.exception("Text-to-speech error")
        raise HTTPException(
            status_code=500,
            detail="An error occurred during speech generation."
        )


# =============================================================================
# AccessBridge: OCR and STT Endpoints
# =============================================================================

@router.post("/ocr")
async def perform_ocr(req: OcrRequest):
    """
    Perform OCR on an uploaded document using Gemini Vision.

    Supports: PDF, PNG, JPG, JPEG
    Returns: Extracted text content
    """
    try:
        if not GEMINI_API_KEY:
            raise HTTPException(
                status_code=500,
                detail="OCR service is not configured"
            )

        # Decode base64 file
        file_bytes = base64.b64decode(req.file_base64)

        # Map file types to MIME types
        mime_types = {
            "pdf": "application/pdf",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
        }
        mime_type = mime_types.get(req.file_type.lower(), "application/pdf")

        # Use Gemini Vision for OCR
        model = genai.GenerativeModel(model_config.get_model("vision"))

        # Create file part for vision
        file_part = {
            "mime_type": mime_type,
            "data": file_bytes
        }

        # Language-specific prompt
        lang_hint = "French" if req.language == "fr" else "English"
        prompt = f"""Extract ALL text content from this document.

The document is likely in {lang_hint}.
Preserve the structure and formatting as much as possible.
Include all visible text, numbers, dates, and labels.
If there are forms, extract field names and their values.

Return ONLY the extracted text, no commentary."""

        response = model.generate_content([prompt, file_part])
        extracted_text = response.text

        return {"text": extracted_text, "language": req.language}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("OCR processing error")
        raise HTTPException(
            status_code=500,
            detail="An error occurred during OCR processing."
        )


@router.post("/stt")
async def speech_to_text(req: SttRequest):
    """
    Perform Speech-to-Text on uploaded audio using Gemini.

    Supports: WAV, MP3, WEBM, OGG, M4A
    Returns: Transcribed text
    """
    try:
        if not GEMINI_API_KEY:
            raise HTTPException(
                status_code=500,
                detail="Speech-to-text service is not configured"
            )

        # Decode base64 audio
        audio_bytes = base64.b64decode(req.audio_base64)

        # Map audio formats to MIME types
        mime_types = {
            "wav": "audio/wav",
            "mp3": "audio/mp3",
            "webm": "audio/webm",
            "ogg": "audio/ogg",
            "m4a": "audio/mp4",
        }
        mime_type = mime_types.get(req.audio_format.lower(), "audio/wav")

        # Use Gemini for transcription
        model = genai.GenerativeModel(model_config.get_model("audio"))

        # Create audio part
        audio_part = {
            "mime_type": mime_type,
            "data": audio_bytes
        }

        # Language-specific prompt
        lang_hint = "French" if req.language == "fr" else "English"
        prompt = f"""Transcribe this audio recording accurately.

The speaker is likely speaking in {lang_hint}.
Include all spoken words, numbers, and proper nouns.
Preserve natural speech patterns but clean up filler words.

Return ONLY the transcription, no timestamps or commentary."""

        response = model.generate_content([prompt, audio_part])
        transcription = response.text

        return {"text": transcription, "language": req.language}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Speech-to-text error")
        raise HTTPException(
            status_code=500,
            detail="An error occurred during speech-to-text processing."
        )


# =============================================================================
# Translation Endpoint for Dynamic Multilingual Support
# =============================================================================

# Language name mapping for translation prompts
LANGUAGE_NAMES = {
    "en": "English",
    "fr": "French",
    "es": "Spanish",
    "zh": "Chinese (Simplified)",
    "ar": "Arabic",
    "pa": "Punjabi",
    "tl": "Tagalog",
    "hi": "Hindi",
    "ko": "Korean",
    "vi": "Vietnamese",
    "pt": "Portuguese",
    "de": "German",
    "it": "Italian",
    "ja": "Japanese",
    "ru": "Russian",
}


@router.post("/translate")
async def translate_texts(req: TranslateRequest):
    """
    Translate multiple texts using LLM.

    Supports dynamic translation to any language using Gemini.
    Returns a mapping of original text -> translated text.
    """
    try:
        model_config.ensure_configured()

        # Get language names for better prompts
        source_lang_name = LANGUAGE_NAMES.get(req.source_language, req.source_language)
        target_lang_name = LANGUAGE_NAMES.get(req.target_language, req.target_language)

        # If source and target are the same, return originals
        if req.source_language == req.target_language:
            return {"translations": {text: text for text in req.texts}}

        # Use fast model for translations
        model = genai.GenerativeModel(model_config.get_model("fast"))

        # Build translation prompt for batch processing
        texts_formatted = "\n".join([f"[{i+1}] {text}" for i, text in enumerate(req.texts)])

        prompt = f"""Translate the following texts from {source_lang_name} to {target_lang_name}.

These are UI strings for a government services application.
Maintain professional, formal language appropriate for government communications.
Keep translations concise and natural in the target language.

IMPORTANT:
- Return ONLY the translations, numbered to match the input
- Preserve any placeholders like {{name}} or %s
- Keep technical terms accurate
- Do not add explanations

Input texts:
{texts_formatted}

Translations (in {target_lang_name}):"""

        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.1}
        )

        # Parse the response to extract translations
        translations = {}
        response_lines = response.text.strip().split("\n")

        for i, text in enumerate(req.texts):
            # Try to find the corresponding translation
            for line in response_lines:
                # Match numbered format like "[1] translated text" or "1. translated text"
                if line.strip().startswith(f"[{i+1}]"):
                    translated = line.strip()[len(f"[{i+1}]"):].strip()
                    translations[text] = translated
                    break
                elif line.strip().startswith(f"{i+1}."):
                    translated = line.strip()[len(f"{i+1}."):].strip()
                    translations[text] = translated
                    break
                elif line.strip().startswith(f"{i+1})"):
                    translated = line.strip()[len(f"{i+1})"):].strip()
                    translations[text] = translated
                    break

            # Fallback: if no match found, use original
            if text not in translations:
                # Try to use response lines in order if parsing failed
                if i < len(response_lines):
                    # Remove any numbering prefix
                    cleaned = response_lines[i].strip()
                    for prefix in [f"[{i+1}]", f"{i+1}.", f"{i+1})"]:
                        if cleaned.startswith(prefix):
                            cleaned = cleaned[len(prefix):].strip()
                            break
                    translations[text] = cleaned if cleaned else text
                else:
                    translations[text] = text

        return {"translations": translations}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Translation error")
        raise HTTPException(
            status_code=500,
            detail="An error occurred during translation."
        )
