"""
Tests for centralized error handling.
"""

import pytest
from fastapi import status
from core.errors import (
    ErrorCode,
    GovAIError,
    ValidationError,
    NotFoundError,
    DocumentNotFoundError,
    ProcessingError,
    EmbeddingError,
    LLMError,
    ServiceUnavailableError,
    handle_exception,
    raise_validation_error,
)


class TestErrorCode:
    """Test ErrorCode enum."""

    def test_error_codes_are_strings(self):
        """Error codes should be string values."""
        assert isinstance(ErrorCode.VALIDATION_ERROR.value, str)
        assert ErrorCode.VALIDATION_ERROR.value == "VALIDATION_ERROR"

    def test_all_error_codes_exist(self):
        """Verify all expected error codes exist."""
        expected_codes = [
            "VALIDATION_ERROR",
            "INVALID_INPUT",
            "NOT_FOUND",
            "DOCUMENT_NOT_FOUND",
            "PROCESSING_ERROR",
            "INTERNAL_ERROR",
        ]
        for code in expected_codes:
            assert hasattr(ErrorCode, code)


class TestGovAIError:
    """Test base GovAIError class."""

    def test_create_error(self):
        """Can create a basic error."""
        error = GovAIError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Test error",
        )
        assert error.code == ErrorCode.INTERNAL_ERROR
        assert error.message == "Test error"
        assert error.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert error.details == {}

    def test_create_error_with_details(self):
        """Can create error with additional details."""
        error = GovAIError(
            code=ErrorCode.VALIDATION_ERROR,
            message="Invalid field",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"field": "email"},
        )
        assert error.details == {"field": "email"}

    def test_to_http_exception(self):
        """Can convert to HTTPException."""
        error = GovAIError(
            code=ErrorCode.NOT_FOUND,
            message="Resource not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )
        http_exc = error.to_http_exception()
        assert http_exc.status_code == 404
        assert http_exc.detail["code"] == "NOT_FOUND"
        assert http_exc.detail["message"] == "Resource not found"


class TestValidationError:
    """Test ValidationError class."""

    def test_default_status_code(self):
        """Validation errors should be 400."""
        error = ValidationError("Invalid input")
        assert error.status_code == status.HTTP_400_BAD_REQUEST

    def test_with_custom_code(self):
        """Can use custom error code."""
        error = ValidationError(
            message="Invalid file",
            code=ErrorCode.INVALID_FILE_TYPE,
        )
        assert error.code == ErrorCode.INVALID_FILE_TYPE


class TestNotFoundError:
    """Test NotFoundError class."""

    def test_default_status_code(self):
        """Not found errors should be 404."""
        error = NotFoundError("Item not found")
        assert error.status_code == status.HTTP_404_NOT_FOUND

    def test_document_not_found(self):
        """DocumentNotFoundError includes doc_id."""
        error = DocumentNotFoundError("doc-123")
        assert error.status_code == status.HTTP_404_NOT_FOUND
        assert error.code == ErrorCode.DOCUMENT_NOT_FOUND
        assert error.details["doc_id"] == "doc-123"
        assert "doc-123" in error.message


class TestProcessingError:
    """Test ProcessingError class."""

    def test_default_values(self):
        """ProcessingError has correct defaults."""
        error = ProcessingError()
        assert error.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert error.code == ErrorCode.PROCESSING_ERROR


class TestHandleException:
    """Test handle_exception helper."""

    def test_handles_govai_error(self):
        """Converts GovAIError to HTTPException."""
        error = ValidationError("Test error")
        http_exc = handle_exception(error)
        assert http_exc.status_code == 400

    def test_handles_generic_exception(self):
        """Converts generic exceptions to 500."""
        error = ValueError("Something went wrong")
        http_exc = handle_exception(error)
        assert http_exc.status_code == 500

    def test_uses_custom_message(self):
        """Uses provided default message."""
        error = ValueError("Something went wrong")
        http_exc = handle_exception(error, "Custom error message")
        assert http_exc.detail["message"] == "Custom error message"


class TestRaiseValidationError:
    """Test raise_validation_error helper."""

    def test_raises_validation_error(self):
        """Raises ValidationError with field context."""
        with pytest.raises(ValidationError) as exc_info:
            raise_validation_error("email", "must be a valid email address")

        error = exc_info.value
        assert error.code == ErrorCode.INVALID_INPUT
        assert "email" in error.message
        assert error.details["field"] == "email"

    def test_includes_value_when_provided(self):
        """Includes truncated value in details."""
        with pytest.raises(ValidationError) as exc_info:
            raise_validation_error("count", "must be positive", value=-5)

        error = exc_info.value
        assert error.details["value"] == "-5"
