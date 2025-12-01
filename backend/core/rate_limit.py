"""
Rate limiting configuration using slowapi.

This module provides rate limiting functionality to protect API endpoints
from abuse and ensure fair usage.
"""

import logging
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# Initialize the limiter with IP-based key extraction
limiter = Limiter(key_func=get_remote_address)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Custom handler for rate limit exceeded errors.

    Returns a JSON response with error details and retry information.
    """
    logger.warning(
        f"Rate limit exceeded for {get_remote_address(request)}: {exc.detail}"
    )
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please slow down.",
            "detail": str(exc.detail),
        }
    )


# Rate limit configurations for different endpoint types
class RateLimits:
    """Centralized rate limit configurations."""

    # File upload operations - restrictive to prevent abuse
    UPLOAD = "10/minute"

    # Search operations - moderate limit for normal usage
    SEARCH = "60/minute"

    # Agent operations (RAG, LexGraph, etc.) - moderate limit
    AGENT = "30/minute"

    # Dangerous operations - very restrictive
    PURGE = "1/hour"

    # Connector operations - moderate
    CONNECTOR = "20/minute"

    # Health/status checks - relaxed
    HEALTH = "120/minute"
