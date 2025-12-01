import asyncio
import re
import os
import logging
from datetime import datetime
from typing import List, Optional
import google.generativeai as genai

logger = logging.getLogger(__name__)

# Backend imports
from embeddings import get_embedding
from database import get_collection
from reranker import rerank_documents
from diversity import DiversityReranker
from core.config import GEMINI_API_KEY
from core.model_state import model_config
from core.constants import (
    SEARCH_INITIAL_LIMIT,
    KEYWORD_SEARCH_LIMIT,
    DEFAULT_MAX_CHUNKS_PER_SOURCE,
    DATASET_MAX_CHUNKS_PER_SOURCE,
)
from api.schemas import SearchResult, SearchRequest

class SearchService:
    def __init__(self):
        self.diversity_reranker = DiversityReranker()
        if GEMINI_API_KEY:
            genai.configure(api_key=GEMINI_API_KEY)

    async def _generate_query_variations(
        self, original_query: str, target_language: str
    ) -> List[str]:
        """Generates multiple query variations using Gemini, including an alternate language."""
        if not GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY not found - skipping query variations")
            return [original_query]

        model = genai.GenerativeModel(model_config.get_model("fast")) # Using a fast, lightweight model

        alt_language = "French" if target_language == "en" else "English"
        language_instruction = f"The variations should be in {target_language}. Also provide ONE variation in {alt_language}."

        prompt = f"""You are a helpful assistant that rephrases search queries to improve retrieval recall.
        Generate 3 distinct semantic variations of the following query. 
        
        CRITICAL: If the query refers to a specific legislative bill, act, or named entity (e.g., "Bill C-4"), you MUST generate variations that explicitly ask for "history of...", "all versions of...", or "different years of..." to ensure all relevant instances are retrieved, not just the most recent one.

        {language_instruction}

        Original Query: "{original_query}"

        Provide the variations as a comma-separated list, e.g., "query 1, query 2, query 3, query 4 (in French)".
        Be concise and avoid conversational filler.
        """

        try:
            response = await model.generate_content_async(
                prompt,
                generation_config={"temperature": 0.3, "max_output_tokens": 200},
            )
            # Attempt to parse the comma-separated list.
            # Clean up any potential markdown or extra spaces.
            variations_raw = response.text.strip()
            variations_raw = variations_raw.replace('"', '').strip()
            variations = [v.strip() for v in variations_raw.split(",") if v.strip()]

            # Ensure the original query is always included
            if original_query not in variations:
                variations.insert(0, original_query) # Add to the beginning

            logger.debug(f"Generated {len(variations)} query variations")
            return variations
        except Exception as e:
            logger.error(f"Error generating query variations: {e}")
            return [original_query] # Fallback to original query on error

    async def search(self, request: SearchRequest) -> List[SearchResult]:
        try:
            collection = get_collection()

            # 1. Embed Query (single embedding - fast mode)
            query_emb = get_embedding(request.query)
            if not query_emb:
                raise Exception("Failed to generate query embedding.")

            # 2. Build Filters
            where_filter = {"language": request.language}

            # Add category filter if specified
            if request.categories and len(request.categories) > 0:
                where_filter = {
                    "$and": [
                        {"language": request.language},
                        {"category": {"$in": request.categories}}
                    ]
                }
                logger.debug(f"Category filter applied: {len(request.categories)} categories")

            # 3. Query DB - reduced limit for speed, only fetch embeddings for MMR
            initial_limit = SEARCH_INITIAL_LIMIT

            # Only include embeddings if using diverse/MMR strategy
            include_fields = ["documents", "metadatas", "distances"]
            if request.strategy == "diverse":
                include_fields.append("embeddings")

            # Single vector search (no query expansion for maximum speed)
            vector_result = await asyncio.to_thread(
                collection.query,
                query_embeddings=[query_emb],
                n_results=initial_limit,
                where=where_filter,
                include=include_fields,
            )

            vector_search_results = [vector_result]
            original_query_emb = query_emb  # Alias for compatibility

            # Process and merge results from all vector searches
            candidates = {}  # Map id -> candidate_obj to deduplicate

            # Helper to process a result batch
            def process_batch(res_batch, is_keyword_match=False):
                if not res_batch or not res_batch["ids"]:
                    return

                b_ids = res_batch["ids"][0]
                b_dists = res_batch["distances"][0]
                b_metas = res_batch["metadatas"][0]
                b_docs = res_batch["documents"][0]
                b_embs = []
                if "embeddings" in res_batch and res_batch["embeddings"] is not None:
                    emb_data = res_batch["embeddings"]
                    if emb_data and len(emb_data) > 0:
                        b_embs = emb_data[0] if emb_data[0] is not None else []

                for i in range(len(b_ids)):
                    doc_id = b_ids[i]

                    # If it exists, keep the one with the higher score (lower distance)
                    if doc_id in candidates:
                        current_score = candidates[doc_id]["score"]
                        new_score = 1.0 - b_dists[i]
                        if new_score > current_score: 
                             candidates[doc_id]["score"] = new_score
                        if is_keyword_match: 
                            candidates[doc_id]["is_keyword_match"] = True
                        continue

                    meta = b_metas[i]
                    # Date Logic (Time Travel)
                    start_date_str = meta.get("effective_date_start")
                    if start_date_str:
                        try:
                            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
                            ref_date_obj = datetime.now()
                            if request.reference_date:
                                ref_date_obj = datetime.strptime(
                                    request.reference_date, "%Y-%m-%d"
                                )
                            if start_date > ref_date_obj:
                                continue
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Date parsing failed for '{start_date_str}': {e}")

                    candidates[doc_id] = {
                        "id": doc_id,
                        "content": b_docs[i],
                        "source_title": meta.get("source_title", "Unknown"),
                        "score": 1.0 - b_dists[i],
                        "metadata": meta,
                        "is_keyword_match": is_keyword_match,
                        "embedding": b_embs[i] if i < len(b_embs) else None,
                    }

            # Process all vector search results
            for res in vector_search_results:
                process_batch(res)

            # PATH B: Dynamic Keyword Search (Identifier Extraction) - only for bill numbers
            keyword_results_list = []
            keywords = re.findall(r"\b[\w-]*\d[\w-]*\b", request.query)
            if keywords:
                raw_keyword = keywords[0].upper()
                variants = {raw_keyword}
                if re.match(r"^[A-Z]\d+$", raw_keyword):
                    variants.add(f"{raw_keyword[0]}-{raw_keyword[1:]}")
                if re.match(r"^[A-Z]-\d+$", raw_keyword):
                    variants.add(raw_keyword.replace("-", ""))

                for target_kw in variants:
                    try:
                        kw_res = await asyncio.to_thread(
                            collection.query,
                            query_embeddings=[original_query_emb],
                            n_results=KEYWORD_SEARCH_LIMIT,
                            where=where_filter,
                            where_document={"$contains": target_kw},
                            include=include_fields,
                        )

                        # STRICT FILTERING: Enforce word boundaries
                        if kw_res and kw_res["ids"] and kw_res["ids"][0]:
                            filtered_ids = []
                            filtered_dists = []
                            filtered_metas = []
                            filtered_docs = []
                            filtered_embs = []

                            pattern = r"\b" + re.escape(target_kw) + r"\b"

                            for i, doc_content in enumerate(kw_res["documents"][0]):
                                if re.search(pattern, doc_content, re.IGNORECASE):
                                    filtered_ids.append(kw_res["ids"][0][i])
                                    filtered_dists.append(kw_res["distances"][0][i])
                                    filtered_metas.append(kw_res["metadatas"][0][i])
                                    filtered_docs.append(doc_content)
                                    if "embeddings" in kw_res and kw_res["embeddings"] and kw_res["embeddings"][0]:
                                        filtered_embs.append(kw_res["embeddings"][0][i])

                            if filtered_ids:
                                result_dict = {
                                    "ids": [filtered_ids],
                                    "distances": [filtered_dists],
                                    "metadatas": [filtered_metas],
                                    "documents": [filtered_docs],
                                }
                                if filtered_embs:
                                    result_dict["embeddings"] = [filtered_embs]
                                keyword_results_list.append(result_dict)
                    except Exception as e:
                        logger.warning(f"Keyword query error: {e}")

            for kr in keyword_results_list:
                process_batch(kr, is_keyword_match=True)

            candidate_list = list(candidates.values())

            # --- THEME FILTERING (Post-processing) ---
            if request.themes and len(request.themes) > 0:
                logger.debug(f"Theme filter applied: {len(request.themes)} themes")
                filtered_by_theme = []
                for doc in candidate_list:
                    doc_themes = doc["metadata"].get("themes", "").lower()
                    # Check if any requested theme matches (partial match)
                    matches = any(
                        theme.lower() in doc_themes
                        for theme in request.themes
                    )
                    if matches:
                        filtered_by_theme.append(doc)
                candidate_list = filtered_by_theme
                logger.debug(f"Candidates after theme filter: {len(candidate_list)}")

            # --- SOURCE DIVERSITY FILTERING (Throttling) ---
            candidate_list.sort(key=lambda x: x["score"], reverse=True)

            source_counts = {}
            filtered_candidate_list = []

            for doc in candidate_list:
                sid = doc["metadata"].get("source_id", doc.get("source_title", "unknown"))
                doc_type = str(doc["metadata"].get("doc_type", "")).lower()
                category = str(doc["metadata"].get("category", "")).lower()

                limit = DEFAULT_MAX_CHUNKS_PER_SOURCE
                if doc_type == "csv" or category == "dataset":
                    limit = DATASET_MAX_CHUNKS_PER_SOURCE

                if source_counts.get(sid, 0) < limit:
                    filtered_candidate_list.append(doc)
                    source_counts[sid] = source_counts.get(sid, 0) + 1

            candidate_list = filtered_candidate_list
            
            dist = {}
            for d in candidate_list:
                sid = d["metadata"].get("source_id", "unknown")
                dist[sid] = dist.get(sid, 0) + 1
            logger.debug(f"Source distribution: {len(dist)} unique sources")

            # 5. RERANKING STRATEGY
            ranked_results = []

            if request.strategy == "diverse":
                logger.debug(f"Applying diversity reranking (lambda={request.diversity_lambda})")
                ranked_results = self.diversity_reranker.rerank(
                    original_query_emb,
                    candidate_list,
                    final_k=request.limit,
                    lambda_mult=request.diversity_lambda,
                )
            else:
                ranked_results = rerank_documents(
                    request.query, candidate_list, top_k=len(candidate_list)
                ) 

                for doc in ranked_results:
                    if doc.get("is_keyword_match"):
                        doc["rerank_score"] += 20.0

                ranked_results = sorted(
                    ranked_results, key=lambda x: x["rerank_score"], reverse=True
                )
                ranked_results = ranked_results[: request.limit]

            logger.debug(f"Results after reranking ({request.strategy}): {len(ranked_results)}")

            # 7. Format Response
            final_results = []
            for doc in ranked_results:
                final_results.append(
                    SearchResult(
                        id=doc["id"],
                        content=doc["content"],
                        source_title=doc["source_title"],
                        score=doc.get("score", 0.0),
                        rerank_score=doc.get("rerank_score", 0.0)
                        or doc.get("diversity_score", 0.0),
                        metadata=doc["metadata"],
                    )
                )

            return final_results

        except Exception as e:
            logger.error(f"Search failed: {type(e).__name__}")
            raise e
