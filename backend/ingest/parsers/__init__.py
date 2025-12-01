"""
Document parsers for various file types.

This module provides a unified interface for parsing different document types.
"""

from pathlib import Path
from typing import Optional

from .base import BaseParser, ParseResult, ParsedDocument
from .text import TextParser
from .html import HTMLParser
from .pdf import PDFParser
from .csv_parser import CSVParser

__all__ = [
    "BaseParser",
    "ParseResult",
    "ParsedDocument",
    "TextParser",
    "HTMLParser",
    "PDFParser",
    "CSVParser",
    "get_parser",
    "PARSERS",
]

# Registry of all available parsers
PARSERS = [
    TextParser(),
    HTMLParser(),
    PDFParser(),
    CSVParser(),
]


def get_parser(file_path: Path) -> Optional[BaseParser]:
    """
    Get the appropriate parser for a file based on its extension.

    Args:
        file_path: Path to the file to parse

    Returns:
        A parser instance that can handle the file, or None if no parser found
    """
    for parser in PARSERS:
        if parser.can_parse(file_path):
            return parser
    return None
