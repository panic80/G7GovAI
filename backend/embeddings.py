"""
Gemini-based embeddings with LRU caching for faster repeat queries.

Uses Google Gemini text-embedding-004 (768 dimensions).
"""
import os
import logging
from functools import lru_cache
from typing import List
import google.generativeai as genai
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

try:
    from core.constants import EMBEDDING_CACHE_SIZE, EMBEDDING_BATCH_SIZE, EMBEDDING_DIMENSIONS
    from core.model_state import model_config
except ImportError:
    load_dotenv()
    model_config = None
    EMBEDDING_CACHE_SIZE = 1000
    EMBEDDING_BATCH_SIZE = 100
    EMBEDDING_DIMENSIONS = 768


@lru_cache(maxsize=EMBEDDING_CACHE_SIZE)
def get_embedding(text: str, dimensions: int = EMBEDDING_DIMENSIONS) -> List[float]:
    """
    Generate embedding for a single text with LRU caching.

    First call: ~2-5s (Gemini API)
    Cached call: ~0.01ms
    """
    if model_config is None or not model_config.ensure_configured():
        return []
    try:
        model = "models/text-embedding-004"
        result = genai.embed_content(
            model=model, content=text, task_type="retrieval_query"
        )
        return result["embedding"]
    except Exception as e:
        logger.error(f"Error embedding text: {e}")
        return []


def get_embeddings_batch(texts: List[str], dimensions: int = EMBEDDING_DIMENSIONS) -> List[List[float]]:
    """
    Generate batch of embeddings using Gemini.

    Note: Batch calls are NOT cached (used for document ingestion).
    """
    if model_config is None or not model_config.ensure_configured():
        return []
    try:
        model = "models/text-embedding-004"
        all_embeddings = []

        for i in range(0, len(texts), EMBEDDING_BATCH_SIZE):
            batch = texts[i : i + EMBEDDING_BATCH_SIZE]
            result = genai.embed_content(
                model=model, content=batch, task_type="retrieval_document"
            )
            all_embeddings.extend(result["embedding"])

        return all_embeddings
    except Exception as e:
        logger.error(f"Error embedding batch: {e}")
        # Fallback to individual processing
        return [get_embedding(text) for text in texts]


def clear_embedding_cache():
    """Clear the LRU cache for embeddings."""
    get_embedding.cache_clear()
    logger.debug("Embedding cache cleared.")


def get_cache_info():
    """Get cache statistics."""
    return get_embedding.cache_info()
