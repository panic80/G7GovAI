"""
Text and Markdown file parser.
"""

import logging
from pathlib import Path
from typing import List

from .base import BaseParser, ParseResult, ParsedDocument

logger = logging.getLogger(__name__)


class TextParser(BaseParser):
    """Parser for plain text and markdown files."""

    supported_extensions = [".txt", ".md"]

    def parse(self, file_path: Path) -> ParseResult:
        """Parse a text or markdown file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            clean_content = self.clean_text(content)

            if not clean_content:
                return ParseResult(
                    documents=[],
                    file_type=file_path.suffix.lower(),
                    source_path=str(file_path),
                    error="File is empty after cleaning"
                )

            return ParseResult(
                documents=[ParsedDocument(content=clean_content)],
                file_type=file_path.suffix.lower(),
                source_path=str(file_path)
            )

        except Exception as e:
            logger.error(f"Error parsing text file {file_path}: {e}")
            return ParseResult(
                documents=[],
                file_type=file_path.suffix.lower(),
                source_path=str(file_path),
                error=str(e)
            )
