"""
Documents router - Document management and ingestion endpoints.
"""

import re
import json
from pathlib import Path
from urllib.parse import unquote

from fastapi import APIRouter, UploadFile, File
from fastapi.responses import StreamingResponse
from typing import List

from database import get_collection
from api.schemas import DocumentMetadata, FilterOptionsResponse
from ingest import process_file_pipeline_streaming
from core import (
    get_logger,
    log_error,
    log_audit,
    handle_exception,
    ValidationError,
    DocumentNotFoundError,
    ProcessingError,
    ErrorCode,
    ALLOWED_FILE_EXTENSIONS,
)
from core.constants import ALLOWED_CONTENT_TYPES

logger = get_logger(__name__)
router = APIRouter()
script_dir = Path(__file__).resolve().parent.parent.parent  # backend/


@router.get("/documents", response_model=List[DocumentMetadata])
async def get_documents():
    """
    List all documents in the knowledge base with their metadata.
    """
    try:
        collection = get_collection()
        all_docs = collection.get(include=["metadatas"])

        if not all_docs or not all_docs["metadatas"]:
            return []

        source_map = {}

        for meta in all_docs["metadatas"]:
            sid = meta.get("source_id")
            if not sid:
                continue

            if sid not in source_map:
                source_map[sid] = {
                    "source_title": meta.get("source_title", "Unknown"),
                    "source_id": sid,
                    "doc_type": meta.get("doc_type", "unknown"),
                    "category": meta.get("category", "Other"),
                    "themes": meta.get("themes", ""),
                    "updated_at": meta.get("effective_date_start", ""),
                    "chunk_count": 0,
                }
            source_map[sid]["chunk_count"] += 1

        return list(source_map.values())

    except Exception as e:
        log_error("Error fetching documents", error=e)
        raise handle_exception(
            ProcessingError("An error occurred while fetching documents.")
        )


@router.get("/filter-options", response_model=FilterOptionsResponse)
async def get_filter_options():
    """Get available filter options (categories and themes) from the knowledge base."""
    try:
        collection = get_collection()
        all_docs = collection.get(include=["metadatas"])

        if not all_docs or not all_docs["metadatas"]:
            return FilterOptionsResponse(categories=[], themes=[])

        categories_set = set()
        themes_set = set()

        for meta in all_docs["metadatas"]:
            # Collect categories
            category = meta.get("category", "").strip()
            if category and category != "Unknown":
                categories_set.add(category)

            # Collect themes (comma-separated in the metadata)
            themes_str = meta.get("themes", "")
            if themes_str:
                for theme in themes_str.split(","):
                    theme = theme.strip()
                    if theme:
                        themes_set.add(theme)

        return FilterOptionsResponse(
            categories=sorted(list(categories_set)),
            themes=sorted(list(themes_set))
        )

    except Exception as e:
        log_error("Error fetching filter options", error=e)
        raise handle_exception(
            ProcessingError("An error occurred while fetching filter options.")
        )


@router.post("/ingest")
async def ingest_document(file: UploadFile = File(...)):
    """
    Ingest a document into the knowledge base.

    Supports: PDF, TXT, CSV, MD, JSON files.
    Returns a streaming response with ingestion progress.
    """
    try:
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ALLOWED_FILE_EXTENSIONS:
            raise ValidationError(
                message=f"Invalid file type. Allowed: {', '.join(sorted(ALLOWED_FILE_EXTENSIONS))}",
                code=ErrorCode.INVALID_FILE_TYPE,
                details={"extension": file_ext, "allowed": list(ALLOWED_FILE_EXTENSIONS)},
            )

        if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
            raise ValidationError(
                message="Invalid content type",
                code=ErrorCode.INVALID_FILE_TYPE,
                details={"content_type": file.content_type},
            )

        # Sanitize filename
        safe_filename = re.sub(r"[^\w\.-]", "_", file.filename)
        safe_filename = safe_filename.lstrip(".-")
        if not safe_filename:
            safe_filename = "unnamed_file" + file_ext

        # Save uploaded file temporarily
        temp_dir = script_dir / "source_data" / "temp"
        temp_path = temp_dir / safe_filename
        temp_dir.mkdir(parents=True, exist_ok=True)

        with open(temp_path, "wb") as buffer:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                buffer.write(chunk)

        collection = get_collection()

        log_audit(
            action="ingest_start",
            resource="document",
            details={"filename": safe_filename, "extension": file_ext}
        )

        return StreamingResponse(
            process_file_pipeline_streaming(temp_path, collection),
            media_type="application/x-ndjson",
        )

    except ValidationError as e:
        raise e.to_http_exception()
    except Exception as e:
        log_error("Document ingestion error", error=e, context={"uploaded_file": file.filename})
        raise handle_exception(
            ProcessingError("An error occurred during document ingestion.")
        )


@router.get("/documents/{doc_id}")
async def get_document_by_id(doc_id: str):
    """Get all chunks and metadata for a specific document by doc_id or source_id.

    Works with any doc_id format by querying the chunk's metadata to get source_id.
    Handles: chunk IDs, row IDs, row-part IDs, or direct source_ids.
    """
    try:
        decoded_id = unquote(doc_id)
        collection = get_collection()

        # Step 1: Try to find the exact doc_id and get source_id from its metadata
        chunk_result = collection.get(ids=[decoded_id], include=["metadatas"])

        if chunk_result and chunk_result["ids"] and chunk_result["metadatas"]:
            # Found the chunk - extract source_id from its metadata
            source_id = chunk_result["metadatas"][0].get("source_id", decoded_id)
        else:
            # Not a chunk ID - treat it as a source_id directly
            source_id = decoded_id

        # Step 2: Get all chunks with that source_id
        results = collection.get(
            where={"source_id": source_id},
            include=["documents", "metadatas"]
        )

        if not results or not results["ids"]:
            raise DocumentNotFoundError(doc_id)

        # Aggregate document data
        chunks = []
        metadata = {}

        for i, chunk_id in enumerate(results["ids"]):
            meta = results["metadatas"][i] if results["metadatas"] else {}
            content = results["documents"][i] if results["documents"] else ""

            # Capture metadata from first chunk
            if not metadata:
                metadata = {
                    "source_id": meta.get("source_id", source_id),
                    "source_title": meta.get("source_title", "Unknown Document"),
                    "doc_type": meta.get("doc_type", "unknown"),
                    "category": meta.get("category", "Other"),
                    "themes": meta.get("themes", ""),
                    "effective_date_start": meta.get("effective_date_start", ""),
                    "effective_date_end": meta.get("effective_date_end"),
                    "language": meta.get("language", "en"),
                }

            chunks.append({
                "chunk_id": chunk_id,
                "content": content,
                "section_reference": meta.get("section_reference", ""),
            })

        # Sort chunks by section reference if available
        chunks.sort(key=lambda x: x.get("section_reference", ""))

        return {
            "metadata": metadata,
            "chunks": chunks,
            "total_chunks": len(chunks),
        }

    except DocumentNotFoundError as e:
        raise e.to_http_exception()
    except Exception as e:
        log_error("Error fetching document by ID", error=e, context={"doc_id": doc_id})
        raise handle_exception(
            ProcessingError("An error occurred while fetching the document.")
        )


@router.get("/graph")
async def get_knowledge_graph():
    """Get the knowledge graph data for visualization."""
    graph_path = script_dir / "graph_data.json"
    if graph_path.exists():
        with open(graph_path, "r") as f:
            return json.load(f)
    return {"nodes": [], "links": []}
