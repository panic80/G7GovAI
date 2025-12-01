"""
Shared file upload utilities.

Provides unified file upload handling with validation for use across
documents.py and knowledge_base.py routers.
"""

import logging
import re
import tempfile
from pathlib import Path
from typing import Set, Optional

from fastapi import UploadFile, HTTPException

from core.constants import (
    ALLOWED_FILE_EXTENSIONS,
    ALLOWED_CONTENT_TYPES,
    FILE_CHUNK_SIZE_BYTES,
    MAX_FILENAME_LENGTH,
)

logger = logging.getLogger(__name__)


class FileUploadError(Exception):
    """Raised when file upload validation fails."""
    pass


def sanitize_filename(filename: str) -> str:
    """
    Securely sanitize a filename.

    Args:
        filename: Original filename from upload

    Returns:
        Sanitized filename safe for filesystem operations

    Raises:
        FileUploadError: If filename is invalid
    """
    if not filename:
        raise FileUploadError("Filename cannot be empty")

    # Remove dangerous characters
    safe = re.sub(r"[^\w\.-]", "_", filename)
    safe = safe.lstrip(".-")

    # Enforce length limit
    if len(safe) > MAX_FILENAME_LENGTH:
        name, ext = safe.rsplit(".", 1) if "." in safe else (safe, "")
        if ext:
            safe = name[:MAX_FILENAME_LENGTH - len(ext) - 1] + "." + ext
        else:
            safe = safe[:MAX_FILENAME_LENGTH]

    if not safe:
        raise FileUploadError("Filename invalid after sanitization")

    return safe


def validate_file_extension(
    filename: str,
    allowed: Optional[Set[str]] = None
) -> str:
    """
    Validate file extension against whitelist.

    Args:
        filename: Filename to check
        allowed: Set of allowed extensions (with dots). Defaults to ALLOWED_FILE_EXTENSIONS.

    Returns:
        The extension (lowercase with dot)

    Raises:
        HTTPException: If extension not allowed
    """
    if allowed is None:
        allowed = ALLOWED_FILE_EXTENSIONS

    ext = Path(filename).suffix.lower()

    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{ext}'. Allowed: {', '.join(sorted(allowed))}"
        )

    return ext


def validate_content_type(
    content_type: str,
    allowed: Optional[Set[str]] = None
) -> str:
    """
    Validate content type against whitelist.

    Args:
        content_type: MIME type to check
        allowed: Set of allowed content types. Defaults to ALLOWED_CONTENT_TYPES.

    Returns:
        The normalized content type (lowercase, no params)

    Raises:
        HTTPException: If content type not allowed
    """
    if allowed is None:
        allowed = ALLOWED_CONTENT_TYPES

    # Normalize: extract base type without parameters
    base_type = content_type.split(";")[0].strip().lower() if content_type else ""

    if base_type not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid content type '{base_type}'. Allowed: {', '.join(sorted(allowed))}"
        )

    return base_type


async def save_uploaded_file(
    file: UploadFile,
    allowed_extensions: Optional[Set[str]] = None,
    allowed_content_types: Optional[Set[str]] = None,
    max_size_mb: int = 50,
    temp_dir: Optional[Path] = None
) -> Path:
    """
    Save an uploaded file to a temporary location with validation.

    Args:
        file: FastAPI UploadFile object
        allowed_extensions: Set of allowed file extensions
        allowed_content_types: Set of allowed MIME types
        max_size_mb: Maximum file size in megabytes
        temp_dir: Directory to save file. Uses system temp if not specified.

    Returns:
        Path to the saved temporary file

    Raises:
        HTTPException: If validation fails or file too large
    """
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Validate extension
    validate_file_extension(file.filename, allowed_extensions)

    # Validate content type
    if file.content_type:
        validate_content_type(file.content_type, allowed_content_types)

    # Sanitize filename
    safe_filename = sanitize_filename(file.filename)

    # Create temp directory if needed
    if temp_dir is None:
        temp_dir = Path(tempfile.gettempdir()) / "govai_uploads"

    temp_dir.mkdir(parents=True, exist_ok=True)

    # Save file with size check
    temp_path = temp_dir / safe_filename
    max_size_bytes = max_size_mb * 1024 * 1024
    total_size = 0

    try:
        with open(temp_path, "wb") as f:
            while True:
                chunk = await file.read(FILE_CHUNK_SIZE_BYTES)
                if not chunk:
                    break

                total_size += len(chunk)
                if total_size > max_size_bytes:
                    # Clean up partial file
                    temp_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds maximum size of {max_size_mb}MB"
                    )

                f.write(chunk)

        logger.info(f"Saved uploaded file: {safe_filename} ({total_size} bytes)")
        return temp_path

    except HTTPException:
        raise
    except Exception as e:
        # Clean up on error
        temp_path.unlink(missing_ok=True)
        logger.error(f"Error saving uploaded file: {e}")
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")


def cleanup_temp_file(file_path: Path) -> None:
    """
    Clean up a temporary file.

    Args:
        file_path: Path to file to delete
    """
    try:
        if file_path and file_path.exists():
            file_path.unlink()
            logger.debug(f"Cleaned up temp file: {file_path}")
    except Exception as e:
        logger.warning(f"Failed to clean up temp file {file_path}: {e}")
