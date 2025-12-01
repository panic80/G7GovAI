"""
Security and utility middleware for GovAI backend.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Headers added:
    - X-Content-Type-Options: Prevents MIME type sniffing
    - X-Frame-Options: Prevents clickjacking
    - X-XSS-Protection: Legacy XSS protection (for older browsers)
    - Referrer-Policy: Controls referrer information
    - Cache-Control: Prevents caching of sensitive data
    - Permissions-Policy: Restricts browser features
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Legacy XSS protection for older browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Restrict browser features (no camera, mic, geolocation, etc.)
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), interest-cohort=()"
        )

        # For API responses, prevent caching of potentially sensitive data
        if request.url.path.startswith("/search") or request.url.path.startswith("/agent"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request logging (sanitized, no sensitive data).
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        import logging
        import time

        logger = logging.getLogger("govai.requests")

        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        # Log request (sanitized - no query params or body)
        logger.info(
            f"{request.method} {request.url.path} "
            f"status={response.status_code} "
            f"duration={process_time:.3f}s"
        )

        # Add timing header
        response.headers["X-Process-Time"] = f"{process_time:.3f}"

        return response
