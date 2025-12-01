"""
PDF file parser.
"""

import logging
from pathlib import Path
from typing import Optional

from .base import BaseParser, ParseResult, ParsedDocument

logger = logging.getLogger(__name__)

# Optional import for pdfplumber
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    pdfplumber = None
    PDFPLUMBER_AVAILABLE = False


class PDFParser(BaseParser):
    """Parser for PDF files using pdfplumber."""

    supported_extensions = [".pdf"]

    def parse(self, file_path: Path) -> ParseResult:
        """Parse a PDF file and extract text with table support."""
        if not PDFPLUMBER_AVAILABLE:
            logger.warning("pdfplumber not installed, cannot parse PDF files")
            return ParseResult(
                documents=[],
                file_type=".pdf",
                source_path=str(file_path),
                error="pdfplumber not installed"
            )

        try:
            full_text = ""
            pdf_metadata = {}

            with pdfplumber.open(file_path) as pdf:
                pdf_metadata = pdf.metadata or {}

                for page in pdf.pages:
                    # Extract text
                    text = page.extract_text() or ""

                    # Extract and format tables as Markdown
                    table_text = self._extract_tables_as_markdown(page)

                    # Combine text and tables
                    full_text += f"{text}\n{table_text}\n\n"

            clean_content = self.clean_text(full_text)

            if not clean_content:
                return ParseResult(
                    documents=[],
                    file_type=".pdf",
                    source_path=str(file_path),
                    error="PDF content is empty after extraction"
                )

            # Try to get title from metadata
            title = pdf_metadata.get("Title") or pdf_metadata.get("title")

            return ParseResult(
                documents=[ParsedDocument(
                    content=clean_content,
                    title=title,
                    metadata=pdf_metadata
                )],
                file_type=".pdf",
                source_path=str(file_path)
            )

        except Exception as e:
            logger.error(f"Error parsing PDF file {file_path}: {e}")
            return ParseResult(
                documents=[],
                file_type=".pdf",
                source_path=str(file_path),
                error=str(e)
            )

    def _extract_tables_as_markdown(self, page) -> str:
        """Extract tables from a PDF page and format as Markdown."""
        tables = page.extract_tables()
        table_text = ""

        for table in tables:
            if not table:
                continue

            # Filter out None values
            cleaned_table = [
                [cell if cell is not None else "" for cell in row]
                for row in table
            ]

            if len(cleaned_table) == 0:
                continue

            # Header row
            headers = cleaned_table[0]
            headers = [h.replace("\n", " ") for h in headers]
            table_text += "\n\n| " + " | ".join(headers) + " |\n"
            table_text += "| " + " | ".join(["---"] * len(headers)) + " |\n"

            # Data rows
            for row in cleaned_table[1:]:
                row = [c.replace("\n", " ") for c in row]
                table_text += "| " + " | ".join(row) + " |\n"

            table_text += "\n"

        return table_text
