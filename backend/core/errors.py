"""
Centralized error types for GovAI backend.

Provides consistent error handling across all API endpoints with:
- Type-safe error classes
- HTTP status code mapping
- Structured error responses
"""

from enum import Enum
from typing import Optional, Dict, Any
from fastapi import HTTPException, status


class ErrorCode(str, Enum):
    """Application error codes for consistent error identification."""

    # Validation errors (400)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    INVALID_FILE_TYPE = "INVALID_FILE_TYPE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"

    # Authentication/Authorization errors (401/403)
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    INVALID_TOKEN = "INVALID_TOKEN"

    # Not found errors (404)
    NOT_FOUND = "NOT_FOUND"
    DOCUMENT_NOT_FOUND = "DOCUMENT_NOT_FOUND"
    CONNECTOR_NOT_FOUND = "CONNECTOR_NOT_FOUND"

    # Conflict errors (409)
    CONFLICT = "CONFLICT"
    DUPLICATE_ENTRY = "DUPLICATE_ENTRY"

    # Rate limiting (429)
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

    # Server errors (500)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    EMBEDDING_ERROR = "EMBEDDING_ERROR"
    LLM_ERROR = "LLM_ERROR"
    PROCESSING_ERROR = "PROCESSING_ERROR"

    # Service unavailable (503)
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    MODEL_NOT_LOADED = "MODEL_NOT_LOADED"


class GovAIError(Exception):
    """Base exception class for GovAI application errors."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

    def to_http_exception(self) -> HTTPException:
        """Convert to FastAPI HTTPException."""
        return HTTPException(
            status_code=self.status_code,
            detail={
                "code": self.code.value,
                "message": self.message,
                **self.details,
            }
        )


# =============================================================================
# Specific Error Classes
# =============================================================================

class ValidationError(GovAIError):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str = "Validation failed",
        code: ErrorCode = ErrorCode.VALIDATION_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class NotFoundError(GovAIError):
    """Raised when a requested resource is not found."""

    def __init__(
        self,
        message: str = "Resource not found",
        code: ErrorCode = ErrorCode.NOT_FOUND,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class DocumentNotFoundError(NotFoundError):
    """Raised when a document is not found."""

    def __init__(self, doc_id: str):
        super().__init__(
            message=f"Document not found: {doc_id}",
            code=ErrorCode.DOCUMENT_NOT_FOUND,
            details={"doc_id": doc_id},
        )


class ProcessingError(GovAIError):
    """Raised when document/data processing fails."""

    def __init__(
        self,
        message: str = "Processing failed",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            code=ErrorCode.PROCESSING_ERROR,
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


class EmbeddingError(GovAIError):
    """Raised when embedding generation fails."""

    def __init__(
        self,
        message: str = "Embedding generation failed",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            code=ErrorCode.EMBEDDING_ERROR,
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


class LLMError(GovAIError):
    """Raised when LLM call fails."""

    def __init__(
        self,
        message: str = "LLM request failed",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            code=ErrorCode.LLM_ERROR,
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


class ServiceUnavailableError(GovAIError):
    """Raised when a required service is unavailable."""

    def __init__(
        self,
        message: str = "Service temporarily unavailable",
        code: ErrorCode = ErrorCode.SERVICE_UNAVAILABLE,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
        )


# =============================================================================
# Error Handler Helpers
# =============================================================================

def handle_exception(exc: Exception, default_message: str = "An unexpected error occurred") -> HTTPException:
    """
    Convert any exception to an appropriate HTTPException.

    Args:
        exc: The exception to handle
        default_message: Message to use for unknown exceptions

    Returns:
        HTTPException with appropriate status code and detail
    """
    if isinstance(exc, GovAIError):
        return exc.to_http_exception()

    if isinstance(exc, HTTPException):
        return exc

    # Log unexpected errors (will be caught by logging)
    import logging
    logging.error(f"Unexpected error: {exc}", exc_info=True)

    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={
            "code": ErrorCode.INTERNAL_ERROR.value,
            "message": default_message,
        }
    )


def raise_validation_error(
    field: str,
    message: str,
    value: Optional[Any] = None,
) -> None:
    """Helper to raise a validation error with field context."""
    details = {"field": field}
    if value is not None:
        details["value"] = str(value)[:100]  # Truncate for safety
    raise ValidationError(
        message=f"Invalid {field}: {message}",
        code=ErrorCode.INVALID_INPUT,
        details=details,
    )
