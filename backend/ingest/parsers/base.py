"""
Base parser interface for document extraction.

All file type parsers should inherit from this base class.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ParsedDocument:
    """Represents a parsed document or document chunk."""
    content: str
    title: Optional[str] = None
    metadata: Optional[Dict] = None


@dataclass
class ParseResult:
    """Result of parsing a file."""
    documents: List[ParsedDocument]
    file_type: str
    source_path: str
    is_multi_row: bool = False  # True for CSV/JSON where each row is a document
    error: Optional[str] = None


class BaseParser(ABC):
    """Abstract base class for file parsers."""

    supported_extensions: List[str] = []

    @classmethod
    def can_parse(cls, file_path: Path) -> bool:
        """Check if this parser can handle the given file."""
        return file_path.suffix.lower() in cls.supported_extensions

    @abstractmethod
    def parse(self, file_path: Path) -> ParseResult:
        """
        Parse a file and extract its content.

        Args:
            file_path: Path to the file to parse

        Returns:
            ParseResult containing the extracted documents
        """
        pass

    @staticmethod
    def clean_text(text: str) -> str:
        """Clean up excessive whitespace and newlines."""
        import re
        if not text:
            return ""
        clean = re.sub(r"\n\s*\n", "\n\n", text).strip()
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean
