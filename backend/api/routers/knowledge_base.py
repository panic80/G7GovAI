"""
Unified Knowledge Base API Router
==================================
Single ingestion interface for all data sources:
- File uploads (PDF, CSV, JSON, etc.)
- G7 government data connectors

Endpoints:
- POST /knowledge-base/ingest      - Unified ingestion (files or connectors)
- GET  /knowledge-base/stats       - Knowledge base statistics
- GET  /knowledge-base/connectors  - List available G7 connectors
"""

import asyncio
import gzip
import json
import logging
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core.rate_limit import limiter, RateLimits

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from database import get_collection
from ingest import process_file_pipeline_streaming, process_records_pipeline_streaming
from connectors import CONNECTORS

logger = logging.getLogger(__name__)
router = APIRouter()

script_dir = Path(__file__).resolve().parent.parent.parent  # backend/


# =============================================================================
# Request/Response Models
# =============================================================================

class ConnectorImportRequest(BaseModel):
    """Request for importing data from a G7 connector."""
    connector_id: str
    dataset_id: Optional[str] = None
    limit: Optional[int] = None  # No limit by default - import all records


class KnowledgeBaseStats(BaseModel):
    """Knowledge base statistics response."""
    total_documents: int
    by_source: Dict[str, int]
    by_connector: Dict[str, int]
    last_updated: Optional[str] = None


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/knowledge-base/ingest")
@limiter.limit(RateLimits.UPLOAD)
async def unified_ingest(
    request: Request,
    source_type: str = Form(...),
    # For file uploads
    file: Optional[UploadFile] = File(None),
    # For connector imports (as form fields or JSON)
    connector_id: Optional[str] = Form(None),
    dataset_id: Optional[str] = Form(None),
    limit: Optional[int] = Form(None),  # No limit - import all records
):
    """
    Unified ingestion endpoint for all data sources.

    Args:
        source_type: "file" or "connector"
        file: File to upload (when source_type="file")
        connector_id: G7 connector ID (when source_type="connector")
        dataset_id: Specific dataset ID (when source_type="connector")
        limit: Max records to import (when source_type="connector")

    Returns:
        StreamingResponse with NDJSON progress updates
    """
    if source_type == "file":
        return await _ingest_file(file)
    elif source_type == "connector":
        return await _ingest_connector(connector_id, dataset_id, limit)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source_type: {source_type}. Must be 'file' or 'connector'"
        )


@router.post("/knowledge-base/ingest/connector")
async def ingest_from_connector(request: ConnectorImportRequest):
    """
    Import data from a G7 connector (JSON body version).

    Alternative to the unified endpoint for connector-only imports.
    """
    return await _ingest_connector(
        request.connector_id,
        request.dataset_id,
        request.limit
    )


@router.get("/knowledge-base/stats")
async def get_stats() -> KnowledgeBaseStats:
    """
    Get knowledge base statistics.

    Returns document counts by source and connector.
    """
    try:
        collection = get_collection()
        all_docs = collection.get(include=["metadatas"])

        if not all_docs or not all_docs["metadatas"]:
            return KnowledgeBaseStats(
                total_documents=0,
                by_source={},
                by_connector={},
                last_updated=None
            )

        by_source: Dict[str, int] = {}
        by_connector: Dict[str, int] = {}
        latest_date = None

        for meta in all_docs["metadatas"]:
            # Count by source_id
            source_id = meta.get("source_id", "unknown")
            by_source[source_id] = by_source.get(source_id, 0) + 1

            # Count by connector (if present)
            connector = meta.get("connector")
            if connector:
                by_connector[connector] = by_connector.get(connector, 0) + 1
            else:
                by_connector["file_upload"] = by_connector.get("file_upload", 0) + 1

            # Track latest update
            date_str = meta.get("effective_date_start")
            if date_str and (latest_date is None or date_str > latest_date):
                latest_date = date_str

        return KnowledgeBaseStats(
            total_documents=len(all_docs["metadatas"]),
            by_source=by_source,
            by_connector=by_connector,
            last_updated=latest_date
        )

    except Exception as e:
        logger.exception("Error getting knowledge base stats")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while fetching knowledge base statistics."
        )


@router.post("/knowledge-base/ingest-sample-data")
async def ingest_sample_data():
    """
    Ingest all sample data files for demo purposes.

    Looks in backend/sample_data/ and ingests all supported files.
    Handles .gz compressed files by decompressing on-the-fly.
    """
    sample_dir = script_dir / "sample_data"

    if not sample_dir.exists():
        raise HTTPException(
            status_code=404,
            detail="Sample data directory not found. Please ensure backend/sample_data/ exists."
        )

    # Find all sample files
    sample_files = []
    for ext in [".txt", ".csv", ".json", ".md", ".html", ".pdf", ".gz"]:
        sample_files.extend(sample_dir.glob(f"*{ext}"))

    if not sample_files:
        raise HTTPException(
            status_code=404,
            detail="No sample data files found in backend/sample_data/"
        )

    async def stream_sample_ingestion():
        """Stream progress for all sample files."""
        collection = get_collection()
        total_files = len(sample_files)

        yield json.dumps({
            "phase": "starting",
            "progress": 0,
            "message": f"Found {total_files} sample files to ingest",
            "total_files": total_files,
            "overall_progress": 0
        }) + "\n"

        # Allow the event loop to flush this message
        await asyncio.sleep(0)

        for idx, file_path in enumerate(sample_files):
            file_name = file_path.name
            file_progress_base = int((idx / total_files) * 100)
            file_progress_range = 100 / total_files  # Each file gets this % of overall progress

            # Initial file message
            yield json.dumps({
                "phase": "reading",
                "progress": 0,
                "message": f"📄 Reading {file_name}...",
                "current_file": file_name,
                "file_index": idx + 1,
                "total_files": total_files,
                "overall_progress": file_progress_base
            }) + "\n"
            await asyncio.sleep(0)  # Flush

            try:
                # Handle compressed files
                if file_path.suffix == ".gz":
                    yield json.dumps({
                        "phase": "decompressing",
                        "progress": 5,
                        "message": f"📦 Decompressing {file_name}...",
                        "current_file": file_name,
                        "file_index": idx + 1,
                        "total_files": total_files,
                        "overall_progress": file_progress_base + 2
                    }) + "\n"
                    await asyncio.sleep(0)

                    temp_dir = script_dir / "source_data" / "temp"
                    temp_dir.mkdir(parents=True, exist_ok=True)
                    original_name = file_path.stem
                    temp_path = temp_dir / original_name

                    with gzip.open(file_path, 'rb') as f_in:
                        with open(temp_path, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)

                    ingest_path = temp_path
                else:
                    ingest_path = file_path

                # Process through ingestion pipeline using a queue to get updates
                import queue
                import threading

                update_queue = queue.Queue()
                processing_done = threading.Event()

                def run_pipeline():
                    """Run the blocking pipeline in a thread, putting updates in queue."""
                    try:
                        for update in process_file_pipeline_streaming(ingest_path, collection):
                            update_queue.put(update)
                    finally:
                        processing_done.set()

                # Start pipeline in background thread
                thread = threading.Thread(target=run_pipeline, daemon=True)
                thread.start()

                # Stream updates as they come in
                last_phase = "reading"
                while not processing_done.is_set() or not update_queue.empty():
                    try:
                        update = update_queue.get(timeout=0.1)
                        update_data = json.loads(update.strip())

                        # Add file context
                        update_data["current_file"] = file_name
                        update_data["file_index"] = idx + 1
                        update_data["total_files"] = total_files

                        # Get phase/status
                        phase = update_data.get("status") or update_data.get("phase", "processing")
                        update_data["phase"] = phase

                        # Calculate overall progress based on phase within file
                        phase_weights = {"reading": 10, "analyzing": 50, "embedding": 90, "complete": 100}
                        phase_progress = phase_weights.get(phase, 50)

                        # If we have batch progress, use it
                        if "total" in update_data and update_data["total"] > 0:
                            batch_frac = update_data.get("progress", 0) / update_data["total"]
                            if phase == "analyzing":
                                phase_progress = 10 + int(40 * batch_frac)  # 10-50%
                            elif phase == "embedding":
                                phase_progress = 50 + int(50 * batch_frac)  # 50-100%

                        overall = file_progress_base + int((phase_progress / 100) * file_progress_range)
                        update_data["overall_progress"] = min(overall, 99)

                        # Add emoji indicators
                        if phase != last_phase:
                            emoji = {"reading": "📄", "analyzing": "🔍", "embedding": "💾", "complete": "✅"}.get(phase, "⏳")
                            update_data["message"] = f"{emoji} {update_data.get('message', phase.title())}"
                            last_phase = phase

                        yield json.dumps(update_data) + "\n"
                    except queue.Empty:
                        await asyncio.sleep(0.05)  # Brief sleep to yield to event loop
                        continue
                    except json.JSONDecodeError:
                        yield update

                thread.join(timeout=1)  # Wait for thread to finish

                # Clean up temp file if we created one
                if file_path.suffix == ".gz" and temp_path.exists():
                    temp_path.unlink()

            except Exception as e:
                logger.exception(f"Error processing sample file {file_name}")
                yield json.dumps({
                    "phase": "error",
                    "progress": file_progress_base,
                    "message": f"❌ Error processing {file_name}: {str(e)[:100]}",
                    "current_file": file_name,
                    "overall_progress": file_progress_base
                }) + "\n"
                continue

        yield json.dumps({
            "phase": "complete",
            "progress": 100,
            "message": f"✅ Successfully ingested {total_files} sample files",
            "total_files": total_files,
            "overall_progress": 100
        }) + "\n"

    return StreamingResponse(
        stream_sample_ingestion(),
        media_type="application/x-ndjson"
    )


@router.delete("/knowledge-base/purge")
@limiter.limit(RateLimits.PURGE)
async def purge_knowledge_base(
    request: Request,
    confirmation: str = Query(
        ...,
        description="Safety confirmation. Must be 'CONFIRM_PURGE_ALL_DATA' to proceed."
    )
):
    """
    Purge all documents from the knowledge base.

    WARNING: This permanently deletes all ingested data.
    Requires explicit confirmation parameter for safety.

    Rate limited to 1 request per hour per IP.
    """
    # Require explicit confirmation to prevent accidental deletion
    if confirmation != "CONFIRM_PURGE_ALL_DATA":
        raise HTTPException(
            status_code=400,
            detail="Safety confirmation required. Pass confirmation='CONFIRM_PURGE_ALL_DATA' to proceed."
        )

    try:
        collection = get_collection()

        # Get current count before purge
        all_docs = collection.get()
        doc_count = len(all_docs.get("ids", []))

        if doc_count == 0:
            return {
                "status": "success",
                "message": "Knowledge base is already empty",
                "deleted_count": 0
            }

        # Delete all documents by getting all IDs and deleting them
        all_ids = all_docs.get("ids", [])
        if all_ids:
            collection.delete(ids=all_ids)

        logger.info(f"Purged {doc_count} documents from knowledge base")

        return {
            "status": "success",
            "message": f"Successfully purged {doc_count} documents",
            "deleted_count": doc_count
        }

    except Exception as e:
        logger.exception("Error purging knowledge base")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while purging the knowledge base."
        )


@router.get("/knowledge-base/connectors")
async def list_connectors() -> Dict[str, Any]:
    """
    List all available G7 data connectors.

    Returns connectors grouped by country.
    """
    result: Dict[str, List[Dict[str, Any]]] = {}

    for country, connectors in CONNECTORS.items():
        result[country] = []
        for connector_id, connector in connectors.items():
            result[country].append(connector.to_dict())

    return {"connectors": result}


@router.get("/knowledge-base/connectors/{connector_id}/datasets")
async def list_connector_datasets(connector_id: str) -> Dict[str, Any]:
    """
    List available datasets for a specific connector.
    """
    connector = _find_connector(connector_id)
    if not connector:
        raise HTTPException(
            status_code=404,
            detail=f"Connector '{connector_id}' not found"
        )

    datasets = await connector.list_datasets()

    return {
        "datasets": [
            {
                "id": ds.id,
                "name": ds.name,
                "description": ds.description,
                "asset_type": ds.asset_type,
                "estimated_records": ds.estimated_records,
                "last_updated": ds.last_updated,
            }
            for ds in datasets
        ]
    }


# =============================================================================
# Internal Functions
# =============================================================================

async def _ingest_file(file: Optional[UploadFile]) -> StreamingResponse:
    """Handle file upload ingestion."""
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")

    ALLOWED_EXTENSIONS = {".pdf", ".txt", ".csv", ".md", ".json", ".html"}
    ALLOWED_CONTENT_TYPES = {
        "application/pdf",
        "text/plain",
        "text/csv",
        "text/markdown",
        "application/json",
        "text/html",
    }

    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
        # Allow if extension is valid (some browsers send wrong content-type)
        pass

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

    return StreamingResponse(
        process_file_pipeline_streaming(temp_path, collection),
        media_type="application/x-ndjson",
    )


async def _ingest_connector(
    connector_id: Optional[str],
    dataset_id: Optional[str],
    limit: int
) -> StreamingResponse:
    """Handle G7 connector import."""
    if not connector_id:
        raise HTTPException(status_code=400, detail="connector_id is required")

    connector = _find_connector(connector_id)
    if not connector:
        raise HTTPException(
            status_code=404,
            detail=f"Connector '{connector_id}' not found"
        )

    # Get dataset ID if not provided
    if not dataset_id:
        try:
            datasets = await connector.list_datasets()
            if datasets:
                dataset_id = datasets[0].id
            else:
                raise HTTPException(
                    status_code=400,
                    detail="No datasets available for this connector"
                )
        except Exception as e:
            logger.exception(f"Error listing datasets for {connector_id}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to list datasets: {str(e)}"
            )

    # Get connector metadata
    connector_country = getattr(connector, 'country', '')

    async def stream_connector_import():
        """Stream connector import with full pipeline processing."""
        all_records = []
        dataset_title = dataset_id

        try:
            # Phase 1: Fetch data from connector (0-50%)
            async for update in connector.import_dataset(dataset_id, limit):
                phase = update.get("phase", "")

                if phase == "completed":
                    all_records = update.get("records", [])
                    if all_records and all_records[0].get("dataset_title"):
                        dataset_title = all_records[0]["dataset_title"]

                    yield json.dumps({
                        "phase": "fetched",
                        "progress": 50,
                        "message": f"Fetched {len(all_records)} records from {connector_id}",
                        "fetched_count": len(all_records)
                    }) + "\n"

                elif phase == "error":
                    yield json.dumps(update) + "\n"
                    return
                else:
                    # Scale progress to 0-50%
                    progress = update.get("progress", 0)
                    scaled_progress = int(progress * 0.5)
                    update["progress"] = scaled_progress
                    yield json.dumps(update) + "\n"

            # Phase 2: Process through full pipeline (50-100%)
            if all_records:
                collection = get_collection()

                # Use the new direct pipeline function (no temp file needed)
                for pipeline_update in process_records_pipeline_streaming(
                    records=all_records,
                    source_id=dataset_id,
                    source_title=dataset_title,
                    connector_id=connector_id,
                    country=connector_country,
                    collection=collection
                ):
                    try:
                        update_data = json.loads(pipeline_update.strip())
                        # Scale pipeline progress from 50-100%
                        status = update_data.get("status", "")
                        if status == "reading":
                            update_data["progress"] = 55
                        elif status == "analyzing":
                            # Map analyzing progress
                            prog = update_data.get("progress", 0)
                            total = update_data.get("total", 1)
                            update_data["progress"] = 55 + int(20 * prog / max(total, 1))
                        elif status == "embedding":
                            # Map embedding progress
                            prog = update_data.get("progress", 0)
                            total = update_data.get("total", 1)
                            update_data["progress"] = 75 + int(20 * prog / max(total, 1))
                        elif status == "complete":
                            update_data["progress"] = 100

                        # Convert status to phase for consistency
                        if "status" in update_data:
                            update_data["phase"] = update_data.pop("status")

                        yield json.dumps(update_data) + "\n"
                    except json.JSONDecodeError:
                        yield pipeline_update

            else:
                yield json.dumps({
                    "phase": "complete",
                    "progress": 100,
                    "message": "No records to process",
                    "stored_count": 0
                }) + "\n"

        except Exception as e:
            logger.exception(f"Connector import error for {connector_id}")
            yield json.dumps({
                "phase": "error",
                "progress": 0,
                "message": f"Import failed: {str(e)[:100]}"
            }) + "\n"

    return StreamingResponse(
        stream_connector_import(),
        media_type="application/x-ndjson"
    )


def _find_connector(connector_id: str):
    """Find a connector by ID across all countries."""
    connector_id = connector_id.lower()

    for country, connectors in CONNECTORS.items():
        if connector_id in connectors:
            return connectors[connector_id]

    return None
