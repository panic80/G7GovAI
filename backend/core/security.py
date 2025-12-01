"""
Security module for GovAI API authentication.

Implements API key validation with:
- Constant-time comparison to prevent timing attacks
- Strict validation (no auto_error bypass)
- Minimal public endpoints
- Environment-controlled auth toggle for demo deployments
"""

import os
import logging
from secrets import compare_digest
from fastapi import Security, HTTPException, status, Request
from fastapi.security import APIKeyHeader
from .config import GOVAI_API_KEY

logger = logging.getLogger(__name__)

API_KEY_NAME = "X-GovAI-Key"

# Environment toggle for demo deployments
# Set DISABLE_AUTH=true to skip API key validation (for judges/evaluators)
DISABLE_AUTH = os.getenv("DISABLE_AUTH", "false").lower() in ("true", "1", "yes")

# auto_error=False allows us to handle missing keys explicitly
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Public endpoints that don't require authentication
# Minimized for security - only health check is public
PUBLIC_PATHS = frozenset(["/health"])


async def verify_api_key(request: Request, api_key: str = Security(api_key_header)):
    """
    Verify API key for protected endpoints.

    Authentication can be disabled via DISABLE_AUTH=true environment variable
    for demo/evaluation deployments. When disabled, logs a warning at startup.

    Security measures when enabled:
    - Constant-time comparison to prevent timing attacks
    - Explicit missing key handling (no silent bypass)
    - Structured logging for audit trails
    """
    # Skip auth for public paths
    if request.url.path in PUBLIC_PATHS:
        return

    # Skip auth if explicitly disabled (demo mode)
    if DISABLE_AUTH:
        return

    # Validate API key is configured on server
    if not GOVAI_API_KEY:
        logger.error("GOVAI_API_KEY not configured - rejecting request")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API authentication not configured"
        )

    # Validate client provided a key
    if not api_key:
        logger.warning(f"Missing API key from {request.client.host if request.client else 'unknown'}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"}
        )

    # Constant-time comparison to prevent timing attacks
    if not compare_digest(api_key, GOVAI_API_KEY):
        logger.warning(f"Invalid API key from {request.client.host if request.client else 'unknown'}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )

    return


# Log auth status at module load
if DISABLE_AUTH:
    logger.warning("⚠️  API authentication is DISABLED (DISABLE_AUTH=true)")
else:
    logger.info("✓ API authentication enabled")
