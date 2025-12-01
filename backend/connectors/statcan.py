"""
Statistics Canada (StatCan) Data Connector
==========================================
Connects to Statistics Canada Web Data Service REST API.

API Documentation: https://www.statcan.gc.ca/en/developers/wds

Infrastructure-related datasets:
- Table 34-10-0013: Core public infrastructure
- Table 36-10-0608: Non-residential construction
- Table 17-10-0009: Population estimates
"""

import aiohttp
import asyncio
import logging
from typing import List, Dict, Any, Optional, AsyncIterator
from datetime import datetime

from .base import BaseConnector, DatasetInfo

logger = logging.getLogger(__name__)


class StatCanConnector(BaseConnector):
    """
    Connector for Statistics Canada Web Data Service.

    Uses POST-based API with coordinate system for data queries.
    Supports ZIP extraction for large CSV downloads.
    Base URL: https://www150.statcan.gc.ca/t1/wds/rest

    Endpoints used:
    - /getAllCubesListLite: List all available tables
    - /getDataFromCubePidCoordAndLatestNPeriods: Get data
    """

    BASE_URL = "https://www150.statcan.gc.ca/t1/wds/rest"

    # Infrastructure-related Product IDs
    INFRASTRUCTURE_TABLES = {
        "34100013": {
            "name": "Core public infrastructure",
            "asset_type": "infrastructure",
            "description": "Core public infrastructure by function, asset and province/territory"
        },
        "34100270": {
            "name": "Infrastructure spending",
            "asset_type": "budget",
            "description": "Government spending on infrastructure"
        },
        "36100608": {
            "name": "Construction statistics",
            "asset_type": "construction",
            "description": "Non-residential building construction"
        },
        "17100009": {
            "name": "Population estimates",
            "asset_type": "demographics",
            "description": "Population estimates by province and territory"
        },
    }

    @property
    def connector_id(self) -> str:
        return "statcan"

    @property
    def country(self) -> str:
        return "CA"

    @property
    def name(self) -> str:
        return "Statistics Canada"

    @property
    def description(self) -> str:
        return "Statistics Canada Web Data Service - Infrastructure and demographic datasets"

    async def list_datasets(self) -> List[DatasetInfo]:
        """
        List available datasets by querying StatCan API for metadata.
        """
        datasets = []
        session = await self._get_session()

        for table_id, info in self.INFRASTRUCTURE_TABLES.items():
            try:
                # Query StatCan API for cube metadata
                url = f"{self.BASE_URL}/getCubeMetadata"
                payload = [{"productId": int(table_id)}]

                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and len(data) > 0:
                            obj = data[0].get("object", {})
                            datasets.append(DatasetInfo(
                                id=f"statcan_{table_id}",
                                name=obj.get("cubeTitleEn", info["name"]),
                                description=info["description"],
                                asset_type=info["asset_type"],
                                estimated_records=obj.get("nbDatapointsCube", 0),
                                last_updated=obj.get("cubeEndDate", ""),
                            ))
                        else:
                            # Fallback if API returns empty
                            datasets.append(DatasetInfo(
                                id=f"statcan_{table_id}",
                                name=info["name"],
                                description=info["description"],
                                asset_type=info["asset_type"],
                                estimated_records=0,
                                last_updated=None,
                            ))
            except Exception as e:
                logger.warning(f"Error fetching StatCan table {table_id}: {e}")
                continue

        return datasets

    async def get_table_metadata(self, product_id: str) -> Dict[str, Any]:
        """
        Get metadata for a specific table.

        Args:
            product_id: StatCan product ID (e.g., "34100013")

        Returns:
            Table metadata including dimensions and coordinates
        """
        session = await self._get_session()

        try:
            url = f"{self.BASE_URL}/getCubeMetadata"
            payload = [{"productId": int(product_id)}]

            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    if data and len(data) > 0:
                        return data[0].get("object", {})
                return {}
        except Exception as e:
            logger.warning(f"StatCan metadata error: {e}")
            return {}

    async def _build_coordinate(self, metadata: Dict[str, Any]) -> str:
        """
        Build a valid coordinate string from cube metadata.

        The coordinate format is dimension values separated by dots.
        We use "1" for first member of each dimension, "0" for all members.
        """
        dimensions = metadata.get("dimension", [])
        if not dimensions:
            return "1.1.0.0.0.0.0.0.0.0"  # Fallback default

        coords = []
        for dim in dimensions:
            members = dim.get("member", [])
            if members and len(members) > 0:
                # Use first available member
                coords.append("1")
            else:
                # Use "0" for all/any
                coords.append("0")

        return ".".join(coords)

    async def _fetch_csv_data(
        self,
        product_id: str,
        session: aiohttp.ClientSession,
        limit: Optional[int] = None  # None means no limit
    ) -> List[Dict[str, Any]]:
        """
        Fetch data by downloading and parsing the CSV file.

        This is more reliable than the coordinate-based API as it always returns data.
        """
        import csv
        import io
        import zipfile

        records = []

        try:
            # Get CSV download URL
            url = f"{self.BASE_URL}/getFullTableDownloadCSV/{product_id}/en"
            async with session.get(url) as response:
                if response.status != 200:
                    return records
                data = await response.json()
                if data.get("status") != "SUCCESS":
                    return records
                csv_url = data.get("object")
                if not csv_url:
                    return records

            # Download and parse the CSV (it's a zip file)
            logger.debug(f"Downloading CSV from {csv_url}")
            async with session.get(csv_url, timeout=aiohttp.ClientTimeout(total=60)) as response:
                if response.status != 200:
                    return records

                zip_content = await response.read()

            # Extract CSV from zip
            with zipfile.ZipFile(io.BytesIO(zip_content)) as zf:
                # Find the main data file (not metadata)
                csv_files = [n for n in zf.namelist() if n.endswith('.csv') and 'MetaData' not in n]
                if not csv_files:
                    return records

                csv_data = zf.read(csv_files[0]).decode('utf-8-sig')

            # Parse CSV
            reader = csv.DictReader(io.StringIO(csv_data))
            for i, row in enumerate(reader):
                if limit is not None and i >= limit:
                    break
                # Clean and normalize the row
                clean_row = {k.strip(): v.strip() if isinstance(v, str) else v
                            for k, v in row.items() if k}
                records.append(clean_row)

        except Exception as e:
            logger.warning(f"CSV fetch error for {product_id}: {e}")

        return records

    async def _fetch_multiple_vectors(
        self,
        product_id: str,
        metadata: Dict[str, Any],
        limit: Optional[int],
        session: aiohttp.ClientSession
    ) -> List[Dict[str, Any]]:
        """
        Fetch data using multiple coordinate combinations to get more records.

        Falls back to CSV download if coordinate-based API doesn't return data.
        """
        records = []
        dimensions = metadata.get("dimension", [])

        if not dimensions:
            # Try CSV download as fallback
            return await self._fetch_csv_data(product_id, session, limit)

        # Get dimension member info for labeling
        dim_labels = {}
        for dim in dimensions:
            dim_id = dim.get("dimensionPositionId", 0)
            members = dim.get("member", [])
            dim_labels[dim_id] = {
                "name": dim.get("dimensionNameEn", f"Dim{dim_id}"),
                "members": {m.get("memberId", 0): m.get("memberNameEn", "") for m in members}
            }

        # Try fetching with first member of first dimension, varying others
        first_dim_members = dimensions[0].get("member", []) if dimensions else []
        # When no limit, use a large number for periods_per_member
        effective_limit = limit if limit is not None else 100000
        periods_per_member = max(1, effective_limit // max(len(first_dim_members), 1))

        for member in first_dim_members[:10]:  # Limit to 10 variations
            member_id = member.get("memberId", 1)
            coords = [str(member_id)] + ["1"] * (len(dimensions) - 1)
            coordinate = ".".join(coords)

            url = f"{self.BASE_URL}/getDataFromCubePidCoordAndLatestNPeriods"
            payload = [{
                "productId": int(product_id),
                "coordinate": coordinate,
                "latestN": periods_per_member
            }]

            try:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Check if response is a list with data
                        if isinstance(data, list) and len(data) > 0:
                            obj = data[0].get("object", {})
                            vector_data = obj.get("vectorDataPoint", [])

                            for point in vector_data:
                                records.append({
                                    "value": point.get("value"),
                                    "ref_period": point.get("refPer"),
                                    "ref_period_2": point.get("refPer2"),
                                    "coordinate": coordinate,
                                    "dimension_label": member.get("memberNameEn", ""),
                                })

                                if limit is not None and len(records) >= limit:
                                    return records
            except Exception as e:
                logger.debug(f"Vector fetch error for coord {coordinate}: {e}")
                continue

        # If coordinate-based API didn't return data, try CSV download
        if not records:
            logger.info(f"Coordinate API returned no data, trying CSV download for {product_id}")
            records = await self._fetch_csv_data(product_id, session, limit)

        return records

    async def import_dataset(
        self,
        dataset_id: str,
        limit: Optional[int] = None  # None means no limit
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Import data from a StatCan table.

        Yields progress updates and final result.

        Args:
            dataset_id: Dataset ID (e.g., "statcan_34100013")
            limit: Maximum records to import

        Yields:
            Progress updates: {"phase": "processing", "progress": 0-100, "message": "..."}
            Final result: {"phase": "completed", "records": [...], "count": N}
        """
        start_time = datetime.now()

        # Extract product ID from dataset_id
        if dataset_id.startswith("statcan_"):
            product_id = dataset_id.replace("statcan_", "")
        else:
            product_id = dataset_id

        yield {
            "phase": "starting",
            "progress": 0,
            "message": f"Connecting to Statistics Canada for table {product_id}..."
        }

        table_info = self.INFRASTRUCTURE_TABLES.get(product_id, {})
        if not table_info:
            yield {
                "phase": "error",
                "progress": 0,
                "message": f"Unknown table ID: {product_id}"
            }
            return

        session = await self._get_session()
        records = []

        try:
            # Step 1: Get cube metadata to understand dimension structure
            yield {
                "phase": "processing",
                "progress": 10,
                "message": "Fetching table metadata..."
            }

            metadata = await self.get_table_metadata(product_id)
            if not metadata:
                yield {
                    "phase": "error",
                    "progress": 15,
                    "message": f"Could not fetch metadata for table {product_id}"
                }
                return

            table_name = metadata.get("cubeTitleEn", table_info['name'])

            yield {
                "phase": "processing",
                "progress": 20,
                "message": f"Fetching {table_name}..."
            }

            # Step 2: Build valid coordinate from metadata
            coordinate = await self._build_coordinate(metadata)

            yield {
                "phase": "processing",
                "progress": 30,
                "message": "Querying StatCan data vectors..."
            }

            # Step 3: Fetch data using multiple coordinate combinations
            raw_records = await self._fetch_multiple_vectors(
                product_id, metadata, limit, session
            )

            yield {
                "phase": "processing",
                "progress": 60,
                "message": f"Processing {len(raw_records)} data points..."
            }

            # Step 4: Format records for output
            for i, raw in enumerate(raw_records[:limit]):
                # Check if this is CSV data (has REF_DATE, GEO, VALUE columns)
                # or vector API data (has value, ref_period, coordinate)
                if "REF_DATE" in raw or "VALUE" in raw:
                    # CSV format - use actual column names
                    records.append({
                        "id": f"{product_id}_{i}",
                        "name": f"{table_name}",
                        "type": table_info["asset_type"],
                        "region": raw.get("GEO", "Canada"),
                        "value": raw.get("VALUE"),
                        "ref_date": raw.get("REF_DATE"),
                        "unit": raw.get("UOM"),
                        "scalar_factor": raw.get("SCALAR_FACTOR"),
                        "source": "Statistics Canada",
                        "table_id": product_id,
                        # Include additional fields
                        **{k: v for k, v in raw.items()
                           if k not in ("REF_DATE", "GEO", "VALUE", "UOM", "SCALAR_FACTOR")}
                    })
                else:
                    # Vector API format
                    records.append({
                        "id": f"{product_id}_{i}",
                        "name": f"{table_name}",
                        "type": table_info["asset_type"],
                        "region": raw.get("dimension_label", "Canada"),
                        "value": raw.get("value"),
                        "ref_period": raw.get("ref_period"),
                        "source": "Statistics Canada",
                        "table_id": product_id,
                        "coordinate": raw.get("coordinate"),
                    })

                if i > 0 and i % 100 == 0:
                    yield {
                        "phase": "processing",
                        "progress": 60 + int(30 * i / len(raw_records)),
                        "message": f"Processed {i} records..."
                    }

        except aiohttp.ClientError as e:
            yield {
                "phase": "error",
                "progress": 50,
                "message": f"Connection error: {str(e)}"
            }
            return
        except Exception as e:
            logger.exception(f"StatCan import error for {product_id}")
            yield {
                "phase": "error",
                "progress": 50,
                "message": f"Import error: {str(e)}"
            }
            return

        # No dummy data fallback - report actual results
        if not records:
            yield {
                "phase": "completed",
                "progress": 100,
                "message": f"No data found for table {product_id}. The table may have restricted access or different coordinate requirements.",
                "records": [],
                "count": 0,
                "duration_ms": int((datetime.now() - start_time).total_seconds() * 1000),
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
            "datasets": [table_id for table_id in self.INFRASTRUCTURE_TABLES.keys()],
        }
