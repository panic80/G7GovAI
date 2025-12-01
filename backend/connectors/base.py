"""
Base Connector Utilities
========================
Shared utilities for all G7 data connectors.

Provides common methods for:
- Estimating record counts from file metadata
- Fetching CSV/JSON previews without full download
- Parsing tabular data
- SSL handling with fallback for government sites
- Shared dataclasses and mixins for connectors
"""

import aiohttp
import csv
import io
import json
import logging
import ssl
import certifi
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Optional, AsyncIterator

logger = logging.getLogger(__name__)


# =============================================================================
# Shared Dataclasses
# =============================================================================

@dataclass
class DatasetInfo:
    """Information about an available dataset."""
    id: str
    name: str
    description: str
    asset_type: str
    estimated_records: int
    last_updated: Optional[str] = None


@dataclass
class ImportResult:
    """Result of a data import operation."""
    success: bool
    records_imported: int
    errors: List[str]
    dataset_id: str
    duration_ms: int


# =============================================================================
# Session Manager Mixin
# =============================================================================

class SessionManagerMixin:
    """
    Mixin providing aiohttp session management for connectors.

    Requires the class to have:
    - self.timeout: aiohttp.ClientTimeout
    - self.session: Optional[aiohttp.ClientSession]
    """
    session: Optional[aiohttp.ClientSession] = None
    timeout: aiohttp.ClientTimeout

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self.session

    async def close(self):
        """Close the session."""
        if self.session and not self.session.closed:
            await self.session.close()


# =============================================================================
# SSL Utilities
# =============================================================================


def create_ssl_context(verify: bool = True) -> ssl.SSLContext:
    """
    Create an SSL context with proper certificate verification.

    Uses certifi certificates for maximum compatibility.
    Falls back to unverified context only when explicitly requested.

    Args:
        verify: Whether to verify SSL certificates (default True)

    Returns:
        Configured SSL context
    """
    if verify:
        ctx = ssl.create_default_context(cafile=certifi.where())
        return ctx
    else:
        # Unverified context - logs warning
        logger.warning("Creating unverified SSL context - use only for known problematic endpoints")
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

# User-Agent header to avoid being blocked by servers
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; GovAI/1.0; +https://github.com/govai)',
    'Accept': 'text/csv,application/csv,text/plain,*/*',
}


async def estimate_csv_rows(url: str, session: aiohttp.ClientSession) -> int:
    """
    Estimate row count from a CSV file using HTTP HEAD + Content-Length.

    Uses heuristic of ~100 bytes per row (typical for government statistics data).

    Args:
        url: URL of the CSV file
        session: aiohttp session

    Returns:
        Estimated number of rows, or 0 if cannot estimate
    """
    try:
        async with session.head(
            url,
            headers=DEFAULT_HEADERS,
            allow_redirects=True,
            timeout=aiohttp.ClientTimeout(total=10)
        ) as resp:
            if resp.status == 200:
                content_length = int(resp.headers.get('Content-Length', 0))
                if content_length > 0:
                    # Heuristic: ~100 bytes per row for typical CSV data
                    return max(1, content_length // 100)
    except Exception:
        pass
    return 0


async def estimate_rows_from_url(url: str, session: aiohttp.ClientSession) -> int:
    """
    Estimate row count from a file URL using HTTP HEAD request.

    More robust than estimate_csv_rows - works with various content types
    and handles redirects properly.

    Args:
        url: URL of the data file
        session: aiohttp session

    Returns:
        Estimated number of rows, or 0 if cannot estimate
    """
    try:
        # Try with proper SSL first, fall back to unverified if needed
        ssl_context = create_ssl_context(verify=True)
        async with session.head(
            url,
            headers=DEFAULT_HEADERS,
            allow_redirects=True,
            timeout=aiohttp.ClientTimeout(total=15),
            ssl=ssl_context
        ) as resp:
            if resp.status == 200:
                content_length = int(resp.headers.get('Content-Length', 0))
                content_type = resp.headers.get('Content-Type', '').lower()

                if content_length > 0:
                    # Estimate based on content type
                    if 'csv' in content_type or 'text/plain' in content_type:
                        return max(1, content_length // 100)  # ~100 bytes/row
                    elif 'json' in content_type:
                        return max(1, content_length // 200)  # ~200 bytes/row
                    elif 'xml' in content_type:
                        return max(1, content_length // 300)  # ~300 bytes/row
                    else:
                        # Default estimate for unknown types
                        return max(1, content_length // 150)
    except Exception as e:
        logger.debug(f"HEAD request failed for {url}: {e}")
    return 0


async def fetch_csv_preview(
    url: str,
    session: aiohttp.ClientSession,
    limit: Optional[int] = 100,
    encoding: str = 'utf-8'
) -> List[Dict[str, Any]]:
    """
    Fetch first N rows of a CSV file without downloading the entire file.

    Streams the first 100KB and parses available rows.
    Handles redirects, various encodings, and adds proper headers.

    Args:
        url: URL of the CSV file
        session: aiohttp session
        limit: Maximum number of rows to return
        encoding: Primary character encoding to try (default utf-8)

    Returns:
        List of dictionaries representing CSV rows
    """
    records = []

    # Encodings to try (German/French government data often uses these)
    encodings_to_try = [encoding, 'utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    # Remove duplicates while preserving order
    seen = set()
    encodings_to_try = [e for e in encodings_to_try if not (e in seen or seen.add(e))]

    try:
        timeout = aiohttp.ClientTimeout(total=30)
        ssl_context = create_ssl_context(verify=True)
        async with session.get(
            url,
            headers=DEFAULT_HEADERS,
            allow_redirects=True,
            timeout=timeout,
            ssl=ssl_context
        ) as response:
            if response.status == 200:
                # Check Content-Type - skip HTML pages
                content_type = response.headers.get('Content-Type', '').lower()
                if 'html' in content_type:
                    logger.debug(f"Skipping HTML response for {url}")
                    return records

                # Read first 100KB max to get preview
                content = await response.content.read(100 * 1024)

                # Double-check content isn't HTML (some servers send wrong Content-Type)
                if content[:100].lower().startswith((b'<!doctype', b'<html', b'<?xml')):
                    logger.debug(f"Content looks like HTML/XML for {url}")
                    return records

                # Try different encodings until one works
                text = None
                for enc in encodings_to_try:
                    try:
                        text = content.decode(enc)
                        # Verify it's valid by checking for common issues
                        if '\x00' not in text:  # Binary file check
                            break
                    except (UnicodeDecodeError, LookupError):
                        continue

                if text is None:
                    # Last resort: decode with errors='ignore'
                    text = content.decode('utf-8', errors='ignore')

                # Handle potential BOM
                if text.startswith('\ufeff'):
                    text = text[1:]

                # Try to detect delimiter (some EU data uses semicolons)
                first_line = text.split('\n')[0] if '\n' in text else text
                delimiter = ';' if first_line.count(';') > first_line.count(',') else ','

                reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
                for i, row in enumerate(reader):
                    if limit is not None and i >= limit:
                        break
                    # Clean up keys and values
                    clean_row = {k.strip(): v.strip() if isinstance(v, str) else v
                                 for k, v in row.items() if k}
                    if clean_row:  # Skip empty rows
                        records.append(clean_row)
            else:
                logger.debug(f"CSV preview got HTTP {response.status} for {url}")

    except aiohttp.ClientError as e:
        logger.debug(f"CSV preview connection error for {url}: {e}")
    except Exception as e:
        logger.debug(f"CSV preview error for {url}: {e}")

    return records


async def fetch_json_preview(
    url: str,
    session: aiohttp.ClientSession,
    limit: int = 100,
    data_path: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Fetch preview of a JSON data file.

    Args:
        url: URL of the JSON file
        session: aiohttp session
        limit: Maximum records to return
        data_path: Path to data array in JSON structure (e.g., ["result", "records"])

    Returns:
        List of dictionaries representing data records
    """
    records = []
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with session.get(url, timeout=timeout) as response:
            if response.status == 200:
                # Read up to 500KB for JSON preview
                content = await response.content.read(500 * 1024)
                text = content.decode('utf-8', errors='ignore')

                try:
                    data = json.loads(text)

                    # Navigate to data path if specified
                    if data_path:
                        for key in data_path:
                            if isinstance(data, dict):
                                data = data.get(key, [])
                            else:
                                break

                    # Extract records
                    if isinstance(data, list):
                        records = data[:limit]
                    elif isinstance(data, dict):
                        # Single record
                        records = [data]
                except json.JSONDecodeError:
                    pass
    except Exception as e:
        logger.warning(f"JSON preview error for {url}: {e}")
    return records


async def get_datastore_info(
    base_url: str,
    resource_id: str,
    session: aiohttp.ClientSession
) -> Optional[Dict[str, Any]]:
    """
    Query CKAN DataStore for resource row count and schema.

    Args:
        base_url: CKAN API base URL
        resource_id: Resource ID to query
        session: aiohttp session

    Returns:
        Dictionary with 'total' row count and 'fields' schema, or None
    """
    try:
        url = f"{base_url}/action/datastore_search"
        params = {"resource_id": resource_id, "limit": 0, "include_total": "true"}

        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("success"):
                    result = data.get("result", {})
                    return {
                        "total": result.get("total", 0),
                        "fields": result.get("fields", [])
                    }
    except Exception as e:
        logger.warning(f"DataStore info error: {e}")
    return None


async def fetch_from_datastore(
    base_url: str,
    resource_id: str,
    session: aiohttp.ClientSession,
    limit: Optional[int] = 100
) -> List[Dict[str, Any]]:
    """
    Fetch actual data rows from CKAN DataStore.

    Args:
        base_url: CKAN API base URL
        resource_id: Resource ID to query
        session: aiohttp session
        limit: Maximum rows to return (None for no limit)

    Returns:
        List of data records
    """
    try:
        url = f"{base_url}/action/datastore_search"
        params = {"resource_id": resource_id}
        if limit is not None:
            params["limit"] = limit

        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("success"):
                    result = data.get("result", {})
                    records = result.get("records", [])
                    # Remove internal _id field from records
                    return [{k: v for k, v in r.items() if not k.startswith('_')}
                            for r in records]
    except Exception as e:
        logger.warning(f"DataStore fetch error: {e}")
    return []


def estimate_records_from_filesize(filesize: int, format_type: str = "csv") -> int:
    """
    Estimate record count from file size.

    Args:
        filesize: File size in bytes
        format_type: File format (csv, json, xml)

    Returns:
        Estimated record count
    """
    if not filesize or filesize <= 0:
        return 0

    # Bytes per record heuristic by format
    bytes_per_record = {
        "csv": 100,
        "json": 200,
        "xml": 300,
        "xlsx": 150,
        "xls": 150,
    }

    divisor = bytes_per_record.get(format_type.lower(), 100)
    return max(1, filesize // divisor)


# =============================================================================
# Abstract Base Connector
# =============================================================================

class BaseConnector(ABC, SessionManagerMixin):
    """
    Abstract base class for all G7 data connectors.

    Provides:
    - Common session management (via SessionManagerMixin)
    - Standard progress/error/completion helpers
    - Enforced interface for connector implementations

    Subclasses must implement:
    - connector_id, country, name, description properties
    - list_datasets() method
    - import_dataset() async generator method
    """

    def __init__(self, timeout: int = 30):
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session: Optional[aiohttp.ClientSession] = None

    # -------------------------------------------------------------------------
    # Required Properties (must be implemented by subclasses)
    # -------------------------------------------------------------------------

    @property
    @abstractmethod
    def connector_id(self) -> str:
        """Unique identifier for this connector (e.g., 'census', 'istat')."""
        pass

    @property
    @abstractmethod
    def country(self) -> str:
        """Two-letter country code (ISO 3166-1 alpha-2)."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for display."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Brief description of the data source."""
        pass

    # -------------------------------------------------------------------------
    # Required Methods (must be implemented by subclasses)
    # -------------------------------------------------------------------------

    @abstractmethod
    async def list_datasets(self) -> List[DatasetInfo]:
        """
        List available datasets from this data source.

        Returns:
            List of DatasetInfo objects describing available datasets.
        """
        pass

    @abstractmethod
    async def import_dataset(
        self,
        dataset_id: str,
        limit: Optional[int] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Import data from a specific dataset.

        Yields progress updates during import, followed by final result.

        Args:
            dataset_id: ID of the dataset to import
            limit: Maximum records to import (None for no limit)

        Yields:
            Progress dicts with 'phase', 'progress', 'message' keys.
            Final yield includes 'records' and 'count'.
        """
        pass

    # -------------------------------------------------------------------------
    # Concrete Methods (shared by all connectors)
    # -------------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialize connector info for API response."""
        return {
            "id": self.connector_id,
            "name": self.name,
            "country": self.country,
            "description": self.description,
        }

    def _progress(self, phase: str, progress: int, message: str) -> Dict[str, Any]:
        """Create a progress update dict."""
        return {"phase": phase, "progress": progress, "message": message}

    def _error(self, progress: int, message: str) -> Dict[str, Any]:
        """Create an error update dict."""
        return {"phase": "error", "progress": progress, "message": message}

    def _completed(
        self,
        records: List[Dict],
        duration_ms: int,
        message: Optional[str] = None,
        **extra
    ) -> Dict[str, Any]:
        """Create a completion result dict."""
        result = {
            "phase": "completed",
            "progress": 100,
            "message": message or f"Import complete: {len(records)} records in {duration_ms}ms",
            "records": records,
            "count": len(records),
            "duration_ms": duration_ms,
        }
        result.update(extra)
        return result


# =============================================================================
# CKAN Connector Base Class
# =============================================================================

class CKANConnector(BaseConnector):
    """
    Base class for CKAN-based government data portals.

    CKAN (Comprehensive Knowledge Archive Network) is used by many government
    open data portals including data.gov (US), dati.gov.it (IT), govdata.de (DE).

    Subclasses should set:
    - BASE_URL: The CKAN API base URL
    - SOURCE_NAME: Human-readable source name for records
    - DATASET_SEARCHES: Dict mapping search_id -> {query, asset_type}

    Subclasses can override:
    - _get_api_endpoints(): For non-standard API structures
    - _filter_tabular_resources(): For custom resource filtering
    - _fetch_resource_data(): For custom data fetching (e.g., France's Tabular API)
    """

    BASE_URL: str = ""  # Must be set by subclass
    SOURCE_NAME: str = ""  # Must be set by subclass
    DATASET_SEARCHES: Dict[str, Dict[str, str]] = {}  # Must be set by subclass

    def _get_api_endpoints(self) -> Dict[str, str]:
        """
        Return CKAN API endpoints.
        Override for non-standard APIs (e.g., data.gouv.fr).
        """
        return {
            "search": f"{self.BASE_URL}/action/package_search",
            "show": f"{self.BASE_URL}/action/package_show",
        }

    def _get_api_result_path(self, response_data: Dict) -> Any:
        """
        Extract result from API response.
        Standard CKAN returns {"success": true, "result": {...}}.
        Override for different structures.
        """
        return response_data.get("result", {})

    def _filter_tabular_resources(self, resources: List[Dict]) -> List[Dict]:
        """
        Filter resources to tabular formats.
        Override in Germany for permissive fallback.
        """
        return [
            r for r in resources
            if (r.get("format") or "").upper() in ("CSV", "JSON", "XLSX", "XLS", "")
        ]

    async def _fetch_resource_data(
        self,
        resource: Dict[str, Any],
        dataset_id: str,
        dataset_title: str,
        session: aiohttp.ClientSession,
        limit: Optional[int]
    ) -> List[Dict[str, Any]]:
        """
        Fetch data from a single resource.
        Override in France for Tabular API support.
        """
        records = []
        resource_id = resource.get("id")
        resource_url = resource.get("url", "")
        resource_format = (resource.get("format") or "").upper()

        # Method 1: Try CKAN DataStore API
        if resource_id:
            datastore_records = await fetch_from_datastore(
                self.BASE_URL, resource_id, session, limit
            )
            if datastore_records:
                for row in datastore_records:
                    records.append({
                        "source": self.SOURCE_NAME,
                        "dataset_id": dataset_id,
                        "dataset_title": dataset_title,
                        "resource_id": resource_id,
                        **row
                    })
                return records

        # Method 2: Try CSV preview
        if resource_format == "CSV" and resource_url:
            csv_records = await fetch_csv_preview(resource_url, session, limit)
            if csv_records:
                for row in csv_records:
                    records.append({
                        "source": self.SOURCE_NAME,
                        "dataset_id": dataset_id,
                        "dataset_title": dataset_title,
                        "resource_id": resource_id,
                        **row
                    })

        return records

    async def _estimate_total_rows(
        self,
        resources: List[Dict],
        session: aiohttp.ClientSession
    ) -> int:
        """Estimate total rows across all resources."""
        total_rows = 0
        for resource in resources:
            resource_id = resource.get("id")
            resource_format = (resource.get("format") or "").upper()
            resource_url = resource.get("url", "")

            # Method 1: Try DataStore
            if resource_id:
                datastore_info = await get_datastore_info(
                    self.BASE_URL, resource_id, session
                )
                if datastore_info and datastore_info.get("total", 0) > 0:
                    total_rows += datastore_info["total"]
                    continue

            # Method 2: File size estimate
            if resource_format in ("CSV", "XLSX", "XLS", "JSON"):
                filesize = resource.get("size") or resource.get("filesize") or 0
                if filesize > 0:
                    total_rows += estimate_records_from_filesize(filesize, resource_format.lower())
                    continue

            # Method 3: URL HEAD request
            if resource_url and resource_format in ("CSV", "JSON", ""):
                url_rows = await estimate_rows_from_url(resource_url, session)
                if url_rows > 0:
                    total_rows += url_rows

        return total_rows

    def _extract_date(self, ds: Dict) -> Optional[str]:
        """Extract last updated date from dataset metadata."""
        date_field = ds.get("metadata_modified") or ds.get("last_modified") or ""
        return date_field[:10] if date_field else None

    async def list_datasets(self) -> List[DatasetInfo]:
        """
        List available datasets by querying CKAN API.
        Common implementation for all CKAN-based connectors.
        """
        datasets = []
        session = await self._get_session()
        endpoints = self._get_api_endpoints()

        for search_id, search_info in self.DATASET_SEARCHES.items():
            try:
                params = {"q": search_info["query"], "rows": 1}

                async with session.get(endpoints["search"], params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        result = self._get_api_result_path(data)
                        items = result.get("results", []) if isinstance(result, dict) else []

                        if items:
                            ds = items[0]
                            resources = ds.get("resources", [])
                            total_rows = await self._estimate_total_rows(resources, session)

                            datasets.append(DatasetInfo(
                                id=ds.get("id", f"{self.connector_id}_{search_id}"),
                                name=ds.get("title", search_info["query"]),
                                description=(ds.get("notes", "") or ds.get("description", "") or "")[:200],
                                asset_type=search_info["asset_type"],
                                estimated_records=total_rows if total_rows > 0 else len(resources),
                                last_updated=self._extract_date(ds),
                            ))
            except Exception as e:
                logger.warning(f"Error fetching {search_id}: {e}")
                continue

        return datasets

    async def import_dataset(
        self,
        dataset_id: str,
        limit: Optional[int] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Import data from a CKAN dataset.
        Common implementation with hooks for customization.
        """
        start_time = datetime.now()

        yield self._progress("starting", 0, f"Connecting to {self.SOURCE_NAME}...")

        session = await self._get_session()
        records = []
        endpoints = self._get_api_endpoints()

        try:
            # Fetch metadata
            yield self._progress("processing", 10, "Fetching dataset metadata...")

            params = {"id": dataset_id}
            async with session.get(endpoints["show"], params=params) as response:
                if response.status != 200:
                    yield self._error(15, f"Dataset not found: HTTP {response.status}")
                    return

                data = await response.json()
                ds = self._get_api_result_path(data)
                dataset_title = ds.get("title", "Unknown")

            yield self._progress("processing", 20, f"Found: {dataset_title}...")

            resources = ds.get("resources", [])
            tabular_resources = self._filter_tabular_resources(resources)

            yield self._progress("processing", 30, f"Found {len(tabular_resources)} resources...")

            # Fetch data from resources
            for i, resource in enumerate(tabular_resources):
                if limit is not None and len(records) >= limit:
                    break

                remaining = (limit - len(records)) if limit is not None else None
                progress = 30 + int(50 * i / max(len(tabular_resources), 1))

                yield self._progress("processing", progress, f"Fetching resource {i+1}/{len(tabular_resources)}...")

                resource_records = await self._fetch_resource_data(
                    resource, dataset_id, dataset_title, session, remaining
                )
                records.extend(resource_records)

            # Handle empty results
            if not records:
                duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                yield self._completed(
                    [],
                    duration_ms,
                    f"Dataset '{dataset_title}' has {len(resources)} resources but data is not accessible.",
                    resources_found=len(resources)
                )
                return

        except aiohttp.ClientError as e:
            yield self._error(50, f"API connection error: {str(e)[:100]}")
            return
        except Exception as e:
            logger.exception(f"{self.SOURCE_NAME} import error for {dataset_id}")
            yield self._error(50, f"Import error: {str(e)[:100]}")
            return

        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        yield self._completed(records, duration_ms)
