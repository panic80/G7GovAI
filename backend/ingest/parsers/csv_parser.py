"""
CSV file parser.
"""

import csv
import logging
from pathlib import Path
from typing import List

from .base import BaseParser, ParseResult, ParsedDocument

logger = logging.getLogger(__name__)


class CSVParser(BaseParser):
    """Parser for CSV files with QP Notes schema support."""

    supported_extensions = [".csv"]

    # QP Notes specific columns
    QP_NOTES_COLUMNS = [
        "title_en",
        "question_en",
        "response_en",
        "background_en",
        "additional_information_en",
    ]

    def parse(self, file_path: Path) -> ParseResult:
        """Parse a CSV file, handling QP Notes format specially."""
        try:
            documents: List[ParsedDocument] = []

            with open(file_path, "r", encoding="utf-8") as f:
                # Check for header
                sample = f.read(1024)
                f.seek(0)

                try:
                    has_header = csv.Sniffer().has_header(sample)
                except csv.Error:
                    has_header = True  # Assume header exists

                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames or []

                # Detect QP Notes schema
                is_qp_notes = any(col in fieldnames for col in self.QP_NOTES_COLUMNS)

                logger.debug(f"CSV Analysis - Is QP Notes? {is_qp_notes}. Columns: {fieldnames}")

                for row in reader:
                    doc = self._parse_row(row, fieldnames, is_qp_notes)
                    if doc:
                        documents.append(doc)

            if not documents:
                return ParseResult(
                    documents=[],
                    file_type=".csv",
                    source_path=str(file_path),
                    is_multi_row=True,
                    error="No rows extracted from CSV"
                )

            return ParseResult(
                documents=documents,
                file_type=".csv",
                source_path=str(file_path),
                is_multi_row=True
            )

        except Exception as e:
            logger.error(f"Error parsing CSV file {file_path}: {e}")
            return ParseResult(
                documents=[],
                file_type=".csv",
                source_path=str(file_path),
                is_multi_row=True,
                error=str(e)
            )

    def _parse_row(self, row: dict, fieldnames: List[str], is_qp_notes: bool) -> ParsedDocument | None:
        """Parse a single CSV row into a ParsedDocument."""
        row_text_parts = []
        row_title = None

        if is_qp_notes:
            # Extract title separately for QP Notes
            row_title = row.get("title_en", "").strip() or None

            # Extract specific columns
            for col in self.QP_NOTES_COLUMNS:
                if col in row and row[col]:
                    row_text_parts.append(row[col].strip())
        else:
            # Generic extraction
            for k, v in row.items():
                if v and str(v).strip():
                    row_text_parts.append(f"{k}: {str(v).strip()}")

        if not row_text_parts:
            return None

        content = " | ".join(row_text_parts)
        return ParsedDocument(content=content, title=row_title)
