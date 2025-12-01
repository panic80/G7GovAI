"""
JSON parsing utilities with robust error handling.

Provides safe JSON parsing functions that handle:
- Malformed JSON
- JSON embedded in markdown code blocks
- LLM responses with surrounding text
- Partial or truncated JSON
"""

import json
import re
import logging
from typing import Any, Optional, List, TypeVar, Type

logger = logging.getLogger(__name__)

T = TypeVar('T')


def safe_json_parse(text: str, default: Any = None) -> Optional[Any]:
    """
    Safely parse JSON with error handling.

    Args:
        text: String to parse as JSON
        default: Value to return if parsing fails

    Returns:
        Parsed JSON or default value

    Example:
        >>> safe_json_parse('{"key": "value"}')
        {'key': 'value'}
        >>> safe_json_parse('invalid', default={})
        {}
    """
    if not text or not isinstance(text, str):
        return default

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.debug(f"JSON parse error: {e}, input preview: {text[:100]}")
        return default


def safe_json_loads(text: str) -> Optional[Any]:
    """
    Parse JSON string, returning None on failure.

    Alias for safe_json_parse with None as default.

    Args:
        text: String to parse

    Returns:
        Parsed JSON or None
    """
    return safe_json_parse(text, default=None)


def extract_json_from_text(text: str) -> Optional[dict]:
    """
    Extract a JSON object from text that may contain markdown fences or surrounding text.

    Handles common LLM output patterns:
    - ```json ... ```
    - ``` ... ```
    - Plain JSON objects
    - JSON with surrounding explanation text

    Args:
        text: Text potentially containing a JSON object

    Returns:
        Extracted and parsed JSON dict, or None if not found

    Example:
        >>> extract_json_from_text('Here is the result: ```json\\n{"key": "value"}\\n```')
        {'key': 'value'}
    """
    if not text or not isinstance(text, str):
        return None

    text = text.strip()

    # Try direct parse first (fastest path)
    result = safe_json_parse(text)
    if isinstance(result, dict):
        return result

    # Try extracting from markdown code blocks
    patterns = [
        # JSON code block
        r'```json\s*([\s\S]*?)\s*```',
        # Generic code block
        r'```\s*([\s\S]*?)\s*```',
        # Find JSON object pattern (greedy, from first { to last })
        r'(\{[\s\S]*\})',
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            candidate = match.group(1).strip()
            result = safe_json_parse(candidate)
            if isinstance(result, dict):
                return result

    return None


def extract_json_array_from_text(text: str) -> Optional[List[Any]]:
    """
    Extract a JSON array from text that may contain markdown fences.

    Similar to extract_json_from_text but for arrays.

    Args:
        text: Text potentially containing a JSON array

    Returns:
        Extracted and parsed JSON array, or None if not found

    Example:
        >>> extract_json_array_from_text('```json\\n[1, 2, 3]\\n```')
        [1, 2, 3]
    """
    if not text or not isinstance(text, str):
        return None

    text = text.strip()

    # Try direct parse first
    result = safe_json_parse(text)
    if isinstance(result, list):
        return result

    # Try extracting from markdown code blocks
    patterns = [
        r'```json\s*([\s\S]*?)\s*```',
        r'```\s*([\s\S]*?)\s*```',
        r'(\[[\s\S]*\])',
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            candidate = match.group(1).strip()
            result = safe_json_parse(candidate)
            if isinstance(result, list):
                return result

    return None


def parse_llm_json_response(
    text: str,
    expected_keys: Optional[List[str]] = None,
    default: Optional[dict] = None
) -> dict:
    """
    Parse JSON from an LLM response with validation.

    Attempts to extract and parse JSON, validates expected keys if provided,
    and returns a default value if parsing fails.

    Args:
        text: LLM response text
        expected_keys: Optional list of keys that must be present
        default: Default value if parsing fails (defaults to {})

    Returns:
        Parsed JSON dict

    Example:
        >>> parse_llm_json_response(
        ...     '{"answer": "yes", "confidence": 0.9}',
        ...     expected_keys=['answer']
        ... )
        {'answer': 'yes', 'confidence': 0.9}
    """
    if default is None:
        default = {}

    # Extract JSON from text
    result = extract_json_from_text(text)

    if result is None:
        logger.warning(f"Failed to extract JSON from LLM response: {text[:200]}")
        return default

    # Validate expected keys if provided
    if expected_keys:
        missing_keys = [key for key in expected_keys if key not in result]
        if missing_keys:
            logger.warning(f"LLM response missing expected keys: {missing_keys}")
            # Still return the result, but log the warning

    return result


def fix_truncated_json(text: str) -> Optional[str]:
    """
    Attempt to fix truncated JSON by closing unclosed brackets.

    This is a best-effort function for handling truncated LLM responses.

    Args:
        text: Potentially truncated JSON string

    Returns:
        Fixed JSON string, or None if unfixable

    Example:
        >>> fix_truncated_json('{"items": [1, 2')
        '{"items": [1, 2]}'
    """
    if not text or not isinstance(text, str):
        return None

    text = text.strip()

    # Count unclosed brackets
    open_braces = text.count('{') - text.count('}')
    open_brackets = text.count('[') - text.count(']')

    # If already balanced, return as-is
    if open_braces == 0 and open_brackets == 0:
        return text

    # If more closing than opening, can't fix
    if open_braces < 0 or open_brackets < 0:
        return None

    # Close unclosed brackets (in reverse order of typical nesting)
    fixed = text
    fixed += ']' * open_brackets
    fixed += '}' * open_braces

    # Verify it parses
    if safe_json_parse(fixed) is not None:
        return fixed

    return None


def clean_json_string(text: str) -> str:
    """
    Clean a string for JSON embedding.

    Escapes special characters that would break JSON parsing.

    Args:
        text: String to clean

    Returns:
        Cleaned string safe for JSON embedding
    """
    if not text:
        return ""

    # Replace problematic characters
    replacements = [
        ('\\', '\\\\'),  # Backslash first
        ('"', '\\"'),    # Double quotes
        ('\n', '\\n'),   # Newlines
        ('\r', '\\r'),   # Carriage returns
        ('\t', '\\t'),   # Tabs
    ]

    result = text
    for old, new in replacements:
        result = result.replace(old, new)

    return result


def merge_json_objects(*objects: Optional[dict]) -> dict:
    """
    Merge multiple JSON objects, with later objects taking precedence.

    Args:
        *objects: JSON objects to merge (None values are skipped)

    Returns:
        Merged JSON object

    Example:
        >>> merge_json_objects({'a': 1}, {'b': 2}, {'a': 3})
        {'a': 3, 'b': 2}
    """
    result = {}
    for obj in objects:
        if obj is not None and isinstance(obj, dict):
            result.update(obj)
    return result
