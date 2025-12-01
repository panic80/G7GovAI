import os
import chromadb
import logging
from typing import List, Optional, Dict, Generator, Union, Any, AsyncGenerator
import google.generativeai as genai
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
import datetime
from bs4 import BeautifulSoup
import re
from pathlib import Path
import csv
from tqdm import tqdm
import concurrent.futures
import sys
import json

logger = logging.getLogger(__name__)

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

# Add current directory to path to allow importing embeddings if run directly
script_dir = Path(__file__).resolve().parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

# Use absolute imports - backend dir should be in sys.path
from embeddings import get_embeddings_batch
from core.model_state import model_config
from core.constants import ANALYSIS_MAX_WORKERS, ANALYSIS_BATCH_SIZE, EMBEDDING_MAX_WORKERS
from core.adaptive_rate_limiter import gemini_limiter

# 1. Load Environment Variables
env_path = script_dir.parent / ".env.local"
load_dotenv(dotenv_path=env_path)

# 1.1. Categorization model - initialized lazily via model_config
# See get_categorization_model() function below


def get_categorization_model(model_type: str = "fast"):
    """
    Get Gemini model for categorization, using model_config API key.

    Returns None if API key not configured (categorization will be skipped).
    """
    if not model_config.ensure_configured():
        logger.warning("API key not configured - categorization will be skipped")
        return None
    return genai.GenerativeModel(model_config.get_model(model_type))

# 2. Setup ChromaDB
DB_DIR = script_dir / "chroma_db"
client = chromadb.PersistentClient(path=str(DB_DIR))
collection = client.get_or_create_collection(
    name="gov_knowledge_base", embedding_function=None
)

# 3. Helper: Embedding Function (OpenAI)
logger.info("Using shared OpenAI embedding model from embeddings.py")


# Helper for text cleaning
def clean_text(text: str) -> str:
    # Clean up excessive whitespace and newlines
    clean_text = re.sub(r"\n\s*\n", "\n\n", text).strip()
    clean_text = re.sub(r"\s+", " ", clean_text).strip()
    return clean_text


# Helper for categorization and theme extraction using Gemini
def analyze_document(text: str, model_name: str = None) -> Dict[str, str]:
    # Get model using model_config (lazy initialization)
    # Use "fast" model (gemini-2.5-flash-lite, 4000 RPM) not "reasoning" (gemini-2.5-pro, 150 RPM)
    model = get_categorization_model("fast")
    if not model:
        return {"category": "Unknown", "themes": "", "title": ""}

    try:

        prompt = f"""Analyze this document excerpt (first {len(text[:2000])} chars) and extract metadata.
        
        Target Information:
        1. Title: The official document title.
           - Look for large headers, "Act", "Regulation", "Policy", or specific government titles.
           - If bilingual (English/French), format as "English Title / French Title".
           - If the text contains "SOR/..." or "C.R.C., c. ...", try to find the corresponding descriptive title.
           - If no clear title is found, return "null".
        2. Category: ONE from [Policy, Press Release, Guidance, Report, Info, Legal, Technical, Form, Dataset, Other].
        3. Themes: 1-3 key topics (comma separated).

        Text Excerpt:
        ---
        {text[:2000]}
        ---

        Output strictly as valid JSON:
        {{
            "title": "Extracted Title or null",
            "category": "Category Name",
            "themes": "Theme 1, Theme 2"
        }}
        """

        response = model.generate_content(
            prompt, generation_config={"response_mime_type": "application/json"}
        )
        data = json.loads(response.text)

        # Validate Category (simplified for Lite speed)
        category = data.get("category", "Other")

        # Process Themes
        themes = data.get("themes", [])
        if isinstance(themes, list):
            themes_str = ", ".join(themes)
        else:
            themes_str = str(themes)

        title = data.get("title", "")
        if str(title).lower() == "null":
            title = ""

        return {"category": category, "themes": themes_str, "title": title}

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning(f"Gemini analysis parsing error: {e}")
        return {"category": "Unknown", "themes": "", "title": "", "error": str(e)}
    except Exception as e:
        error_str = str(e).lower()
        # Re-raise rate limit errors so adaptive limiter can detect them
        if "429" in error_str or "quota" in error_str or "resource" in error_str or "rate" in str(e):
            logger.warning(f"Rate limit error in analyze_document: {e}")
            raise  # Let caller handle rate limits
        logger.error(f"Gemini analysis failed ({model_name}): {e}")
        return {"category": "Unknown", "themes": "", "title": "", "error": str(e)}


# Function to process different document types
def process_document(file_path: Path) -> Optional[Dict]:
    content = None
    file_type = file_path.suffix.lower()
    metadata = {}

    try:
        logger.debug(f"Processing file: {file_path.name} (type: {file_type})")
        if file_type == ".html":
            with open(file_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            soup = BeautifulSoup(html_content, "html.parser")
            for script in soup(
                [
                    "script",
                    "style",
                    "header",
                    "footer",
                    "nav",
                    "meta",
                    "link",
                    "noscript",
                    "form",
                ]
            ):
                script.decompose()
            content_div = (
                soup.find("main")
                or soup.find("article")
                or soup.find("div", class_="main-container")
                or soup.find("div", id="wb-cont")
                or soup.body
            )
            if content_div:
                content = content_div.get_text(separator="\n\n")
            content = clean_text(content) if content else None

        elif file_type == ".txt" or file_type == ".md":
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            content = clean_text(content)

        elif file_type == ".pdf":
            if not pdfplumber:
                logger.warning("pdfplumber not installed - cannot process PDF")
                return None

            full_text = ""
            with pdfplumber.open(file_path) as pdf:
                metadata = pdf.metadata or {}  # Extract PDF metadata
                for page in pdf.pages:
                    # Extract text
                    text = page.extract_text() or ""

                    # Extract and format tables as Markdown
                    tables = page.extract_tables()
                    table_text = ""
                    for table in tables:
                        # table is a list of lists
                        if not table:
                            continue

                        # Filter out None values
                        cleaned_table = [
                            [cell if cell is not None else "" for cell in row]
                            for row in table
                        ]

                        # Basic Markdown Table Construction
                        if len(cleaned_table) > 0:
                            # Header
                            headers = cleaned_table[0]
                            # Sanitize headers for markdown
                            headers = [h.replace("\n", " ") for h in headers]
                            table_text += "\n\n| " + " | ".join(headers) + " |\n"
                            table_text += (
                                "| " + " | ".join(["---"] * len(headers)) + " |\n"
                            )
                            # Rows
                            for row in cleaned_table[1:]:
                                row = [c.replace("\n", " ") for c in row]
                                table_text += "| " + " | ".join(row) + " |\n"
                            table_text += "\n"

                    # Combine (prefer tables if text is sparse, but usually text contains the table content too)
                    # Appending the structured table at the end of the page text is a safe way to ensure structure is present.
                    full_text += f"{text}\n{table_text}\n\n"

            content = clean_text(full_text)

        elif file_type == ".csv":
            with open(file_path, "r", encoding="utf-8") as f:
                # Read first to check header
                sample = f.read(1024)
                f.seek(0)
                has_header = csv.Sniffer().has_header(sample)

                reader = csv.DictReader(f)
                rows = []

                # QP Notes Schema Detection
                qp_cols = [
                    "title_en",
                    "question_en",
                    "response_en",
                    "background_en",
                    "additional_information_en",
                ]

                fieldnames = reader.fieldnames or []
                is_qp_notes = any(col in fieldnames for col in qp_cols)

                logger.debug(f"CSV analysis: QP Notes format={is_qp_notes}, columns={len(fieldnames)}")

                for row in reader:
                    row_text_parts = []
                    row_title = None

                    if is_qp_notes:
                        # Extract title separately for QP Notes
                        row_title = row.get("title_en", "").strip() or None
                        # Specific Extraction
                        for col in qp_cols:
                            if col in row and row[col]:
                                row_text_parts.append(row[col].strip())
                    else:
                        # Generic Extraction
                        for k, v in row.items():
                            if v and str(v).strip():
                                row_text_parts.append(f"{k}: {str(v).strip()}")

                    if row_text_parts:
                        # Return dict with content and optional title for each row
                        rows.append({
                            "content": " | ".join(row_text_parts),
                            "title": row_title
                        })

            # Return List[dict] for CSV wrapped in dict
            if not rows:
                 logger.debug("CSV processed but no rows extracted")

            return {
                "content": rows,
                "metadata": {"has_row_titles": is_qp_notes},
            }  

        elif file_type == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, list):
                # Treat as list of records -> Batch Analysis path
                return {
                    "content": [json.dumps(item, ensure_ascii=False) for item in data],
                    "metadata": {},
                }
            elif isinstance(data, dict):
                # Treat as single document -> Prose path
                return {
                    "content": json.dumps(data, ensure_ascii=False, indent=2),
                    "metadata": {},
                }
            else:
                return {"content": str(data), "metadata": {}}

        else:
            logger.debug(f"Unsupported file type: {file_type}")
            return None

        content_len = len(content) if content else 0
        logger.debug(f"Extracted {content_len} chars from {file_path.name}")
        return {"content": content, "metadata": metadata}

    except Exception as e:
        logger.error(f"Error reading file {file_path.name}: {type(e).__name__}")
        return None


# Helper for Semantic/Dynamic Chunking
def semantic_chunking(
    text: str, max_chunk_size: int = 1000, min_chunk_size: int = 200
) -> List[str]:
    """
    Splits text based on semantic boundaries (paragraphs) first, then size.
    Merges small paragraphs to reach min_chunk_size.
    Splits large paragraphs to respect max_chunk_size.
    """
    # 1. Split by Paragraphs (Double newline is standard for markdown/txt)
    paragraphs = re.split(r"\n\s*\n", text)

    final_chunks = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # Check if adding this para exceeds max size
        if len(current_chunk) + len(para) + 2 <= max_chunk_size:
            current_chunk += "\n\n" + para if current_chunk else para
        else:
            # Current chunk is full, push it
            if current_chunk:
                final_chunks.append(current_chunk)
                current_chunk = ""

            # Handle the new paragraph
            if len(para) > max_chunk_size:
                # If the single paragraph is HUGE, fall back to recursive split
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=max_chunk_size,
                    chunk_overlap=min_chunk_size // 2,
                    separators=["\n", ". ", " "],
                )
                sub_chunks = splitter.split_text(para)
                final_chunks.extend(sub_chunks)
            else:
                current_chunk = para

    # Append any remaining text
    if current_chunk:
        final_chunks.append(current_chunk)

    return final_chunks


# Helper for BATCH categorization and theme extraction
def analyze_batch(
    texts: List[str], model_name: str = None
) -> List[Dict[str, str]]:
    if not texts:
        return []

    # Get model using model_config (lazy initialization)
    model = get_categorization_model("fast")
    if not model:
        return [{"category": "Unknown", "themes": ""} for _ in texts]

    try:

        # Construct a prompt with indexed items
        items_str = ""
        for i, text in enumerate(texts):
            # Sanitize text to remove control characters that might break JSON
            safe_text = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", text[:500])
            items_str += f"ITEM {i}:\n{safe_text}\n\n"

        prompt = f"""Analyze the following {len(texts)} distinct items.
        For EACH item, extract:
        1. Category: ONE from [Policy, Press Release, Guidance, Report, Info, Legal, Technical, Form, Dataset, Other].
        2. Themes: 1-3 key topics.

        ITEMS:
        ---
        {items_str}
        ---

        Output strictly as valid JSON with this structure:
        {{
            "results": [
                {{ "index": 0, "category": "...", "themes": ["..."] }},
                {{ "index": 1, "category": "...", "themes": ["..."] }}
                ...
            ]
        }}
        """

        response = model.generate_content(
            prompt, generation_config={"response_mime_type": "application/json"}
        )

        # Robust JSON Extraction
        response_text = response.text.strip()
        # Remove markdown code blocks if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]

        try:
            data = json.loads(response_text)
        except json.JSONDecodeError:
            # Fallback: Try to find the first { and last }
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start != -1 and end != -1:
                data = json.loads(response_text[start:end])
            else:
                raise

        results = data.get("results", [])

        # Map back to original order safely
        final_results = []
        valid_categories = [
            "Policy",
            "Press Release",
            "Guidance",
            "Report",
            "Info",
            "Legal",
            "Technical",
            "Form",
            "Dataset",
            "Other",
        ]

        # Create a map of index -> result
        result_map = {r.get("index"): r for r in results}

        for i in range(len(texts)):
            res = result_map.get(i, {})
            cat = res.get("category", "Other")
            if cat not in valid_categories:
                cat = "Other"

            themes = res.get("themes", [])
            if isinstance(themes, list):
                themes_str = ", ".join(themes)
            else:
                themes_str = str(themes)

            final_results.append({"category": cat, "themes": themes_str})

        return final_results

    except Exception as e:
        # tqdm.write(f"Error during Batch Gemini analysis: {e}")
        return [{"category": "Unknown", "themes": ""} for _ in texts]


def analyze_batch_worker(texts: List[str], index: int = 0, model_name: str = None) -> tuple[int, List[Dict]]:
    """
    Worker for parallel processing with adaptive rate limiting.

    Uses gemini_limiter to:
    - Limit concurrent API calls
    - Back off on rate limit errors (429)
    - Gradually ramp up after successes
    """
    results = []
    target_model = model_name or model_config.get_model("fast")

    for text in texts:
        gemini_limiter.acquire()
        was_rate_limited = False
        success = False
        try:
            # Use Fast model for batch processing speed
            res = analyze_document(text, model_name=target_model)
            results.append(res)
            success = True
        except Exception as e:
            error_str = str(e).lower()
            # Detect rate limit errors (429, quota exceeded, resource exhausted)
            if "429" in error_str or "quota" in error_str or "resource" in error_str or "rate" in error_str:
                was_rate_limited = True
                logger.warning(f"Rate limit detected in batch analysis: {type(e).__name__}")
            else:
                logger.warning(f"Batch analysis error: {type(e).__name__}")
            results.append({"category": "Unknown", "themes": ""})
        finally:
            gemini_limiter.release(success=success, was_rate_limited=was_rate_limited)

    return index, results


def prepare_upsert_batch_worker(items: List[Dict], common_metadata: Dict):
    """
    Worker for parallel embedding generation and metadata preparation.
    Does NOT upsert to DB to avoid locking issues.
    """
    try:
        texts_to_embed = [item["text"] for item in items]
        batch_embeddings = get_embeddings_batch(texts_to_embed)

        if not batch_embeddings:
            return None

        ids_batch, embs_batch, metas_batch, docs_batch = [], [], [], []

        for j, emb in enumerate(batch_embeddings):
            item = items[j]
            ids_batch.append(item["id"])
            embs_batch.append(emb)
            docs_batch.append(item["text"])

            # Merge specific item metadata with common metadata
            meta = common_metadata.copy()
            meta["category"] = item.get("category", "Other")
            meta["themes"] = item.get("themes", "")
            # Use per-item title if available, otherwise keep common source_title
            if item.get("title"):
                meta["source_title"] = item["title"]

            metas_batch.append(meta)

        return (ids_batch, embs_batch, metas_batch, docs_batch)
    except Exception as e:
        logger.error(f"Embedding worker failed: {type(e).__name__}")
        return None


def process_file_pipeline_streaming(
    file_path: Path, collection
) -> Generator[str, None, None]:
    """
    Generator version of process_file_pipeline.
    Yields JSON string status updates for SSE.
    """
    # Get model names for display
    fast_model = model_config.get_model("fast")
    reasoning_model = model_config.get_model("reasoning")

    yield json.dumps(
        {"status": "reading", "message": f"Reading {file_path.name}...", "model": "pdfplumber"}
    ) + "\n"

    doc_result = process_document(file_path)

    if not doc_result or not doc_result.get("content"):
        yield json.dumps(
            {"status": "skipped", "message": "Skipped (unsupported or empty)"}
        ) + "\n"
        return

    content_obj = doc_result["content"]
    file_metadata = doc_result.get("metadata", {})

    source_id = file_path.stem
    doc_type = file_path.suffix[1:]
    total_upserted = 0

    # Common metadata base
    common_metadata = {
        "source_id": source_id,
        "language": "en",
        "effective_date_start": datetime.date.today().isoformat(),
        "doc_type": doc_type,
    }

    # Use ThreadPoolExecutor for parallel operations
    # Uses adaptive rate limiter internally to handle rate limits
    with concurrent.futures.ThreadPoolExecutor(max_workers=ANALYSIS_MAX_WORKERS) as executor:

        # --- CSV PATH (Batched Row-Level Analysis) ---
        if isinstance(content_obj, list):
            rows = content_obj  # ALL ROWS (can be list of strings or list of dicts)
            yield json.dumps(
                {
                    "status": "analyzing",
                    "message": f"Analyzing {len(rows)} rows (Parallel)...",
                    "model": fast_model,
                }
            ) + "\n"

            # Check if rows have per-row titles (new format: list of dicts)
            has_row_titles = isinstance(rows[0], dict) if rows else False
            default_title = file_path.stem.replace("_", " ").title()
            common_metadata["source_title"] = default_title

            # Extract text for batch analysis
            if has_row_titles:
                row_texts = [r["content"] for r in rows]
                row_titles = [r.get("title") or default_title for r in rows]
            else:
                row_texts = rows
                row_titles = [default_title] * len(rows)

            batches = [
                row_texts[i : i + ANALYSIS_BATCH_SIZE]
                for i in range(0, len(row_texts), ANALYSIS_BATCH_SIZE)
            ]

            all_row_results = []

            # Submit all analysis tasks
            future_to_batch = {
                executor.submit(
                    analyze_batch_worker, batch, i, model_config.get_model("fast")
                ): i
                for i, batch in enumerate(batches)
            }

            completed_analyses = 0
            for future in concurrent.futures.as_completed(future_to_batch):
                idx, analyses = future.result() # result is now (index, results)
                # We don't need idx from result if we have it from future_to_batch logic, but worker returns it for safety
                batch_data = batches[idx]
                completed_analyses += 1

                yield json.dumps(
                    {
                        "status": "analyzing",
                        "message": f"Analyzed batch {completed_analyses}/{len(batches)}...",
                        "progress": completed_analyses,
                        "total": len(batches),
                        "model": fast_model,
                    }
                ) + "\n"

                for j, text in enumerate(batch_data):
                    global_index = (idx * ANALYSIS_BATCH_SIZE) + j
                    all_row_results.append(
                        {
                            "index": global_index,
                            "text": text,
                            "title": row_titles[global_index],  # Per-row title
                            "category": analyses[j]["category"],
                            "themes": analyses[j]["themes"],
                        }
                    )

            # Sort back by global index
            all_row_results.sort(key=lambda x: x["index"])

            # Prepare final list of chunks to embed
            final_items_to_embed = []
            for item in all_row_results:
                text = item["text"]
                row_title = item.get("title", default_title)
                if len(text) > 20000:
                    sub_chunks = semantic_chunking(
                        text, max_chunk_size=2000, min_chunk_size=240
                    )
                    for k, sub_text in enumerate(sub_chunks):
                        final_items_to_embed.append(
                            {
                                "id": f"{source_id}-row-{item['index']}-part-{k}",
                                "text": sub_text,
                                "title": row_title,  # Per-row title
                                "category": item["category"],
                                "themes": item["themes"],
                            }
                        )
                else:
                    final_items_to_embed.append(
                        {
                            "id": f"{source_id}-row-{item['index']}",
                            "text": text,
                            "title": row_title,  # Per-row title
                            "category": item["category"],
                            "themes": item["themes"],
                        }
                    )

            # Parallel Embed / Sequential Upsert
            EMBED_BATCH_SIZE = 20
            yield json.dumps(
                {
                    "status": "embedding",
                    "message": f"Embedding {len(final_items_to_embed)} chunks (Parallel)...",
                    "total": len(final_items_to_embed),
                    "model": "text-embedding-004",
                }
            ) + "\n"

            upsert_batches = [
                final_items_to_embed[i : i + EMBED_BATCH_SIZE]
                for i in range(0, len(final_items_to_embed), EMBED_BATCH_SIZE)
            ]

            future_to_upsert = {
                executor.submit(prepare_upsert_batch_worker, batch, common_metadata): i
                for i, batch in enumerate(upsert_batches)
            }

            completed_upserts = 0
            for future in concurrent.futures.as_completed(future_to_upsert):
                result = future.result()
                if result:
                    ids, embs, metas, docs = result
                    try:
                        collection.upsert(
                            ids=ids, embeddings=embs, metadatas=metas, documents=docs
                        )
                        count = len(ids)
                        total_upserted += count
                    except Exception as e:
                        logger.error(f"Upsert failed for batch: {type(e).__name__}")

                completed_upserts += 1
                yield json.dumps(
                    {
                        "status": "embedding",
                        "message": f"Upserted batch {completed_upserts}/{len(upsert_batches)}...",
                        "progress": completed_upserts * EMBED_BATCH_SIZE,
                        "total": len(final_items_to_embed),
                    }
                ) + "\n"

        # --- PROSE PATH ---
        else:
            full_text = content_obj
            chunks = semantic_chunking(
                full_text, max_chunk_size=2000, min_chunk_size=240
            )
            yield json.dumps(
                {
                    "status": "analyzing",
                    "message": f"Split into {len(chunks)} chunks. Analyzing...",
                    "model": fast_model,
                }
            ) + "\n"

            analysis = analyze_document(full_text, model_name=fast_model)

            # Title Strategy: LLM > Metadata > Filename
            source_title = file_path.stem.replace("_", " ").title()  # Default
            extracted_title = analysis.get("title")
            metadata_title = file_metadata.get("Title")

            if extracted_title and len(extracted_title) > 3:
                source_title = extracted_title
            elif metadata_title and len(metadata_title) > 3:
                source_title = metadata_title

            common_metadata["source_title"] = source_title

            # Prepare items
            final_items_to_embed = []
            for i, chunk_text in enumerate(chunks):
                final_items_to_embed.append(
                    {
                        "id": f"{source_id}-chunk-{i}",
                        "text": chunk_text,
                        "category": analysis["category"],
                        "themes": analysis["themes"],
                    }
                )

            # Parallel Embed / Sequential Upsert
            EMBED_BATCH_SIZE = 20
            yield json.dumps(
                {
                    "status": "embedding",
                    "message": f"Embedding {len(chunks)} chunks (Parallel)...",
                    "total": len(chunks),
                    "model": "text-embedding-004",
                }
            ) + "\n"

            upsert_batches = [
                final_items_to_embed[i : i + EMBED_BATCH_SIZE]
                for i in range(0, len(final_items_to_embed), EMBED_BATCH_SIZE)
            ]

            future_to_upsert = {
                executor.submit(prepare_upsert_batch_worker, batch, common_metadata): i
                for i, batch in enumerate(upsert_batches)
            }

            completed_upserts = 0
            for future in concurrent.futures.as_completed(future_to_upsert):
                result = future.result()
                if result:
                    ids, embs, metas, docs = result
                    try:
                        collection.upsert(
                            ids=ids, embeddings=embs, metadatas=metas, documents=docs
                        )
                        count = len(ids)
                        total_upserted += count
                    except Exception as e:
                        logger.error(f"Upsert failed for batch: {type(e).__name__}")

                completed_upserts += 1
                yield json.dumps(
                    {
                        "status": "embedding",
                        "message": f"Upserted batch {completed_upserts}/{len(upsert_batches)}...",
                        "progress": completed_upserts * EMBED_BATCH_SIZE,
                        "total": len(chunks),
                    }
                ) + "\n"

    yield json.dumps(
        {"status": "complete", "message": "Done", "chunks": total_upserted}
    ) + "\n"


def process_file_pipeline(file_path: Path, collection) -> Dict:
    """
    Legacy wrapper for CLI support.
    """
    # Consume generator
    last_status = None
    for status_json in process_file_pipeline_streaming(file_path, collection):
        last_status = json.loads(status_json)

    return {
        "file_path": file_path,
        "status": "processed",
        "chunks_count": last_status.get("chunks", 0) if last_status else 0,
    }


# Modify ingest_data to accept a source directory
def ingest_data(source_data_dir: Path):
    logger.info("Starting ingestion process...")

    try:
        client.delete_collection(name="gov_knowledge_base")
        logger.info("Cleared existing 'gov_knowledge_base' collection")
    except Exception as e:
        logger.debug("Collection does not exist yet - creating new")
    collection = client.get_or_create_collection(
        name="gov_knowledge_base", embedding_function=None
    )

    if not source_data_dir.exists():
        logger.error(f"Source data directory not found: {source_data_dir}")
        return

    files = [f for f in source_data_dir.iterdir() if f.is_file()]
    total_chunks_ingested = 0

    # Use ThreadPoolExecutor for parallel processing
    MAX_WORKERS = 4

    logger.info(f"Processing {len(files)} files with {MAX_WORKERS} workers")

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all file processing tasks, PASSING COLLECTION
        future_to_file = {
            executor.submit(process_file_pipeline, f, collection): f for f in files
        }

        with tqdm(total=len(files), desc="Ingesting Files", unit="file") as pbar:
            for future in concurrent.futures.as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    result = future.result()

                    if result["status"] == "skipped":
                        pbar.set_description(f"Skipped {file_path.name}")
                    elif result["status"] == "processed":
                        count = result.get("chunks_count", 0)
                        total_chunks_ingested += count
                        pbar.set_description(f"Finished {file_path.name} ({count})")

                except Exception as e:
                    logger.error(f"Exception processing {file_path.name}: {type(e).__name__}")

                pbar.update(1)

    logger.info(f"Ingestion complete. Ingested {total_chunks_ingested} chunks")
    logger.info(f"ChromaDB path: {Path(DB_DIR).resolve()}")


# =============================================================================
# Connector Ingestion Functions (for G7 data sources)
# =============================================================================

def record_to_text(record: Dict[str, Any]) -> str:
    """
    Convert a connector record (dict) into searchable text.

    Handles various field types and creates a readable text representation.
    """
    # Skip internal/metadata-only fields
    skip_fields = {"_id", "id", "resource_id", "dataset_id", "_connector", "_country", "_source"}

    parts = []
    for key, value in record.items():
        if key in skip_fields:
            continue
        if value is None or value == "":
            continue
        # Clean up key name for readability
        clean_key = key.replace("_", " ").replace("-", " ").title()
        parts.append(f"{clean_key}: {value}")

    return " | ".join(parts) if parts else ""


def process_records_pipeline_streaming(
    records: List[Dict[str, Any]],
    source_id: str,
    source_title: str,
    connector_id: str,
    country: str = "",
    collection=None
) -> Generator[str, None, None]:
    """
    Process connector records using the FULL ingestion pipeline.

    Uses the same pattern as process_file_pipeline_streaming() CSV path:
    1. Convert records to text rows
    2. Batch analyze with Gemini (categorization + themes)
    3. Semantic chunking for large records
    4. Parallel embedding with ThreadPoolExecutor
    5. Sequential upsert to ChromaDB

    Args:
        records: List of data records from connector
        source_id: Dataset/source identifier
        source_title: Human-readable title
        connector_id: Connector ID (e.g., "statcan", "ons")
        country: Country code (e.g., "CA", "UK")
        collection: ChromaDB collection (optional, will get default if None)

    Yields:
        JSON progress updates for streaming
    """
    if not records:
        yield json.dumps({
            "status": "complete",
            "message": "No records to process",
            "chunks": 0
        }) + "\n"
        return

    # Get collection if not provided
    if collection is None:
        from database import get_collection
        collection = get_collection()

    # Get model name for display
    fast_model = model_config.get_model("fast")

    yield json.dumps({
        "status": "reading",
        "message": f"Processing {len(records)} records...",
        "progress": 15,
        "current": 0,
        "total": len(records),
        "model": "connector"
    }) + "\n"

    # Convert records to text rows
    total_records = len(records)
    rows = []
    for record in records:
        text = record_to_text(record)
        if text:  # Keep any record with actual data (removed 10-char minimum)
            rows.append(text)

    filtered_count = total_records - len(rows)
    yield json.dumps({
        "status": "converting",
        "message": f"Converted {total_records} → {len(rows)} valid records" + (f" ({filtered_count} empty filtered)" if filtered_count > 0 else ""),
        "progress": 20,
        "current": len(rows),
        "total": total_records
    }) + "\n"

    if not rows:
        yield json.dumps({
            "status": "complete",
            "message": "No valid text content in records",
            "chunks": 0
        }) + "\n"
        return

    # Common metadata
    common_metadata = {
        "source_id": source_id,
        "source_title": source_title,
        "connector": connector_id,
        "country": country,
        "doc_type": "dataset",
        "language": "en",
        "effective_date_start": datetime.date.today().isoformat(),
    }

    total_upserted = 0

    # Use ThreadPoolExecutor for parallel operations (same as file pipeline)
    # Uses adaptive rate limiter internally to handle rate limits
    with concurrent.futures.ThreadPoolExecutor(max_workers=ANALYSIS_MAX_WORKERS) as executor:

        # Phase 1: Batch analysis with Gemini (25-65% of overall progress)
        yield json.dumps({
            "status": "analyzing",
            "message": f"Analyzing {len(rows)} records...",
            "progress": 25,
            "current": 0,
            "total": len(rows),
            "model": fast_model
        }) + "\n"

        batches = [
            rows[i : i + ANALYSIS_BATCH_SIZE]
            for i in range(0, len(rows), ANALYSIS_BATCH_SIZE)
        ]

        all_row_results = []

        # Submit all analysis tasks
        future_to_batch = {
            executor.submit(
                analyze_batch_worker, batch, i, model_config.get_model("fast")
            ): i
            for i, batch in enumerate(batches)
        }

        completed_analyses = 0
        for future in concurrent.futures.as_completed(future_to_batch):
            idx, analyses = future.result()
            batch_data = batches[idx]
            completed_analyses += 1
            records_analyzed = completed_analyses * BATCH_SIZE_ANALYSIS
            # Progress: 25% + (40% * fraction complete) = 25-65%
            phase_progress = 25 + int(40 * completed_analyses / len(batches))

            yield json.dumps({
                "status": "analyzing",
                "message": f"Analyzing records... {min(records_analyzed, len(rows))}/{len(rows)}",
                "progress": phase_progress,
                "current": min(records_analyzed, len(rows)),
                "total": len(rows)
            }) + "\n"

            for j, text in enumerate(batch_data):
                global_index = (idx * ANALYSIS_BATCH_SIZE) + j
                all_row_results.append({
                    "index": global_index,
                    "text": text,
                    "category": analyses[j].get("category", "Dataset"),
                    "themes": analyses[j].get("themes", ""),
                })

        # Sort back by global index
        all_row_results.sort(key=lambda x: x["index"])

        # Phase 2: Semantic chunking for large records
        final_items_to_embed = []
        for item in all_row_results:
            text = item["text"]
            if len(text) > 20000:
                sub_chunks = semantic_chunking(
                    text, max_chunk_size=2000, min_chunk_size=240
                )
                for k, sub_text in enumerate(sub_chunks):
                    final_items_to_embed.append({
                        "id": f"{connector_id}-{source_id}-row-{item['index']}-part-{k}",
                        "text": sub_text,
                        "category": item["category"],
                        "themes": item["themes"],
                    })
            else:
                final_items_to_embed.append({
                    "id": f"{connector_id}-{source_id}-row-{item['index']}",
                    "text": text,
                    "category": item["category"],
                    "themes": item["themes"],
                })

        # Phase 3: Parallel embedding + sequential upsert (65-100% of overall progress)
        EMBED_BATCH_SIZE = 20
        yield json.dumps({
            "status": "embedding",
            "message": f"Embedding {len(final_items_to_embed)} chunks...",
            "progress": 65,
            "current": 0,
            "total": len(final_items_to_embed),
            "model": "text-embedding-004"
        }) + "\n"

        upsert_batches = [
            final_items_to_embed[i : i + EMBED_BATCH_SIZE]
            for i in range(0, len(final_items_to_embed), EMBED_BATCH_SIZE)
        ]

        future_to_upsert = {
            executor.submit(prepare_upsert_batch_worker, batch, common_metadata): i
            for i, batch in enumerate(upsert_batches)
        }

        completed_upserts = 0
        for future in concurrent.futures.as_completed(future_to_upsert):
            result = future.result()
            if result:
                ids, embs, metas, docs = result
                try:
                    collection.upsert(
                        ids=ids, embeddings=embs, metadatas=metas, documents=docs
                    )
                    total_upserted += len(ids)
                except Exception as e:
                    logger.error(f"Upsert failed for batch: {type(e).__name__}")

            completed_upserts += 1
            records_embedded = min(completed_upserts * EMBED_BATCH_SIZE, len(final_items_to_embed))
            # Progress: 65% + (35% * fraction complete) = 65-100%
            phase_progress = 65 + int(35 * completed_upserts / len(upsert_batches))

            yield json.dumps({
                "status": "embedding",
                "message": f"Storing records... {records_embedded}/{len(final_items_to_embed)}",
                "progress": min(phase_progress, 99),  # Cap at 99% until complete
                "current": records_embedded,
                "total": len(final_items_to_embed)
            }) + "\n"

    yield json.dumps({
        "status": "complete",
        "message": f"Successfully imported {total_upserted} records",
        "progress": 100,
        "chunks": total_upserted
    }) + "\n"


# Backwards compatibility alias
def ingest_connector_records(
    records: List[Dict[str, Any]],
    source_id: str,
    source_title: str,
    connector_id: str,
    country: str = "",
    collection=None
) -> Generator[str, None, int]:
    """
    Backwards compatibility wrapper for process_records_pipeline_streaming.
    """
    for update in process_records_pipeline_streaming(
        records, source_id, source_title, connector_id, country, collection
    ):
        yield update


if __name__ == "__main__":
    SOURCE_DATA_DIR = script_dir / "source_data"
    # Ensure the source_data directory exists, create if not
    SOURCE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    # Move source_data.html into the new directory if it exists at the old location
    old_source_html = script_dir / "source_data.html"
    if old_source_html.exists():
        logger.info(f"Moving legacy file to {SOURCE_DATA_DIR}")
        old_source_html.rename(SOURCE_DATA_DIR / old_source_html.name)

    ingest_data(SOURCE_DATA_DIR)
