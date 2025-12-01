"""
Input validation utilities for security.

This module provides centralized validation functions for user inputs
to prevent security vulnerabilities like path traversal, injection attacks,
and other common attack vectors.
"""

import os
import re
import logging
from pathlib import Path
from typing import Set, Optional

logger = logging.getLogger(__name__)


# Security constants
MAX_QUERY_LENGTH = 10000
MAX_FILENAME_LENGTH = 255
ALLOWED_EXTENSIONS: Set[str] = {".pdf", ".txt", ".md", ".csv", ".json", ".html"}
ALLOWED_CONTENT_TYPES: Set[str] = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "text/csv",
    "text/html",
    "application/json",
}


class ValidationError(Exception):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(self.message)


def sanitize_filename(filename: str) -> str:
    """
    Securely sanitize a filename to prevent path traversal and injection attacks.

    Args:
        filename: The original filename from user input

    Returns:
        A sanitized filename safe for filesystem operations

    Raises:
        ValidationError: If the filename is empty or contains path traversal attempts
    """
    if not filename:
        raise ValidationError("Filename cannot be empty", field="filename")

    # Check for path traversal BEFORE sanitizing - reject parent directory attempts
    # Only reject ".." (parent traversal), not leading "/" or "..." (which are sanitized)
    if ".." in filename and "..." not in filename:
        logger.warning(f"Path traversal attempt detected: {filename[:50]}")
        raise ValidationError("Invalid filename: path traversal detected", field="filename")

    # Remove any directory path components
    filename = os.path.basename(filename)

    # Remove dangerous characters, keeping only alphanumeric, dots, hyphens, underscores
    safe = re.sub(r"[^\w\.-]", "_", filename)

    # Remove leading dots and hyphens (prevent hidden files and option injection)
    safe = safe.lstrip(".-")

    # Enforce length limit
    if len(safe) > MAX_FILENAME_LENGTH:
        name, ext = os.path.splitext(safe)
        safe = name[: MAX_FILENAME_LENGTH - len(ext)] + ext

    # Final safety check - should never trigger after above processing
    if ".." in safe or "/" in safe or "\\" in safe:
        logger.warning(f"Path traversal attempt detected: {filename}")
        raise ValidationError("Invalid filename: path traversal detected", field="filename")

    # Ensure we have something left
    if not safe or safe == "_":
        raise ValidationError("Filename results in empty or invalid after sanitization", field="filename")

    return safe


def validate_extension(filename: str, allowed: Optional[Set[str]] = None) -> str:
    """
    Validate that a file has an allowed extension.

    Args:
        filename: The filename to check
        allowed: Optional set of allowed extensions. Defaults to ALLOWED_EXTENSIONS.

    Returns:
        The lowercase extension including the dot (e.g., ".pdf")

    Raises:
        ValidationError: If the extension is not in the allowed set
    """
    if allowed is None:
        allowed = ALLOWED_EXTENSIONS

    ext = Path(filename).suffix.lower()

    if not ext:
        raise ValidationError(
            f"No file extension found. Allowed: {', '.join(sorted(allowed))}",
            field="filename"
        )

    if ext not in allowed:
        raise ValidationError(
            f"File type '{ext}' not allowed. Allowed: {', '.join(sorted(allowed))}",
            field="filename"
        )

    return ext


def validate_content_type(content_type: str, allowed: Optional[Set[str]] = None) -> str:
    """
    Validate that a content type is allowed.

    Args:
        content_type: The MIME type to check
        allowed: Optional set of allowed content types. Defaults to ALLOWED_CONTENT_TYPES.

    Returns:
        The normalized content type (lowercase, without parameters)

    Raises:
        ValidationError: If the content type is not allowed
    """
    if allowed is None:
        allowed = ALLOWED_CONTENT_TYPES

    # Normalize: extract base MIME type (remove charset and other parameters)
    base_type = content_type.split(";")[0].strip().lower()

    if base_type not in allowed:
        raise ValidationError(
            f"Content type '{base_type}' not allowed. Allowed: {', '.join(sorted(allowed))}",
            field="content_type"
        )

    return base_type


def validate_query(query: str, max_length: Optional[int] = None) -> str:
    """
    Validate and sanitize a search query.

    Args:
        query: The search query from user input
        max_length: Optional maximum length. Defaults to MAX_QUERY_LENGTH.

    Returns:
        The trimmed query string

    Raises:
        ValidationError: If the query is empty or exceeds maximum length
    """
    if max_length is None:
        max_length = MAX_QUERY_LENGTH

    if not query or not query.strip():
        raise ValidationError("Query cannot be empty", field="query")

    query = query.strip()

    if len(query) > max_length:
        raise ValidationError(
            f"Query exceeds maximum length of {max_length} characters",
            field="query"
        )

    return query


def validate_document_id(doc_id: str) -> str:
    """
    Validate a document ID to prevent injection attacks.

    Document IDs should only contain alphanumeric characters, hyphens, and underscores.

    Args:
        doc_id: The document ID to validate

    Returns:
        The validated document ID

    Raises:
        ValidationError: If the document ID contains invalid characters
    """
    if not doc_id:
        raise ValidationError("Document ID cannot be empty", field="doc_id")

    # Allow only alphanumeric, hyphens, underscores
    pattern = r"^[a-zA-Z0-9_-]+$"
    if not re.match(pattern, doc_id):
        logger.warning(f"Invalid document ID format: {doc_id[:50]}...")
        raise ValidationError(
            "Document ID contains invalid characters. Only alphanumeric, hyphens, and underscores allowed.",
            field="doc_id"
        )

    if len(doc_id) > 255:
        raise ValidationError("Document ID exceeds maximum length of 255 characters", field="doc_id")

    return doc_id


def validate_language(language: str) -> str:
    """
    Validate a language code.

    Args:
        language: The language code (e.g., "en", "fr")

    Returns:
        The lowercase language code

    Raises:
        ValidationError: If the language code is invalid
    """
    allowed_languages = {"en", "fr"}

    if not language:
        raise ValidationError("Language cannot be empty", field="language")

    language = language.lower().strip()

    if language not in allowed_languages:
        raise ValidationError(
            f"Language '{language}' not supported. Supported: {', '.join(sorted(allowed_languages))}",
            field="language"
        )

    return language
