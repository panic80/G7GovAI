"""
HTML file parser.
"""

import logging
from pathlib import Path
from bs4 import BeautifulSoup

from .base import BaseParser, ParseResult, ParsedDocument

logger = logging.getLogger(__name__)


class HTMLParser(BaseParser):
    """Parser for HTML files."""

    supported_extensions = [".html", ".htm"]

    # Tags to remove from HTML
    REMOVE_TAGS = [
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

    # Selectors to try for main content (in priority order)
    CONTENT_SELECTORS = [
        ("main", {}),
        ("article", {}),
        ("div", {"class": "main-container"}),
        ("div", {"id": "wb-cont"}),  # Canada.ca content ID
    ]

    def parse(self, file_path: Path) -> ParseResult:
        """Parse an HTML file and extract main content."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                html_content = f.read()

            soup = BeautifulSoup(html_content, "html.parser")

            # Remove unwanted tags
            for tag in soup(self.REMOVE_TAGS):
                tag.decompose()

            # Try to find main content container
            content_div = None
            for tag, attrs in self.CONTENT_SELECTORS:
                content_div = soup.find(tag, attrs) if attrs else soup.find(tag)
                if content_div:
                    break

            # Fallback to body
            if not content_div:
                content_div = soup.body

            if not content_div:
                return ParseResult(
                    documents=[],
                    file_type=".html",
                    source_path=str(file_path),
                    error="No content found in HTML"
                )

            content = content_div.get_text(separator="\n\n")
            clean_content = self.clean_text(content)

            if not clean_content:
                return ParseResult(
                    documents=[],
                    file_type=".html",
                    source_path=str(file_path),
                    error="HTML content is empty after cleaning"
                )

            # Try to extract title
            title = None
            title_tag = soup.find("title")
            if title_tag:
                title = title_tag.get_text().strip()

            return ParseResult(
                documents=[ParsedDocument(content=clean_content, title=title)],
                file_type=".html",
                source_path=str(file_path)
            )

        except Exception as e:
            logger.error(f"Error parsing HTML file {file_path}: {e}")
            return ParseResult(
                documents=[],
                file_type=".html",
                source_path=str(file_path),
                error=str(e)
            )
