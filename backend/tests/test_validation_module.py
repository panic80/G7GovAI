"""
Tests for the validation utility module.

Target: 100% coverage on utils/validation.py
"""

import pytest
from utils.validation import (
    ValidationError,
    sanitize_filename,
    validate_extension,
    validate_content_type,
    validate_query,
    validate_document_id,
    validate_language,
    ALLOWED_EXTENSIONS,
    ALLOWED_CONTENT_TYPES,
    MAX_QUERY_LENGTH,
    MAX_FILENAME_LENGTH,
)


class TestSanitizeFilename:
    """Tests for filename sanitization."""

    def test_valid_filename_unchanged(self):
        """Normal filenames should pass through with minimal changes."""
        assert sanitize_filename("document.pdf") == "document.pdf"
        assert sanitize_filename("my-file_v2.txt") == "my-file_v2.txt"

    def test_removes_dangerous_characters(self):
        """Dangerous characters should be replaced with underscores."""
        assert sanitize_filename("file<>name.pdf") == "file__name.pdf"
        assert sanitize_filename("file|name.txt") == "file_name.txt"
        assert sanitize_filename('file"name.csv') == "file_name.csv"

    def test_removes_leading_dots(self):
        """Leading dots should be removed to prevent hidden files."""
        assert sanitize_filename(".hidden.txt") == "hidden.txt"
        assert sanitize_filename("...test.pdf") == "test.pdf"

    def test_removes_leading_hyphens(self):
        """Leading hyphens should be removed to prevent option injection."""
        assert sanitize_filename("-file.txt") == "file.txt"
        assert sanitize_filename("--dangerous.pdf") == "dangerous.pdf"

    def test_path_traversal_blocked(self):
        """Path traversal attempts should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            sanitize_filename("../../../etc/passwd")
        assert "path traversal" in str(exc_info.value).lower()

    def test_directory_separator_removed(self):
        """Directory separators in filename should be sanitized."""
        # After os.path.basename and sanitization
        result = sanitize_filename("/etc/passwd")
        assert "/" not in result
        assert "\\" not in result

    def test_empty_filename_rejected(self):
        """Empty filenames should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            sanitize_filename("")
        assert "empty" in str(exc_info.value).lower()

    def test_none_filename_rejected(self):
        """None filenames should raise ValidationError."""
        with pytest.raises(ValidationError):
            sanitize_filename(None)

    def test_length_limit_enforced(self):
        """Long filenames should be truncated."""
        long_name = "a" * 300 + ".pdf"
        result = sanitize_filename(long_name)
        assert len(result) <= MAX_FILENAME_LENGTH

    def test_extension_preserved_on_truncation(self):
        """Extension should be preserved when truncating."""
        long_name = "a" * 300 + ".pdf"
        result = sanitize_filename(long_name)
        assert result.endswith(".pdf")


class TestValidateExtension:
    """Tests for file extension validation."""

    def test_allowed_extensions_accepted(self):
        """Allowed extensions should pass validation."""
        for ext in ALLOWED_EXTENSIONS:
            filename = f"test{ext}"
            result = validate_extension(filename)
            assert result == ext

    def test_disallowed_extension_rejected(self):
        """Disallowed extensions should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_extension("malware.exe")
        assert "not allowed" in str(exc_info.value).lower()

    def test_case_insensitive(self):
        """Extension check should be case insensitive."""
        assert validate_extension("test.PDF") == ".pdf"
        assert validate_extension("test.TXT") == ".txt"

    def test_no_extension_rejected(self):
        """Files without extension should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            validate_extension("noextension")
        assert "no file extension" in str(exc_info.value).lower()

    def test_custom_allowed_set(self):
        """Custom allowed extensions set should work."""
        custom = {".xyz", ".abc"}
        assert validate_extension("test.xyz", allowed=custom) == ".xyz"

        with pytest.raises(ValidationError):
            validate_extension("test.pdf", allowed=custom)


class TestValidateContentType:
    """Tests for content type validation."""

    def test_allowed_content_types_accepted(self):
        """Allowed content types should pass validation."""
        for ct in ALLOWED_CONTENT_TYPES:
            result = validate_content_type(ct)
            assert result == ct

    def test_disallowed_content_type_rejected(self):
        """Disallowed content types should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_content_type("application/octet-stream")
        assert "not allowed" in str(exc_info.value).lower()

    def test_parameters_stripped(self):
        """Content type parameters should be stripped."""
        result = validate_content_type("text/plain; charset=utf-8")
        assert result == "text/plain"

    def test_case_normalized(self):
        """Content types should be normalized to lowercase."""
        result = validate_content_type("TEXT/PLAIN")
        assert result == "text/plain"


class TestValidateQuery:
    """Tests for query validation."""

    def test_valid_query_returned(self):
        """Valid queries should be returned trimmed."""
        assert validate_query("test query") == "test query"
        assert validate_query("  trimmed  ") == "trimmed"

    def test_empty_query_rejected(self):
        """Empty queries should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_query("")
        assert "empty" in str(exc_info.value).lower()

    def test_whitespace_only_rejected(self):
        """Whitespace-only queries should raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_query("   ")

    def test_max_length_enforced(self):
        """Queries exceeding max length should raise ValidationError."""
        long_query = "x" * (MAX_QUERY_LENGTH + 1)
        with pytest.raises(ValidationError) as exc_info:
            validate_query(long_query)
        assert "maximum length" in str(exc_info.value).lower()

    def test_custom_max_length(self):
        """Custom max length should be respected."""
        with pytest.raises(ValidationError):
            validate_query("12345", max_length=3)

        # Should pass with longer limit
        assert validate_query("12345", max_length=10) == "12345"


class TestValidateDocumentId:
    """Tests for document ID validation."""

    def test_valid_id_accepted(self):
        """Valid document IDs should pass validation."""
        assert validate_document_id("doc123") == "doc123"
        assert validate_document_id("doc-123") == "doc-123"
        assert validate_document_id("doc_123") == "doc_123"
        assert validate_document_id("DOC-ABC-123") == "DOC-ABC-123"

    def test_empty_id_rejected(self):
        """Empty document IDs should raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_document_id("")

    def test_special_characters_rejected(self):
        """Document IDs with special characters should be rejected."""
        invalid_ids = [
            "doc/123",
            "doc\\123",
            "doc<script>",
            "doc;drop table",
            "../passwd",
            "doc|cat",
        ]
        for doc_id in invalid_ids:
            with pytest.raises(ValidationError):
                validate_document_id(doc_id)

    def test_spaces_rejected(self):
        """Document IDs with spaces should be rejected."""
        with pytest.raises(ValidationError):
            validate_document_id("doc 123")

    def test_length_limit(self):
        """Document IDs exceeding 255 chars should be rejected."""
        long_id = "a" * 256
        with pytest.raises(ValidationError):
            validate_document_id(long_id)


class TestValidateLanguage:
    """Tests for language code validation."""

    def test_valid_languages_accepted(self):
        """Valid language codes should pass validation."""
        assert validate_language("en") == "en"
        assert validate_language("fr") == "fr"

    def test_case_insensitive(self):
        """Language validation should be case insensitive."""
        assert validate_language("EN") == "en"
        assert validate_language("FR") == "fr"

    def test_invalid_language_rejected(self):
        """Invalid language codes should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_language("de")
        assert "not supported" in str(exc_info.value).lower()

    def test_empty_language_rejected(self):
        """Empty language should raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_language("")


class TestValidationErrorException:
    """Tests for ValidationError exception."""

    def test_error_has_message(self):
        """ValidationError should have message attribute."""
        error = ValidationError("test message")
        assert error.message == "test message"
        assert str(error) == "test message"

    def test_error_has_field(self):
        """ValidationError should support field attribute."""
        error = ValidationError("bad value", field="query")
        assert error.field == "query"

    def test_error_field_optional(self):
        """Field attribute should be optional."""
        error = ValidationError("message only")
        assert error.field is None
