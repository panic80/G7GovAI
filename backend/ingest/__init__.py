"""
Ingest module - Document ingestion pipeline.

This module provides a modular architecture for document ingestion:
- parsers/: File type specific parsers (PDF, CSV, HTML, TXT, etc.)
- analyzer.py: LLM-based document analysis and categorization
- chunking.py: Text splitting and chunking
- pipeline.py: Orchestration of the full ingestion flow

Public API:
- ingest_file(): Process a single file
- ingest_directory(): Process all files in a directory

For backward compatibility, this module re-exports the original ingest.py functions.
"""

import sys
from pathlib import Path

# Add parent to path for imports
_module_dir = Path(__file__).resolve().parent
_backend_dir = _module_dir.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

# Re-export from parsers
from .parsers import (
    BaseParser,
    ParseResult,
    ParsedDocument,
    get_parser,
    PARSERS,
)

# For backward compatibility, import from the original ingest.py
# This allows gradual migration
# Note: We need to use importlib because both ingest.py and ingest/ exist
import importlib.util
_ingest_legacy_path = _backend_dir / "ingest.py"
if _ingest_legacy_path.exists():
    _spec = importlib.util.spec_from_file_location("ingest_legacy", _ingest_legacy_path)
    _ingest_module = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_ingest_module)

    # Re-export functions
    process_file_pipeline_streaming = _ingest_module.process_file_pipeline_streaming
    process_records_pipeline_streaming = _ingest_module.process_records_pipeline_streaming
    process_document = _ingest_module.process_document
    analyze_document = _ingest_module.analyze_document
    clean_text = _ingest_module.clean_text

__all__ = [
    # Parser exports
    "BaseParser",
    "ParseResult",
    "ParsedDocument",
    "get_parser",
    "PARSERS",
    # Legacy exports (backward compatibility)
    "process_file_pipeline_streaming",
    "process_records_pipeline_streaming",
    "process_document",
    "analyze_document",
    "clean_text",
]
