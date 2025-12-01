"""
Forms router - PDF form field extraction, filling, and auto-mapping endpoints.
"""

import base64
import json
import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException
import google.generativeai as genai

from api.schemas import FormExtractRequest, FormFillRequest, FormAutoFillRequest
from services.pdf_form_service import (
    extract_form_fields,
    extract_form_fields_grouped,
    fill_pdf_form,
    get_form_summary,
    fields_to_dict,
    field_groups_to_dict
)
from core.model_state import model_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/form", tags=["Forms"])


@router.post("/extract-fields")
async def extract_fields(req: FormExtractRequest):
    """
    Extract all fillable fields from a PDF form.

    Returns:
    - fields: Standalone fields (text inputs, etc.)
    - field_groups: Grouped fields (checkboxes, radio buttons, dropdowns with options)
    - Each group has group_label, group_type, and options array
    """
    try:
        # Decode base64 PDF
        pdf_bytes = base64.b64decode(req.pdf_base64)

        # Get form summary
        summary = get_form_summary(pdf_bytes)

        # Extract fields with grouping
        standalone_fields, field_groups = extract_form_fields_grouped(pdf_bytes)
        fields_data = fields_to_dict(standalone_fields)
        groups_data = field_groups_to_dict(field_groups)

        # Total field count includes both standalone and grouped
        total_options = sum(len(g.get("options", [])) for g in groups_data)
        total_count = len(fields_data) + total_options

        return {
            "form_name": summary["form_name"],
            "page_count": summary["page_count"],
            "field_count": total_count,
            "field_types": summary["field_types"],
            "has_required_fields": summary["has_required_fields"],
            "fields": fields_data,
            "field_groups": groups_data  # NEW: grouped checkbox/radio/dropdown fields
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Form field extraction error")
        raise HTTPException(
            status_code=500,
            detail="An error occurred during form field extraction."
        )


@router.post("/fill")
async def fill_form(req: FormFillRequest):
    """
    Fill a PDF form with provided field values.

    Returns the filled PDF as base64.
    """
    try:
        # Decode base64 PDF
        pdf_bytes = base64.b64decode(req.pdf_base64)

        # Fill the form
        filled_pdf = fill_pdf_form(
            pdf_bytes,
            req.field_values,
            flatten=req.flatten
        )

        # Encode result as base64
        filled_base64 = base64.b64encode(filled_pdf).decode('utf-8')

        return {
            "filled_pdf_base64": filled_base64,
            "fields_filled": len(req.field_values),
            "flattened": req.flatten
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Form filling error")
        raise HTTPException(
            status_code=500,
            detail="An error occurred during form filling."
        )


@router.post("/auto-fill")
async def auto_fill_form(req: FormAutoFillRequest):
    """
    Auto-fill a PDF form by mapping extracted data to form fields using LLM.

    1. Extracts form field metadata from PDF
    2. Uses LLM to intelligently map extracted data to form fields
    3. Fills the form with mapped values
    4. Returns filled PDF and mapping details
    """
    try:
        # Decode base64 PDF
        pdf_bytes = base64.b64decode(req.pdf_base64)

        # Extract form fields
        fields = extract_form_fields(pdf_bytes)
        if not fields:
            raise ValueError("PDF does not contain any fillable form fields")

        fields_data = fields_to_dict(fields)

        # Prepare data for LLM mapping
        form_fields_summary = [
            {
                "name": f["name"],
                "label": f["label"],
                "type": f["type"],
                "options": f.get("options")
            }
            for f in fields_data
        ]

        # Prepare extracted data summary
        extracted_summary = {}
        for key, val in req.extracted_data.items():
            if isinstance(val, dict):
                extracted_summary[key] = val.get("value", val)
            else:
                extracted_summary[key] = val

        # Use LLM to map extracted data to form fields
        model_config.ensure_configured()
        model = genai.GenerativeModel(model_config.get_model("fast"))

        lang_instruction = "Respond in French." if req.language == "fr" else "Respond in English."

        prompt = f"""You are a form-filling assistant. Map the extracted user data to PDF form fields.

{lang_instruction}

EXTRACTED USER DATA:
{json.dumps(extracted_summary, indent=2, ensure_ascii=False)}

PDF FORM FIELDS:
{json.dumps(form_fields_summary, indent=2, ensure_ascii=False)}

INSTRUCTIONS:
1. Match extracted data to the most appropriate form fields
2. Split names into first/last if the form has separate fields
3. Format dates according to the field's expected format (usually YYYY-MM-DD)
4. For dropdown/radio fields, match to the closest available option
5. Only map data that was actually extracted - do not invent values
6. Leave fields as null if no matching data exists

Return a JSON object with this exact structure:
{{
  "field_mapping": {{
    "field_name_1": "value_to_fill",
    "field_name_2": "value_to_fill"
  }},
  "unmapped_fields": ["field_name_3", "field_name_4"],
  "unused_data": ["extracted_key_1", "extracted_key_2"]
}}

IMPORTANT: Return ONLY the JSON object, no markdown formatting or explanation."""

        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.1}
        )

        # Parse LLM response
        response_text = response.text.strip()
        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()

        try:
            mapping_result = json.loads(response_text)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse LLM response: {response_text}")
            raise ValueError("Failed to parse field mapping from LLM")

        field_mapping = mapping_result.get("field_mapping", {})
        unmapped_fields = mapping_result.get("unmapped_fields", [])
        unused_data = mapping_result.get("unused_data", [])

        # Filter out null/empty values
        field_values = {k: v for k, v in field_mapping.items() if v is not None and v != ""}

        # Fill the form
        filled_pdf = fill_pdf_form(pdf_bytes, field_values)
        filled_base64 = base64.b64encode(filled_pdf).decode('utf-8')

        # Build response with confidence info
        field_mapping_with_confidence = {}
        for field_name, value in field_values.items():
            # Find which extracted field this value came from
            source_key = None
            confidence = 1.0
            for ext_key, ext_val in req.extracted_data.items():
                if isinstance(ext_val, dict):
                    if str(ext_val.get("value", "")) in str(value) or str(value) in str(ext_val.get("value", "")):
                        source_key = ext_key
                        confidence = ext_val.get("confidence", 1.0)
                        break
                elif str(ext_val) in str(value) or str(value) in str(ext_val):
                    source_key = ext_key
                    break

            field_mapping_with_confidence[field_name] = {
                "value": value,
                "source": source_key,
                "confidence": confidence
            }

        return {
            "filled_pdf_base64": filled_base64,
            "field_mapping": field_mapping_with_confidence,
            "fields_filled": len(field_values),
            "unmapped_fields": unmapped_fields,
            "unused_data": unused_data
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Auto-fill error")
        raise HTTPException(
            status_code=500,
            detail="An error occurred during auto-fill."
        )
