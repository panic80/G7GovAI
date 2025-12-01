"""
PDF Form Service - Extract and fill PDF form fields (AcroForms)

This service handles:
1. Extracting form field metadata from fillable PDFs
2. Filling PDF forms with provided values
3. Generating filled PDFs for download
"""

import io
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import re

from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, TextStringObject, ArrayObject

logger = logging.getLogger(__name__)


class FieldType(str, Enum):
    """Types of PDF form fields."""
    TEXT = "text"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    DROPDOWN = "dropdown"
    SIGNATURE = "signature"
    BUTTON = "button"
    UNKNOWN = "unknown"


@dataclass
class FormField:
    """Represents a single form field in a PDF."""
    name: str
    field_type: FieldType
    label: Optional[str] = None
    value: Optional[str] = None
    options: Optional[List[str]] = None
    required: bool = False
    max_length: Optional[int] = None
    page: int = 0


@dataclass
class FormFieldGroup:
    """Represents a group of related fields (radio buttons, checkboxes under one question)."""
    group_name: str           # Technical name (e.g., "MaritalStatus")
    group_label: str          # Human-readable question (e.g., "What is your marital status?")
    group_type: str           # "radio" (single select), "checkbox" (multi-select), or "dropdown"
    options: List[Dict[str, str]] = field(default_factory=list)  # [{name: "field_name", label: "Display Label"}, ...]
    required: bool = False
    page: int = 0


def _determine_field_type(field: Dict[str, Any]) -> FieldType:
    """Determine the type of a PDF form field from its properties."""
    ft = field.get("/FT")

    if ft == "/Tx":
        return FieldType.TEXT
    elif ft == "/Btn":
        # Check if checkbox or radio
        ff = field.get("/Ff", 0)
        if isinstance(ff, int):
            # Bit 16 (0x10000) indicates radio button
            if ff & 0x10000:
                return FieldType.RADIO
            # Bit 17 (0x20000) indicates pushbutton
            elif ff & 0x20000:
                return FieldType.BUTTON
            else:
                return FieldType.CHECKBOX
        return FieldType.CHECKBOX
    elif ft == "/Ch":
        return FieldType.DROPDOWN
    elif ft == "/Sig":
        return FieldType.SIGNATURE
    else:
        return FieldType.UNKNOWN


def _extract_field_label(field: Dict[str, Any], field_name: str) -> str:
    """Extract a human-readable label for a form field."""
    # Try to get the tooltip (TU) or alternate name
    label = field.get("/TU")  # Tooltip
    if label:
        return str(label)

    # Try to get the field's text content for context
    label = field.get("/T")  # Field name
    if label:
        return str(label)

    # Fall back to cleaning up the field name
    # Convert "form1[0].Page1[0].GivenName[0]" to "Given Name"
    clean_name = field_name
    # Remove array indices
    import re
    clean_name = re.sub(r'\[\d+\]', '', clean_name)
    # Take the last part after dots
    if '.' in clean_name:
        clean_name = clean_name.split('.')[-1]
    # Add spaces before capital letters
    clean_name = re.sub(r'([a-z])([A-Z])', r'\1 \2', clean_name)

    return clean_name


def _get_field_options(field: Dict[str, Any]) -> Optional[List[str]]:
    """Extract options for dropdown/radio fields."""
    options = field.get("/Opt")
    if options:
        if isinstance(options, ArrayObject):
            return [str(opt) for opt in options]
        return [str(options)]
    return None


def extract_form_fields(pdf_bytes: bytes) -> List[FormField]:
    """
    Extract all fillable fields from a PDF AcroForm.

    Args:
        pdf_bytes: The PDF file content as bytes

    Returns:
        List of FormField objects representing each fillable field
    """
    fields: List[FormField] = []

    try:
        pdf_stream = io.BytesIO(pdf_bytes)
        reader = PdfReader(pdf_stream)

        # Check if the PDF has form fields
        if reader.get_fields() is None:
            logger.warning("PDF does not contain any form fields")
            return []

        form_fields = reader.get_fields()

        for field_name, field_data in form_fields.items():
            try:
                # Get field properties
                field_type = _determine_field_type(field_data)

                # Skip non-fillable field types
                if field_type in [FieldType.BUTTON, FieldType.SIGNATURE]:
                    continue

                # Extract label
                label = _extract_field_label(field_data, field_name)

                # Get current value if any
                value = field_data.get("/V")
                if value:
                    value = str(value)

                # Get options for dropdowns/radios
                options = _get_field_options(field_data)

                # Check if required (Ff bit 2)
                ff = field_data.get("/Ff", 0)
                required = bool(isinstance(ff, int) and ff & 0x2)

                # Get max length for text fields
                max_length = field_data.get("/MaxLen")
                if max_length:
                    max_length = int(max_length)

                # Determine page number
                page = 0
                if "/P" in field_data:
                    # Try to determine page from parent reference
                    try:
                        for i, p in enumerate(reader.pages):
                            if field_data.get("/P") == p:
                                page = i
                                break
                    except Exception as e:
                        logger.debug(f"Could not determine page for field {field_name}: {e}")

                field = FormField(
                    name=field_name,
                    field_type=field_type,
                    label=label,
                    value=value,
                    options=options,
                    required=required,
                    max_length=max_length,
                    page=page
                )
                fields.append(field)

            except Exception as e:
                logger.warning(f"Error processing field {field_name}: {e}")
                continue

        logger.info(f"Extracted {len(fields)} form fields from PDF")
        return fields

    except Exception as e:
        logger.exception(f"Error extracting form fields: {e}")
        raise ValueError(f"Failed to extract form fields: {str(e)}")


def fill_pdf_form(
    pdf_bytes: bytes,
    field_values: Dict[str, str],
    flatten: bool = False
) -> bytes:
    """
    Fill a PDF form with provided values.

    Args:
        pdf_bytes: The PDF file content as bytes
        field_values: Dictionary mapping field names to values
        flatten: If True, flatten the form (make fields non-editable)

    Returns:
        The filled PDF as bytes
    """
    try:
        pdf_stream = io.BytesIO(pdf_bytes)
        reader = PdfReader(pdf_stream)
        writer = PdfWriter()

        # CRITICAL: Clone the entire document including AcroForm structure
        # Previously we used add_page() which doesn't copy the form structure
        writer.clone_document_from_reader(reader)

        # Get the form fields
        if reader.get_fields() is None:
            raise ValueError("PDF does not contain any form fields")

        # Update field values - iterate through all pages
        fields_filled = 0
        for field_name, value in field_values.items():
            if value is not None and value != "":
                try:
                    # Update field on all pages (some forms span multiple pages)
                    for page_num, page in enumerate(writer.pages):
                        try:
                            writer.update_page_form_field_values(
                                page,
                                {field_name: value}
                            )
                        except Exception as e:
                            # Field might not exist on this page, try next
                            logger.debug(f"Field {field_name} not on page {page_num}: {e}")
                            continue
                    fields_filled += 1
                except Exception as e:
                    logger.warning(f"Could not fill field {field_name}: {e}")

        logger.info(f"Filled {fields_filled} fields in PDF form")

        # Write to output stream
        output_stream = io.BytesIO()
        writer.write(output_stream)
        output_stream.seek(0)

        return output_stream.read()

    except Exception as e:
        logger.exception(f"Error filling PDF form: {e}")
        raise ValueError(f"Failed to fill PDF form: {str(e)}")


def get_form_summary(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    Get a summary of the form including field count and types.

    Args:
        pdf_bytes: The PDF file content as bytes

    Returns:
        Dictionary with form summary information
    """
    try:
        pdf_stream = io.BytesIO(pdf_bytes)
        reader = PdfReader(pdf_stream)

        # Try to extract form name from metadata
        form_name = "Unknown Form"
        if reader.metadata:
            if reader.metadata.title:
                form_name = reader.metadata.title
            elif reader.metadata.subject:
                form_name = reader.metadata.subject

        fields = extract_form_fields(pdf_bytes)

        # Count by type
        type_counts = {}
        for field in fields:
            field_type = field.field_type.value
            type_counts[field_type] = type_counts.get(field_type, 0) + 1

        return {
            "form_name": form_name,
            "page_count": len(reader.pages),
            "field_count": len(fields),
            "field_types": type_counts,
            "has_required_fields": any(f.required for f in fields)
        }

    except Exception as e:
        logger.exception(f"Error getting form summary: {e}")
        raise ValueError(f"Failed to get form summary: {str(e)}")


def fields_to_dict(fields: List[FormField]) -> List[Dict[str, Any]]:
    """Convert FormField objects to dictionaries for JSON serialization."""
    return [
        {
            "name": f.name,
            "type": f.field_type.value,
            "label": f.label,
            "value": f.value,
            "options": f.options,
            "required": f.required,
            "max_length": f.max_length,
            "page": f.page
        }
        for f in fields
    ]


def _extract_parent_name(field_name: str) -> Optional[str]:
    """
    Extract parent/group name from a field name using common PDF naming patterns.

    Patterns recognized:
    - "Parent.Child" -> "Parent"
    - "Parent[0]" -> "Parent"
    - "form1[0].Page1[0].MaritalStatus[0].Single[0]" -> "MaritalStatus"
    - "Q5_Option1" -> "Q5"
    - "MaritalStatusSingle" -> "MaritalStatus" (heuristic based on camelCase)

    Returns None if no parent pattern detected.
    """
    # Remove array indices
    clean_name = re.sub(r'\[\d+\]', '', field_name)

    # Pattern 1: Dot-separated hierarchy (take second-to-last part)
    if '.' in clean_name:
        parts = clean_name.split('.')
        # If there are at least 2 non-empty parts, use second-to-last as parent
        non_empty = [p for p in parts if p]
        if len(non_empty) >= 2:
            return non_empty[-2]

    # Pattern 2: Underscore-separated (e.g., "Q5_Option1" -> "Q5")
    if '_' in clean_name:
        parts = clean_name.split('_')
        if len(parts) >= 2:
            return parts[0]

    # Pattern 3: CamelCase with common option suffixes
    option_patterns = [
        r'^(.+?)(Single|Married|Divorced|Widowed|Yes|No|True|False|Male|Female|Option\d+|Choice\d+)$',
        r'^(.+?)([A-Z][a-z]+)$',  # Generic camelCase split at last capital
    ]
    for pattern in option_patterns:
        match = re.match(pattern, clean_name, re.IGNORECASE)
        if match:
            potential_parent = match.group(1)
            # Only use if parent is reasonably sized (not just a single char)
            if len(potential_parent) >= 2:
                return potential_parent

    return None


def _clean_option_label(option_name: str, parent_name: str) -> str:
    """
    Extract a clean option label by removing the parent prefix.

    "MaritalStatus.Single" with parent "MaritalStatus" -> "Single"
    "Q5_OptionA" with parent "Q5" -> "OptionA" -> "Option A"
    """
    # Remove parent prefix and any separators
    label = option_name

    # Remove array indices
    label = re.sub(r'\[\d+\]', '', label)

    # Remove parent prefix (with various separators)
    patterns = [
        f'^{re.escape(parent_name)}\\.',
        f'^{re.escape(parent_name)}_',
        f'^{re.escape(parent_name)}',
    ]
    for pattern in patterns:
        label = re.sub(pattern, '', label, flags=re.IGNORECASE)

    # Take last part after dots
    if '.' in label:
        label = label.split('.')[-1]

    # Add spaces to camelCase
    label = re.sub(r'([a-z])([A-Z])', r'\1 \2', label)

    # Clean up underscores
    label = label.replace('_', ' ')

    return label.strip() or option_name


def _make_group_label(parent_name: str, group_type: str) -> str:
    """
    Generate a human-readable question label for a field group.
    """
    # Clean up the parent name
    clean = re.sub(r'\[\d+\]', '', parent_name)
    if '.' in clean:
        clean = clean.split('.')[-1]

    # Add spaces to camelCase
    clean = re.sub(r'([a-z])([A-Z])', r'\1 \2', clean)
    clean = clean.replace('_', ' ')
    clean = clean.strip()

    # Add appropriate suffix based on type
    if group_type == 'checkbox':
        return f"{clean} (select all that apply)"
    else:
        return clean


def extract_form_fields_grouped(pdf_bytes: bytes) -> Tuple[List[FormField], List[FormFieldGroup]]:
    """
    Extract form fields, grouping related checkboxes/radios together.

    This function identifies fields that belong together (like radio button groups
    or checkbox groups) and returns them as FormFieldGroup objects, while keeping
    standalone fields (like text inputs) as regular FormField objects.

    Args:
        pdf_bytes: The PDF file content as bytes

    Returns:
        Tuple of (standalone_fields, field_groups)
    """
    standalone_fields: List[FormField] = []
    groups: Dict[str, List[FormField]] = defaultdict(list)
    group_types: Dict[str, FieldType] = {}

    try:
        pdf_stream = io.BytesIO(pdf_bytes)
        reader = PdfReader(pdf_stream)

        if reader.get_fields() is None:
            logger.warning("PDF does not contain any form fields")
            return [], []

        form_fields = reader.get_fields()

        for field_name, field_data in form_fields.items():
            try:
                field_type = _determine_field_type(field_data)

                # Skip non-fillable types
                if field_type in [FieldType.BUTTON, FieldType.SIGNATURE]:
                    continue

                # Extract common field properties
                label = _extract_field_label(field_data, field_name)
                value = field_data.get("/V")
                if value:
                    value = str(value)
                options = _get_field_options(field_data)

                ff = field_data.get("/Ff", 0)
                required = bool(isinstance(ff, int) and ff & 0x2)

                max_length = field_data.get("/MaxLen")
                if max_length:
                    max_length = int(max_length)

                page = 0
                if "/P" in field_data:
                    try:
                        for i, p in enumerate(reader.pages):
                            if field_data.get("/P") == p:
                                page = i
                                break
                    except Exception as e:
                        logger.debug(f"Could not determine page for field {field_name}: {e}")

                field = FormField(
                    name=field_name,
                    field_type=field_type,
                    label=label,
                    value=value,
                    options=options,
                    required=required,
                    max_length=max_length,
                    page=page
                )

                # Decide if this should be grouped
                if field_type in [FieldType.CHECKBOX, FieldType.RADIO]:
                    # Try to detect parent group
                    parent = _extract_parent_name(field_name)

                    # Also check for /Parent key in field data (PDF-native grouping)
                    if parent is None and "/Parent" in field_data:
                        parent_obj = field_data.get("/Parent")
                        if hasattr(parent_obj, "get") and "/T" in parent_obj:
                            parent = str(parent_obj.get("/T"))

                    if parent:
                        groups[parent].append(field)
                        # Track the group type (prefer radio if any field is radio)
                        if parent not in group_types or field_type == FieldType.RADIO:
                            group_types[parent] = field_type
                    else:
                        # No parent detected, treat as standalone
                        standalone_fields.append(field)

                elif field_type == FieldType.DROPDOWN:
                    # Dropdowns with options are inherently grouped (one question, multiple options)
                    # But they're a single field, so we convert them to a group format
                    if options and len(options) > 1:
                        group = FormFieldGroup(
                            group_name=field_name,
                            group_label=label,
                            group_type="dropdown",
                            options=[{"name": field_name, "label": opt} for opt in options],
                            required=required,
                            page=page
                        )
                        # Add as a group (we'll collect these separately)
                        groups[f"_dropdown_{field_name}"] = [field]
                        group_types[f"_dropdown_{field_name}"] = FieldType.DROPDOWN
                    else:
                        standalone_fields.append(field)
                else:
                    # Text and other fields are standalone
                    standalone_fields.append(field)

            except Exception as e:
                logger.warning(f"Error processing field {field_name}: {e}")
                continue

        # Convert grouped fields to FormFieldGroup objects
        field_groups: List[FormFieldGroup] = []

        for parent_name, fields_in_group in groups.items():
            if len(fields_in_group) < 2 and not parent_name.startswith("_dropdown_"):
                # Groups with only 1 field are probably not real groups
                standalone_fields.extend(fields_in_group)
                continue

            # Handle dropdowns specially
            if parent_name.startswith("_dropdown_"):
                actual_field = fields_in_group[0]
                if actual_field.options:
                    group = FormFieldGroup(
                        group_name=actual_field.name,
                        group_label=actual_field.label or actual_field.name,
                        group_type="dropdown",
                        options=[{"name": actual_field.name, "label": opt} for opt in actual_field.options],
                        required=actual_field.required,
                        page=actual_field.page
                    )
                    field_groups.append(group)
                continue

            # Determine group type
            gtype = group_types.get(parent_name, FieldType.CHECKBOX)
            group_type_str = "radio" if gtype == FieldType.RADIO else "checkbox"

            # Generate group label
            group_label = _make_group_label(parent_name, group_type_str)

            # Check if any field has a tooltip that could be the question
            for f in fields_in_group:
                # If a field's label looks like a question, use it for the group
                if f.label and ('?' in f.label or len(f.label) > 30):
                    group_label = f.label
                    break

            # Build options list
            options = []
            any_required = False
            min_page = 0

            for f in fields_in_group:
                option_label = _clean_option_label(f.name, parent_name)
                # Also try using the field's own label if it's short and descriptive
                if f.label and len(f.label) < 30 and f.label.lower() != option_label.lower():
                    option_label = f.label

                options.append({
                    "name": f.name,
                    "label": option_label
                })

                if f.required:
                    any_required = True
                if f.page < min_page or min_page == 0:
                    min_page = f.page

            group = FormFieldGroup(
                group_name=parent_name,
                group_label=group_label,
                group_type=group_type_str,
                options=options,
                required=any_required,
                page=min_page
            )
            field_groups.append(group)

        # Debug: Log field names and grouping results
        logger.info(f"Extracted {len(standalone_fields)} standalone fields and {len(field_groups)} field groups")
        if standalone_fields:
            logger.info(f"Standalone field names: {[f.name for f in standalone_fields[:10]]}")
        if field_groups:
            logger.info(f"Field groups: {[(g.group_name, g.group_label, len(g.options)) for g in field_groups]}")

        return standalone_fields, field_groups

    except Exception as e:
        logger.exception(f"Error extracting grouped form fields: {e}")
        raise ValueError(f"Failed to extract form fields: {str(e)}")


def field_groups_to_dict(groups: List[FormFieldGroup]) -> List[Dict[str, Any]]:
    """Convert FormFieldGroup objects to dictionaries for JSON serialization."""
    return [
        {
            "group_name": g.group_name,
            "group_label": g.group_label,
            "group_type": g.group_type,
            "options": g.options,
            "required": g.required,
            "page": g.page
        }
        for g in groups
    ]
