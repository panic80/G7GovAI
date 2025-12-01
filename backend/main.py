"""
GovAI RAG Service - FastAPI Application

Main entry point for the GovAI backend API.
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import uvicorn

from core.config import CORS_ORIGINS
from core.security import verify_api_key
from core.rate_limit import limiter, rate_limit_exceeded_handler
from core.middleware import SecurityHeadersMiddleware
from api.routers import search, documents, foresight, agents, system, knowledge_base, forms


# Initialize App
app = FastAPI(
    title="GovAI RAG Service",
    description="Government AI Platform for document search, rules evaluation, and optimization",
    version="1.0.0",
    dependencies=[Depends(verify_api_key)]
)

# Configure rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# CORS Configuration - Tightened for security
# Only allow specific origins, methods, and headers
origins = [origin.strip() for origin in CORS_ORIGINS.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    # Explicit methods instead of wildcard
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    # Explicit headers instead of wildcard
    allow_headers=[
        "content-type",
        "x-govai-key",
        "accept",
        "accept-language",
        "origin",
    ],
    # Expose only necessary headers
    expose_headers=["content-type", "content-length"],
    # Cache preflight requests for 1 hour
    max_age=3600,
)

# Include Routers
app.include_router(system.router, tags=["System"])
app.include_router(search.router, tags=["Search"])
app.include_router(documents.router, tags=["Documents"])
app.include_router(foresight.router, tags=["Foresight"])
app.include_router(agents.router, tags=["Agents"])
app.include_router(knowledge_base.router, tags=["Knowledge Base"])
app.include_router(forms.router, tags=["Forms"])


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
