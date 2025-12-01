"""
Structured logging configuration for GovAI backend.

Provides:
- JSON-formatted logs for production
- Human-readable logs for development
- Request/response logging
- Performance timing
"""

import logging
import sys
import time
from typing import Optional, Any, Dict
from functools import wraps
from contextlib import contextmanager

# Try to import json logger for structured output
try:
    from pythonjsonlogger import jsonlogger
    HAS_JSON_LOGGER = True
except ImportError:
    HAS_JSON_LOGGER = False


# =============================================================================
# Logger Configuration
# =============================================================================

def setup_logging(
    level: str = "INFO",
    json_format: bool = False,
    service_name: str = "govai-backend",
) -> logging.Logger:
    """
    Configure logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        json_format: If True, output structured JSON logs
        service_name: Name to include in log entries

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    logger.handlers.clear()

    # Create handler
    handler = logging.StreamHandler(sys.stdout)

    if json_format and HAS_JSON_LOGGER:
        # JSON format for production
        formatter = jsonlogger.JsonFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s',
            rename_fields={
                'timestamp': '@timestamp',
                'level': 'log_level',
            }
        )
    else:
        # Human-readable format for development
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


# Default logger instance
logger = setup_logging()


# =============================================================================
# Logging Utilities
# =============================================================================

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.

    Args:
        name: Module name (usually __name__)

    Returns:
        Logger instance with the given name
    """
    return logging.getLogger(f"govai-backend.{name}")


@contextmanager
def log_timing(operation: str, logger: Optional[logging.Logger] = None):
    """
    Context manager to log operation timing.

    Usage:
        with log_timing("database_query"):
            results = db.query(...)
    """
    log = logger or logging.getLogger("govai-backend")
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = (time.perf_counter() - start) * 1000  # ms
        log.info(f"{operation} completed in {elapsed:.2f}ms")


def timed(operation: Optional[str] = None):
    """
    Decorator to log function execution time.

    Usage:
        @timed("search_documents")
        async def search(...):
            ...
    """
    def decorator(func):
        op_name = operation or func.__name__

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                elapsed = (time.perf_counter() - start) * 1000
                logger.info(f"{op_name} completed in {elapsed:.2f}ms")

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                elapsed = (time.perf_counter() - start) * 1000
                logger.info(f"{op_name} completed in {elapsed:.2f}ms")

        if hasattr(func, '__await__') or hasattr(func, '__aenter__'):
            return async_wrapper
        return sync_wrapper

    return decorator


def log_request(
    method: str,
    path: str,
    params: Optional[Dict[str, Any]] = None,
    body_preview: Optional[str] = None,
) -> None:
    """Log an incoming API request."""
    msg = f"{method} {path}"
    extra: Dict[str, Any] = {}

    if params:
        extra["params"] = params
    if body_preview:
        extra["body_preview"] = body_preview[:200]

    logger.info(msg, extra=extra if extra else None)


def log_response(
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
) -> None:
    """Log an API response."""
    logger.info(
        f"{method} {path} -> {status_code} ({duration_ms:.2f}ms)"
    )


def log_error(
    message: str,
    error: Optional[Exception] = None,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log an error with optional context.

    Args:
        message: Error description
        error: The exception if available
        context: Additional context data
    """
    extra = context or {}
    if error:
        extra["error_type"] = type(error).__name__
        extra["error_detail"] = str(error)

    logger.error(message, extra=extra, exc_info=error is not None)


def log_warning(
    message: str,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """Log a warning with optional context."""
    logger.warning(message, extra=context)


def log_audit(
    action: str,
    resource: str,
    resource_id: Optional[str] = None,
    user_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log an audit event for tracking important actions.

    Args:
        action: The action performed (create, update, delete, etc.)
        resource: The resource type (document, connector, etc.)
        resource_id: ID of the affected resource
        user_id: ID of the user performing the action
        details: Additional details about the action
    """
    audit_logger = logging.getLogger("govai-backend.audit")
    audit_logger.info(
        f"AUDIT: {action} {resource}",
        extra={
            "audit": True,
            "action": action,
            "resource": resource,
            "resource_id": resource_id,
            "user_id": user_id,
            **(details or {}),
        }
    )
