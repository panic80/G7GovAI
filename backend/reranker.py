import logging
from sentence_transformers import CrossEncoder
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Initialize Cross-Encoder Model at import time (eager loading for faster first query)
_reranker_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", max_length=512)


def get_reranker():
    return _reranker_model


def rerank_documents(
    query: str, documents: List[Dict[str, Any]], top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    Reranks a list of documents based on their relevance to the query using a Cross-Encoder.

    Args:
        query: The user's search query.
        documents: List of dicts, each must have 'content' and 'id' keys.
        top_k: Number of top results to return.

    Returns:
        List of documents sorted by relevance score (descending), limited to top_k.
    """
    if not documents:
        return []

    reranker = get_reranker()

    # Prepare pairs for the model: [[query, doc1], [query, doc2], ...]
    pairs = [[query, doc["content"]] for doc in documents]

    # Predict scores
    scores = reranker.predict(pairs)

    # Attach scores to documents
    for i, doc in enumerate(documents):
        doc["rerank_score"] = float(scores[i])

    # Sort by new score (Descending)
    ranked_docs = sorted(documents, key=lambda x: x["rerank_score"], reverse=True)

    return ranked_docs[:top_k]
