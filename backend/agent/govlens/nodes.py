import re
import json
import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

from embeddings import get_embedding
from database import get_collection
from reranker import rerank_documents

try:
    from diversity import DiversityReranker
except ImportError:
    from .diversity import DiversityReranker

from .state import GovLensState
from agent.core import get_llm, parse_govlens_response
from core.model_state import model_config

# Lazy LLM initialization - created on first use
def get_langchain_llm():
    """Get LangChain LLM lazily (only when API key is configured)."""
    return get_llm(model=model_config.get_model("fast"), temperature=0).langchain

diversity_reranker = DiversityReranker()


# --- Models for Structured Output ---
class RouterOutput(BaseModel):
    strategy: str = Field(description="The strategy to use: 'simple' or 'complex'")
    reason: str = Field(description="Why this strategy was chosen")


class GradeOutput(BaseModel):
    relevant: bool = Field(description="Are the documents relevant to the query?")
    missing_info: str = Field(description="What specific info is missing, if any")


# --- NODES ---


async def router_node(state: GovLensState) -> Dict[str, Any]:
    """
    Classifies the user query to determine the RAG strategy.
    """
    logger.debug("--- ROUTER NODE ---")
    query = state["query"]

    prompt = PromptTemplate(
        template="""You are a senior research librarian. Analyze the following user query and decide on a search strategy.

        Query: "{query}"

        Strategies:
        - \"simple\": For specific, factual questions, definitions, or single-document lookups (e.g., \"What is the effective date of Bill C-13?\", \"Define 'personal information'\").
        - \"complex\": For broad topics, comparisons, summaries of multiple concepts, or questions requiring synthesis of scattered information (e.g., \"Summarize the privacy implications of recent AI legislation\", \"How does the oversight mechanism differ between the two acts?\").

        Return JSON: {{ "strategy": "simple" | "complex", "reason": "string" }}
        """,
        input_variables=["query"],
    )

    chain = prompt | get_langchain_llm() | JsonOutputParser(pydantic_object=RouterOutput)

    try:
        result = await chain.ainvoke({"query": query})
        strategy = result.get("strategy", "simple").lower()
        if strategy not in ["simple", "complex"]:
            strategy = "simple"  # Fallback

        logger.debug(f"Selected Strategy: {strategy}")
        return {
            "search_strategy": strategy,
            "trace_log": [
                f"Router: Selected '{strategy}' strategy. Reason: {result.get('reason')}"
            ],
        }
    except Exception as e:
        logger.warning(f"Router failed: {type(e).__name__}. Defaulting to simple.")
        return {
            "search_strategy": "simple",
            "trace_log": ["Router: Error, defaulting to simple mode."],
        }


async def retrieve_node(state: GovLensState) -> Dict[str, Any]:
    """
    Retrieves documents based on the latest generated query.
    Uses Hybrid Search (Vector + Keyword) and Reranking.
    Now Async and Parallelized.
    """
    logger.debug("--- RETRIEVE NODE ---")
    query = (
        state["generated_queries"][-1] if state["generated_queries"] else state["query"]
    )
    language = state.get("language", "en")
    categories = state.get("categories")
    themes = state.get("themes")

    # Target final count
    final_limit = 20
    initial_limit = 500

    collection = get_collection()

    # Build where filter (with optional category filter)
    where_filter = {"language": language}
    if categories and len(categories) > 0:
        where_filter = {
            "$and": [
                {"language": language},
                {"category": {"$in": categories}}
            ]
        }
        logger.debug(f"Category filter applied: {len(categories)} categories")

    # 1. Multi-Query Generation (Async)
    queries_to_search = [query]
    try:
        logger.debug("Generating query variations")
        alt_lang = "French" if language == "en" else "English"

        mq_prompt = PromptTemplate(
             template="""You are a helpful assistant that rephrases search queries to improve retrieval recall.
            Generate 3 distinct semantic variations of the following query.

            CRITICAL: If the query refers to a specific legislative bill, act, or named entity (e.g., "Bill C-4"), you MUST generate variations that explicitly ask for "history of...", "all versions of...", or "different years of..." to ensure all relevant instances are retrieved, not just the most recent one.

            The variations should be in {language}. Also provide ONE variation in {alt_lang}.

            Original Query: "{query}"

            Provide the variations as a comma-separated list, e.g., "query 1, query 2, query 3, query 4 (in French)".
            Be concise and avoid conversational filler.
            """,
            input_variables=["query", "language", "alt_lang"]
        )

        mq_chain = mq_prompt | get_langchain_llm()
        mq_response = await mq_chain.ainvoke({
            "query": query, "language": language, "alt_lang": alt_lang
        })

        variations_raw = mq_response.content.strip().replace('"', '')
        variations = [v.strip() for v in variations_raw.split(",") if v.strip()]

        # Add variations to search list
        for v in variations:
            if v and v not in queries_to_search:
                queries_to_search.append(v)

        logger.debug(f"Searching with {len(queries_to_search)} query variations")

    except Exception as e:
        logger.warning(f"Multi-Query Generation failed: {type(e).__name__}. Using original query only.")

    # 2. Parallel Embedding & Vector Search
    async def search_single_query(q_text):
        try:
            # Wrap blocking get_embedding
            q_emb = await asyncio.to_thread(get_embedding, q_text)
            if not q_emb:
                return None

            # Wrap blocking collection.query
            res = await asyncio.to_thread(
                collection.query,
                query_embeddings=[q_emb],
                n_results=initial_limit,
                where=where_filter,
                include=["documents", "metadatas", "distances", "embeddings"],
            )
            return res
        except Exception as ex:
            logger.warning(f"Vector search failed: {type(ex).__name__}")
            return None

    # Run all vector searches
    vector_results = await asyncio.gather(*[search_single_query(q) for q in queries_to_search])

    # 3. Keyword Search (Async Wrapper)
    # Only run keyword search on the ORIGINAL query to avoid noise
    keyword_results_list = []
    keywords = re.findall(r"\b[\w-]*\d[\w-]*\b", query)
    if keywords:
        raw_keyword = keywords[0].upper()
        variants = {raw_keyword}
        if re.match(r"^[A-Z]\d+$", raw_keyword):
            variants.add(f"{raw_keyword[0]}-{raw_keyword[1:]}")
        if re.match(r"^[A-Z]-\d+$", raw_keyword):
            variants.add(raw_keyword.replace("-", ""))

        logger.debug(f"Dynamic keyword search: {len(variants)} variants")

        # Use the embedding of the original query for the keyword search (required by chroma api)
        # We can reuse the first result if available, or re-embed
        orig_emb = await asyncio.to_thread(get_embedding, query)

        async def search_keyword(kw):
            try:
                return await asyncio.to_thread(
                    collection.query,
                    query_embeddings=[orig_emb],
                    n_results=initial_limit,
                    where=where_filter,
                    where_document={"$contains": kw},
                    include=["documents", "metadatas", "distances", "embeddings"],
                )
            except Exception as ex:
                logger.warning(f"Keyword search failed: {type(ex).__name__}")
                return None

        kw_results_raw = await asyncio.gather(*[search_keyword(kw) for kw in variants])

        # Post-process keyword results (strict filtering)
        for i, kw_res in enumerate(kw_results_raw):
            target_kw = list(variants)[i]
            if kw_res and kw_res["ids"] and kw_res["ids"][0]:
                filtered_ids = []
                filtered_dists = []
                filtered_metas = []
                filtered_docs = []
                filtered_embs = []

                pattern = r"\b" + re.escape(target_kw) + r"\b"

                for j, doc_content in enumerate(kw_res["documents"][0]):
                    if re.search(pattern, doc_content, re.IGNORECASE):
                        filtered_ids.append(kw_res["ids"][0][j])
                        filtered_dists.append(kw_res["distances"][0][j])
                        filtered_metas.append(kw_res["metadatas"][0][j])
                        filtered_docs.append(doc_content)
                        filtered_embs.append(kw_res["embeddings"][0][j])

                if filtered_ids:
                    keyword_results_list.append(
                        {
                            "ids": [filtered_ids],
                            "distances": [filtered_dists],
                            "metadatas": [filtered_metas],
                            "documents": [filtered_docs],
                            "embeddings": [filtered_embs],
                        }
                    )

    # 4. Merge Candidates
    candidates = {}  # Map id -> candidate_obj

    def process_batch(res_batch, is_keyword_match=False):
        if not res_batch or not res_batch["ids"]:
            return

        b_ids = res_batch["ids"][0]
        b_dists = res_batch["distances"][0]
        b_metas = res_batch["metadatas"][0]
        b_docs = res_batch["documents"][0]
        b_embs = (
            res_batch.get("embeddings", [[]])[0] if "embeddings" in res_batch else []
        )

        for i in range(len(b_ids)):
            doc_id = b_ids[i]

            if doc_id in candidates:
                # Update score if better
                current_score = candidates[doc_id]["score"]
                new_score = 1.0 - b_dists[i]
                if new_score > current_score:
                     candidates[doc_id]["score"] = new_score

                if is_keyword_match:
                    candidates[doc_id]["is_keyword_match"] = True
                continue

            meta = b_metas[i]
            # Simple Date Check (Time Travel)
            start_date_str = meta.get("effective_date_start")
            if start_date_str:
                try:
                    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
                    if start_date > datetime.now():
                        continue
                except (ValueError, TypeError) as e:
                    logger.debug(f"Could not parse effective_date_start '{start_date_str}': {e}")

            candidates[doc_id] = {
                "id": doc_id,
                "content": b_docs[i],
                "source_title": meta.get("source_title", "Unknown"),
                "score": 1.0 - b_dists[i],
                "metadata": meta,
                "is_keyword_match": is_keyword_match,
                "embedding": b_embs[i] if i < len(b_embs) else None,
            }

    for vr in vector_results:
        if vr: process_batch(vr, is_keyword_match=False)

    for kr in keyword_results_list:
        process_batch(kr, is_keyword_match=True)

    candidate_list = list(candidates.values())

    # --- THEME FILTERING (Post-processing) ---
    if themes and len(themes) > 0:
        logger.debug(f"Theme filter applied: {len(themes)} themes")
        filtered_by_theme = []
        for doc in candidate_list:
            doc_themes = doc["metadata"].get("themes", "").lower()
            # Check if any requested theme matches (partial match)
            matches = any(
                theme.lower() in doc_themes
                for theme in themes
            )
            if matches:
                filtered_by_theme.append(doc)
        candidate_list = filtered_by_theme
        logger.debug(f"Candidates after theme filter: {len(candidate_list)}")

    # --- SOURCE DIVERSITY FILTERING ---
    candidate_list.sort(key=lambda x: x["score"], reverse=True)

    DEFAULT_MAX_CHUNKS = 3
    DATASET_MAX_CHUNKS = 500
    source_counts = {}
    filtered_candidate_list = []

    for doc in candidate_list:
        sid = doc["metadata"].get("source_id", doc.get("source_title", "unknown"))
        doc_type = str(doc["metadata"].get("doc_type", "")).lower()
        category = str(doc["metadata"].get("category", "")).lower()

        limit = DEFAULT_MAX_CHUNKS
        if doc_type == "csv" or category == "dataset":
            limit = DATASET_MAX_CHUNKS

        if source_counts.get(sid, 0) < limit:
            filtered_candidate_list.append(doc)
            source_counts[sid] = source_counts.get(sid, 0) + 1

    candidate_list = filtered_candidate_list

    # Debug Print
    logger.debug(f"Merged {len(candidate_list)} candidates from {len(queries_to_search)} queries")

    # 5. Rerank Strategy (MMR)
    logger.debug("Using Diversity Reranker (MMR)")

    # Need an embedding for MMR reference. Use original query embedding.
    # If we haven't computed it yet (e.g. only keyword search ran), compute now.
    # But we did compute 'queries_to_search[0]' which is original query.
    # We can just re-call get_embedding or assume we have it.
    # For simplicity, re-call wrapped:
    ref_emb = await asyncio.to_thread(get_embedding, query)

    ranked_results = await asyncio.to_thread(
        diversity_reranker.rerank,
        ref_emb, candidate_list, final_k=final_limit, lambda_mult=0.7
    )

    new_docs = []
    doc_metadata = state.get("doc_metadata") or {}

    for doc in ranked_results:
        doc_str = f"[Document ID: {doc['id']}] [Source: {doc['source_title']}] Content: {doc['content']}"
        new_docs.append(doc_str)

        # Store metadata for citation enrichment later
        doc_metadata[doc['id']] = {
            "source_title": doc.get('source_title', 'Unknown'),
            "category": doc.get('metadata', {}).get('category', ''),
        }

    # Calculate retrieval confidence from document scores
    if ranked_results:
        scores = [doc.get('score', 0) for doc in ranked_results]
        top_3_avg = sum(scores[:3]) / min(3, len(scores))  # Average of top 3 scores
        coverage = min(len(ranked_results) / 5, 1.0)  # Normalize: 5+ docs = full coverage
        retrieval_confidence = (top_3_avg * 0.7) + (coverage * 0.3)  # Weighted blend
    else:
        retrieval_confidence = 0.0

    # Store retrieval confidence for generate_node
    doc_metadata["_retrieval_confidence"] = retrieval_confidence

    logger.debug(f"Retrieved {len(new_docs)} documents (confidence: {retrieval_confidence:.2f})")

    return {
        "documents": new_docs,
        "doc_metadata": doc_metadata,
        "trace_log": [f"Retrieved {len(new_docs)} documents for query: '{query}' (used {len(queries_to_search)} variations)"],
        "loop_count": state["loop_count"] + 1,
    }


async def grade_documents_node(state: GovLensState) -> Dict[str, Any]:
    """
    [Complex Path Only] Grades if the retrieved documents are sufficient to answer the query.
    """
    logger.debug("--- GRADE DOCUMENTS NODE ---")
    query = state["query"]
    docs = "\n\n".join(state["documents"])

    prompt = PromptTemplate(
        template="""You are a research evaluator.
        User Query: "{query}"

        Retrieved Documents:
        {documents}

        Do these documents contain sufficient information to comprehensively answer the user query?
        If NO, identify what is missing to generate a better search query.

        Return JSON: {{ "relevant": boolean, "missing_info": "string" }}
        """,
        input_variables=["query", "documents"],
    )

    chain = prompt | get_langchain_llm() | JsonOutputParser(pydantic_object=GradeOutput)

    try:
        # Async invoke
        result = await chain.ainvoke(
            {"query": query, "documents": docs[:10000]}
        )
        is_relevant = result.get("relevant", True)
        missing = result.get("missing_info", "")

        log = (
            "Documents graded as relevant."
            if is_relevant
            else f"Information missing: {missing}"
        )

        return {
            "trace_log": [f"Grader: {log}"],
            "missing_info": missing,
        }
    except Exception as e:
        logger.warning(f"Grading failed: {type(e).__name__}")
        return {"trace_log": ["Grader: Error, proceeding to synthesis."]}


async def rewrite_query_node(state: GovLensState) -> Dict[str, Any]:
    """
    [Complex Path Only] Rewrites the query based on missing info to find better documents.
    """
    logger.debug("--- REWRITE QUERY NODE ---")
    original_query = state["query"]

    last_log = state["trace_log"][-1] if state["trace_log"] else ""
    missing_context = ""
    if "Information missing:" in last_log:
        missing_context = f"Focus on finding this missing information: {last_log.split('Information missing:')[1]}"

    prompt = PromptTemplate(
        template="""The original query was: "{query}"

        {missing_context}

        Based on this, generate a BETTER, targeted search query to find missing details.
        Focus on keywords that might appear in legislation or policy documents.

        Return only the new query string.
        """,
        input_variables=["query", "missing_context"],
    )

    chain = prompt | get_langchain_llm()
    try:
        response = await chain.ainvoke(
            {"query": original_query, "missing_context": missing_context}
        )
        new_query = response.content.strip() or original_query
        trace_msg = f"Rewriter: Generated new query '{new_query}'"
    except Exception as e:
        logger.warning(f"Rewrite failed: {type(e).__name__}. Using original query.")
        new_query = original_query
        trace_msg = f"Rewriter: Error, falling back to original query. Detail: {e}"

    logger.debug("Query rewritten")
    return {
        "generated_queries": [new_query],
        "trace_log": [trace_msg],
    }


async def generate_node(state: GovLensState) -> Dict[str, Any]:
    """
    Synthesizes the final answer using RAG.
    """
    logger.debug("--- GENERATE NODE ---")
    query = state["query"]
    docs = "\n\n".join(state["documents"])
    language = state.get("language", "en")

    system_prompt = """You are GovLens, an AI assistant for the Canadian Government.
    Answer the user's query based ONLY on the provided documents.

    Structure your response strictly as JSON:
    {{
      "answer": "Comprehensive summary answer...",
      "lang": "en" or "fr",
      "bullets": ["Key point 1", "Key point 2"],
      "citations": [{{"doc_id": "string", "locator": "string"}}],
      "confidence": float (0.0 to 1.0),
      "abstained": boolean (true if you cannot answer from context)
    }}

    Rules:
    1. Citations are MANDATORY but should be used sparingly. Cite once per paragraph or logical section, not after every sentence.
    2. If language is 'fr', answer in French.
    3. Be professional and precise.
    4. DISAMBIGUATION: If the documents contain multiple distinct entities, laws, projects, or concepts with the same name or identifier (e.g., the same Bill number from different years, or a project name used in different contexts), you MUST list them separately. Clearly distinguish each by its specific context (e.g., Year, Department, Topic) to avoid merging unrelated information.
    5. STRUCTURE: Improve readability by formatting the 'answer' field with Markdown:
       - Break text into multiple short paragraphs using double newlines (\\n\\n).
       - Use bullet points to list distinct items, actions, or timeline events.
    6. CITATION FORMAT: In the "answer" and "bullets" text, cite sources using numbered references like [1], [2], [3].
       - Numbers must appear in sequential order of first appearance (first cite is [1], second new source is [2], etc.)
       - The "citations" array MUST be ordered to match: citations[0] corresponds to [1], citations[1] to [2], etc.
       - IMPORTANT: Cite each source ONCE per paragraph at the END of the relevant content. Do NOT repeat the same citation multiple times within a paragraph.
       - Group related facts from the same source together, then cite once at the end.
       - Example: "Bill C-3 was introduced on January 27, 2020 to expand civilian review. It passed first reading but died on the Order Paper in August 2020 due to COVID-19 delays [1]."
       - Do NOT use doc_id values like (qpnotes-row-123) or (Document ID) inline in the answer text. Use [N] instead.
    """

    prompt = PromptTemplate(
        template=system_prompt
        + "\n\nContext:\n{context}\n\nUser Query: {query}\n\nJSON Response:",
        input_variables=["context", "query"],
    )

    # Use Reasoning Model for final generation
    reasoning_service = get_llm(model=model_config.get_model("reasoning"), temperature=0.1)
    chain = prompt | reasoning_service.langchain

    try:
        # Truncate docs to avoid extremely long contexts
        truncated_docs = docs[:500000]
        logger.debug(f"Calling LLM with {len(truncated_docs)} chars of context")
        response = await chain.ainvoke({"context": truncated_docs, "query": query})
        logger.debug("LLM response received")
        raw_json = response.content.strip()

        # Use shared parsing with comprehensive fallback and citation deduplication
        data = parse_govlens_response(raw_json, language)

        # Enrich citations with titles from doc_metadata
        doc_metadata = state.get("doc_metadata") or {}
        enriched_citations = []
        for cit in data.get("citations", []):
            if isinstance(cit, dict):
                doc_id = cit.get("doc_id", "")
                meta = doc_metadata.get(doc_id, {})
                enriched_cit = {
                    **cit,
                    "title": meta.get("source_title", ""),
                    "category": meta.get("category", cit.get("category", "")),
                    "snippet": cit.get("locator", ""),  # Use locator as snippet for display
                }
                enriched_citations.append(enriched_cit)
            else:
                enriched_citations.append(cit)
        data["citations"] = enriched_citations

        # Calculate confidence algorithmically from retrieval scores (not LLM self-report)
        raw_confidence = doc_metadata.get("_retrieval_confidence", 0.5)
        # Scale to intuitive range (raw 0.3-0.6 → displayed 0.6-0.95)
        scaled_confidence = min(raw_confidence * 1.4 + 0.15, 0.98)
        final_confidence = scaled_confidence
        if data.get("abstained"):
            final_confidence = min(final_confidence, 0.3)  # Cap at 0.3 if abstained
        elif len(enriched_citations) == 0:
            final_confidence *= 0.7  # Reduce if no citations provided
        data["confidence"] = round(final_confidence, 2)

        final_json_str = json.dumps(data)

        return {
            "final_answer": final_json_str,
            "trace_log": ["Final Answer Generated."],
        }
    except Exception as e:
        logger.error(f"Generation Node Critical Error: {type(e).__name__}")
        error_data = {
            "answer": f"Error generating response: {str(e)}",
            "abstained": True,
            "citations": [],
            "bullets": [],
        }
        return {
            "final_answer": json.dumps(error_data),
            "trace_log": [f"Generation Error: {e}"],
        }
