import numpy as np
from typing import List, Dict, Any


class DiversityReranker:
    """
    Implements Maximal Marginal Relevance (MMR) to re-rank documents
    based on a balance of relevance (to query) and diversity (dissimilarity to selected results).
    """

    def __init__(self):
        pass

    def compute_cosine_similarity(self, v1: np.ndarray, v2: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        if norm_v1 == 0 or norm_v2 == 0:
            return 0.0
        return np.dot(v1, v2) / (norm_v1 * norm_v2)

    def rerank(
        self,
        query_embedding: List[float],
        candidates: List[Dict[str, Any]],
        final_k: int,
        lambda_mult: float = 0.6,
    ) -> List[Dict[str, Any]]:
        """
        Applies MMR to select the top 'final_k' diverse documents.

        Args:
            query_embedding: Embedding vector of the query.
            candidates: List of documents. MUST contain 'embedding' key (List[float]).
            final_k: Number of documents to select.
            lambda_mult: Diversity trade-off.
                         1.0 = Pure Relevance (Standard Search).
                         0.0 = Pure Diversity (Maximum dissimilarity).
                         0.5 = Balanced.

        Returns:
            List of selected documents in ranked order. Each doc gets a 'diversity_score'.
        """
        if not candidates:
            return []

        # Ensure inputs are numpy arrays
        query_vec = np.array(query_embedding)

        # Pre-calculate relevance scores (Sim(d, q)) for all candidates
        # and store vectors as numpy arrays for speed
        pool = []
        for doc in candidates:
            emb = doc.get("embedding")
            if emb is None:
                continue

            # Handle both list and numpy array emptiness checks
            if isinstance(emb, (list, tuple)) and len(emb) == 0:
                continue
            if isinstance(emb, np.ndarray) and emb.size == 0:
                continue

            doc_vec = np.array(emb)
            relevance = self.compute_cosine_similarity(query_vec, doc_vec)

            pool.append(
                {
                    "doc": doc,
                    "vec": doc_vec,
                    "relevance": relevance,
                    "id": doc.get("id"),
                }
            )

        if not pool:
            return []

        # MMR Selection Loop
        selected_indices = []
        selected_docs = []

        # Limit K to pool size
        k = min(final_k, len(pool))

        for _ in range(k):
            best_mmr = -float("inf")
            best_idx = -1

            for i, item in enumerate(pool):
                if i in selected_indices:
                    continue

                # Calculate Redundancy (Sim(d, selected))
                # If no docs selected yet, redundancy is 0
                max_sim_to_selected = 0.0
                for sel_idx in selected_indices:
                    sim = self.compute_cosine_similarity(
                        item["vec"], pool[sel_idx]["vec"]
                    )
                    if sim > max_sim_to_selected:
                        max_sim_to_selected = sim

                # MMR Equation
                # MMR = lambda * Relevance - (1 - lambda) * MaxSimToSelected
                mmr_score = (lambda_mult * item["relevance"]) - (
                    (1 - lambda_mult) * max_sim_to_selected
                )

                if mmr_score > best_mmr:
                    best_mmr = mmr_score
                    best_idx = i

            # Select the winner
            if best_idx != -1:
                selected_indices.append(best_idx)
                winner = pool[best_idx]["doc"]
                winner["diversity_score"] = float(best_mmr)  # Add score for debugging
                winner["relevance_score"] = float(pool[best_idx]["relevance"])
                selected_docs.append(winner)

        return selected_docs
