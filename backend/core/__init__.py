"""
GovAI Core Module.

Provides core utilities used across the backend:
- Configuration management
- Error handling
- Logging utilities
- Rate limiting
- Security helpers
- Constants
"""

# Error handling
from .errors import (
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

# Logging
from .logging import (
    setup_logging,
    get_logger,
    log_timing,
    timed,
    log_request,
    log_response,
    log_error,
    log_warning,
    log_audit,
)

# Rate limiting
from .rate_limit import limiter, RateLimits

# Constants
from .constants import (
    ALLOWED_FILE_EXTENSIONS,
    FILE_CHUNK_SIZE_BYTES,
    SEARCH_INITIAL_LIMIT,
    KEYWORD_SEARCH_LIMIT,
    DEFAULT_MAX_CHUNKS_PER_SOURCE,
    DATASET_MAX_CHUNKS_PER_SOURCE,
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_CACHE_SIZE,
    EMBEDDING_DIMENSIONS,
    PROGRESS_WEIGHTS,
)

__all__ = [
    # Errors
    "ErrorCode",
    "GovAIError",
    "ValidationError",
    "NotFoundError",
    "DocumentNotFoundError",
    "ProcessingError",
    "EmbeddingError",
    "LLMError",
    "ServiceUnavailableError",
    "handle_exception",
    "raise_validation_error",
    # Logging
    "setup_logging",
    "get_logger",
    "log_timing",
    "timed",
    "log_request",
    "log_response",
    "log_error",
    "log_warning",
    "log_audit",
    # Rate limiting
    "limiter",
    "RateLimits",
    # Constants
    "ALLOWED_FILE_EXTENSIONS",
    "FILE_CHUNK_SIZE_BYTES",
    "SEARCH_INITIAL_LIMIT",
    "KEYWORD_SEARCH_LIMIT",
    "DEFAULT_MAX_CHUNKS_PER_SOURCE",
    "DATASET_MAX_CHUNKS_PER_SOURCE",
    "EMBEDDING_BATCH_SIZE",
    "EMBEDDING_CACHE_SIZE",
    "EMBEDDING_DIMENSIONS",
    "PROGRESS_WEIGHTS",
]
