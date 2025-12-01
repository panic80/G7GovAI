"""
Japan e-Gov / e-Stat Data Connector
===================================
Connects to Japanese government open data sources.

API Documentation:
- e-Gov Data Portal: https://data.e-gov.go.jp/info/en
- e-Stat API: https://www.e-stat.go.jp/api/

Infrastructure-related datasets:
- Statistical data from Japanese government
- Infrastructure and demographic data
- Regional statistics

API Key Registration: https://www.e-stat.go.jp/api/
Set ESTAT_API_KEY environment variable for full access.
"""

import aiohttp
import logging
import os
from typing import List, Dict, Any, Optional, AsyncIterator
from datetime import datetime

from .base import (
    BaseConnector,
    fetch_csv_preview,
    estimate_records_from_filesize,
    DatasetInfo,
)

logger = logging.getLogger(__name__)


class EGovConnector(BaseConnector):
    """
    Connector for Japanese government data via e-Gov and e-Stat.

    Uses dual API implementation (e-Stat and e-Gov) with fallback.
    Requires ESTAT_API_KEY environment variable for full access.

    e-Gov Portal: https://data.e-gov.go.jp/
    e-Stat API: https://api.e-stat.go.jp/

    For e-Stat API access, set ESTAT_API_KEY environment variable.
    Register at: https://www.e-stat.go.jp/api/
    """

    BASE_URL = "https://data.e-gov.go.jp/data/api/1"
    ESTAT_BASE_URL = "https://api.e-stat.go.jp/rest/3.0/app/json"

    # Search terms to find datasets on e-Gov
    DATASET_SEARCHES = {
        "jinko": {
            "query": "人口",
            "asset_type": "demographics",
        },
        "shakai-kiban": {
            "query": "社会基盤 インフラ",
            "asset_type": "infrastructure",
        },
        "kotsu": {
            "query": "交通",
            "asset_type": "transport",
        },
        "kensetsu": {
            "query": "建設",
            "asset_type": "construction",
        },
        "chiiki": {
            "query": "地域",
            "asset_type": "regional",
        },
    }

    # Japanese prefectures for sample data
    JAPANESE_REGIONS = [
        "Tokyo", "Osaka", "Kanagawa", "Aichi", "Saitama",
        "Chiba", "Hyogo", "Hokkaido", "Fukuoka", "Shizuoka",
        "Ibaraki", "Hiroshima", "Kyoto", "Miyagi", "Niigata",
        "Nagano", "Gifu", "Gunma", "Tochigi", "Okayama"
    ]

    def __init__(self, timeout: int = 30):
        super().__init__(timeout)
        self.estat_api_key = os.environ.get("ESTAT_API_KEY", "")

    @property
    def connector_id(self) -> str:
        return "egov"

    @property
    def country(self) -> str:
        return "JP"

    @property
    def name(self) -> str:
        return "e-Gov / e-Stat"

    @property
    def description(self) -> str:
        return "Japanese Government e-Gov Data Portal - Infrastructure and statistical datasets"

    async def _fetch_estat_stats_list(
        self,
        search_word: str,
        session: aiohttp.ClientSession
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch statistics list from e-Stat API.
        """
        if not self.estat_api_key:
            return None

        try:
            url = f"{self.ESTAT_BASE_URL}/getStatsList"
            params = {
                "appId": self.estat_api_key,
                "searchWord": search_word,
                "limit": 1,
                "lang": "E"  # English
            }

            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    data = await response.json()
                    result = data.get("GET_STATS_LIST", {}).get("DATALIST_INF", {})
                    tables = result.get("TABLE_INF", [])
                    if tables and isinstance(tables, list):
                        return tables[0]
                    elif tables and isinstance(tables, dict):
                        return tables
        except Exception as e:
            logger.debug(f"e-Stat API error: {e}")
        return None

    async def _fetch_estat_data(
        self,
        stats_data_id: str,
        session: aiohttp.ClientSession,
        limit: Optional[int] = None  # None means no limit
    ) -> List[Dict[str, Any]]:
        """
        Fetch actual statistical data from e-Stat API.
        """
        records = []
        if not self.estat_api_key:
            return records

        try:
            url = f"{self.ESTAT_BASE_URL}/getStatsData"
            params = {
                "appId": self.estat_api_key,
                "statsDataId": stats_data_id,
                "startPosition": 1,
                "lang": "E"
            }
            if limit is not None:
                params["limit"] = limit

            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=60)) as response:
                if response.status == 200:
                    data = await response.json()
                    result = data.get("GET_STATS_DATA", {}).get("STATISTICAL_DATA", {})
                    data_inf = result.get("DATA_INF", {})
                    values = data_inf.get("VALUE", [])

                    # Get class info for labeling
                    class_inf = result.get("CLASS_INF", {}).get("CLASS_OBJ", [])
                    class_labels = {}
                    for cls in class_inf:
                        cls_id = cls.get("@id", "")
                        cls_items = cls.get("CLASS", [])
                        if isinstance(cls_items, dict):
                            cls_items = [cls_items]
                        class_labels[cls_id] = {
                            item.get("@code", ""): item.get("@name", "")
                            for item in cls_items
                        }

                    for val in values[:limit]:
                        record = {
                            "value": val.get("$", ""),
                            "unit": val.get("@unit", ""),
                        }
                        # Add dimension labels
                        for key, value in val.items():
                            if key.startswith("@") and key not in ("@unit",):
                                dim_name = key[1:]  # Remove @
                                dim_labels = class_labels.get(dim_name, {})
                                record[dim_name] = dim_labels.get(value, value)
                        records.append(record)
        except Exception as e:
            logger.debug(f"e-Stat data fetch error: {e}")
        return records

    async def list_datasets(self) -> List[DatasetInfo]:
        """
        List available datasets by querying e-Gov and e-Stat APIs.
        Uses e-Stat API if API key is configured for better data access.
        """
        datasets = []
        session = await self._get_session()

        for search_id, search_info in self.DATASET_SEARCHES.items():
            try:
                # Try e-Stat API first (if key is configured)
                if self.estat_api_key:
                    estat_result = await self._fetch_estat_stats_list(search_info["query"], session)
                    if estat_result:
                        # Parse e-Stat response
                        total_number = estat_result.get("OVERALL_TOTAL_NUMBER", 0)
                        if isinstance(total_number, str):
                            total_number = int(total_number) if total_number.isdigit() else 0

                        datasets.append(DatasetInfo(
                            id=estat_result.get("@id", f"estat_{search_id}"),
                            name=estat_result.get("TITLE", {}).get("$", search_info["query"]),
                            description=(estat_result.get("TITLE", {}).get("@no", "") or "")[:200],
                            asset_type=search_info["asset_type"],
                            estimated_records=total_number,
                            last_updated=estat_result.get("UPDATED_DATE", "")[:10] if estat_result.get("UPDATED_DATE") else None,
                        ))
                        continue

                # Fallback to e-Gov portal
                url = f"{self.BASE_URL}/datasets"
                params = {"keyword": search_info["query"], "limit": 1}

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        items = data.get("result", []) if isinstance(data.get("result"), list) else []

                        if items:
                            ds = items[0]
                            resources = ds.get("resources", [])

                            # Estimate records from file sizes
                            total_rows = 0
                            for resource in resources:
                                resource_format = (resource.get("format") or "").upper()
                                filesize = resource.get("size") or 0
                                if resource_format in ("CSV", "XLSX", "XLS") and filesize > 0:
                                    total_rows += estimate_records_from_filesize(
                                        filesize, resource_format.lower()
                                    )

                            datasets.append(DatasetInfo(
                                id=ds.get("id", f"egov_{search_id}"),
                                name=ds.get("title", search_info["query"]),
                                description=(ds.get("description", "") or "")[:200],
                                asset_type=search_info["asset_type"],
                                estimated_records=total_rows if total_rows > 0 else ds.get("resource_count", 0),
                                last_updated=ds.get("metadata_modified", "")[:10] if ds.get("metadata_modified") else None,
                            ))
            except Exception as e:
                logger.warning(f"Error fetching {search_id}: {e}")
                continue

        return datasets

    async def import_dataset(
        self,
        dataset_id: str,
        limit: Optional[int] = None  # None means no limit
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Import actual data rows from a Japanese government dataset.

        Uses e-Stat API when available (requires ESTAT_API_KEY), falls back to CSV preview.

        Args:
            dataset_id: e-Stat stats data ID or e-Gov dataset ID
            limit: Maximum records to import
        """
        start_time = datetime.now()

        yield {
            "phase": "starting",
            "progress": 0,
            "message": f"Connecting to Japanese government data for {dataset_id[:8]}..."
        }

        session = await self._get_session()
        records = []

        try:
            # Check if this is an e-Stat ID (numeric) and we have API key
            is_estat_id = dataset_id.isdigit() or dataset_id.startswith("estat_")
            estat_id = dataset_id.replace("estat_", "") if dataset_id.startswith("estat_") else dataset_id

            if is_estat_id and self.estat_api_key:
                yield {
                    "phase": "processing",
                    "progress": 20,
                    "message": "Fetching data from e-Stat API..."
                }

                # Fetch from e-Stat API
                estat_records = await self._fetch_estat_data(estat_id, session, limit)

                if estat_records:
                    yield {
                        "phase": "processing",
                        "progress": 60,
                        "message": f"Processing {len(estat_records)} statistical records..."
                    }

                    for i, row in enumerate(estat_records):
                        records.append({
                            "source": "e-Stat",
                            "dataset_id": dataset_id,
                            **row
                        })

                        if i > 0 and i % 100 == 0:
                            yield {
                                "phase": "processing",
                                "progress": 60 + int(30 * i / len(estat_records)),
                                "message": f"Processed {i} records..."
                            }

            # Fallback to e-Gov portal
            if not records:
                yield {
                    "phase": "processing",
                    "progress": 20,
                    "message": "Fetching from e-Gov Data Portal..."
                }

                url = f"{self.BASE_URL}/datasets/{dataset_id}"

                async with session.get(url) as response:
                    if response.status != 200:
                        # Try without e-Gov prefix
                        if not is_estat_id:
                            yield {
                                "phase": "error",
                                "progress": 25,
                                "message": f"Dataset not found: HTTP {response.status}"
                            }
                            return
                    else:
                        ds = await response.json()
                        dataset_title = ds.get("title", "Unknown")

                        yield {
                            "phase": "processing",
                            "progress": 40,
                            "message": f"Found: {dataset_title}..."
                        }

                        resources = ds.get("resources", [])

                        # Filter to tabular resources
                        tabular_resources = [
                            r for r in resources
                            if (r.get("format") or "").upper() in ("CSV", "JSON", "XLSX", "XLS", "")
                        ]

                        yield {
                            "phase": "processing",
                            "progress": 50,
                            "message": f"Found {len(tabular_resources)} tabular resources..."
                        }

                        for i, resource in enumerate(tabular_resources):
                            if limit is not None and len(records) >= limit:
                                break

                            resource_url = resource.get("url", "")
                            resource_format = (resource.get("format") or "").upper()
                            remaining = (limit - len(records)) if limit is not None else None

                            yield {
                                "phase": "processing",
                                "progress": 50 + int(40 * i / max(len(tabular_resources), 1)),
                                "message": f"Fetching data from resource {i+1}..."
                            }

                            # Try CSV preview
                            if resource_format == "CSV" and resource_url:
                                csv_records = await fetch_csv_preview(resource_url, session, remaining, encoding='utf-8')
                                if csv_records:
                                    for row in csv_records:
                                        records.append({
                                            "source": "e-Gov Data Portal",
                                            "dataset_id": dataset_id,
                                            "dataset_title": dataset_title,
                                            **row
                                        })

            if not records:
                message = "No data accessible."
                if not self.estat_api_key and is_estat_id:
                    message = "Set ESTAT_API_KEY environment variable for e-Stat data access."

                yield {
                    "phase": "completed",
                    "progress": 100,
                    "message": message,
                    "records": [],
                    "count": 0,
                    "duration_ms": int((datetime.now() - start_time).total_seconds() * 1000),
                }
                return

        except aiohttp.ClientError as e:
            yield {
                "phase": "error",
                "progress": 50,
                "message": f"API connection error: {str(e)[:100]}"
            }
            return
        except Exception as e:
            logger.exception(f"Japan import error for {dataset_id}")
            yield {
                "phase": "error",
                "progress": 50,
                "message": f"Import error: {str(e)[:100]}"
            }
            return

        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        yield {
            "phase": "completed",
            "progress": 100,
            "message": f"Import complete: {len(records)} records in {duration_ms}ms",
            "records": records,
            "count": len(records),
            "duration_ms": duration_ms,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize connector info for API response."""
        return {
            "id": self.connector_id,
            "name": self.name,
            "country": self.country,
            "description": self.description,
            "datasets": list(self.DATASET_SEARCHES.keys()),
        }
