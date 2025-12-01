"""
Search router - Semantic search endpoints.
"""

from fastapi import APIRouter, Depends, Request
from typing import List

from services.search_engine import SearchService
from api.schemas import SearchRequest, SearchResult
from core import (
    limiter,
    RateLimits,
    get_logger,
    handle_exception,
    ProcessingError,
    log_error,
)

logger = get_logger(__name__)
router = APIRouter()


def get_search_service():
    return SearchService()


@router.post("/search", response_model=List[SearchResult])
@limiter.limit(RateLimits.SEARCH)
async def search(
    request: Request,
    search_request: SearchRequest,
    service: SearchService = Depends(get_search_service)
):
    """
    Perform semantic search on the knowledge base.

    Returns a list of relevant documents matching the query.
    Rate limited to 60 requests per minute per IP.
    """
    try:
        return await service.search(search_request)
    except Exception as e:
        log_error(
            "Search error occurred",
            error=e,
            context={"query": search_request.query[:100] if search_request.query else None}
        )
        raise handle_exception(
            ProcessingError(
                message="An error occurred during search. Please try again.",
                details={"query_length": len(search_request.query) if search_request.query else 0}
            )
        )
