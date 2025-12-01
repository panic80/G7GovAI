"""
UK Office for National Statistics (ONS) Data Connector
======================================================
Connects to ONS API (beta) for UK government statistics.

API Documentation: https://api.beta.ons.gov.uk/v1

Infrastructure-related datasets:
- Construction output
- Public sector infrastructure
- Regional statistics
"""

import aiohttp
import asyncio
import logging
from typing import List, Dict, Any, Optional, AsyncIterator
from datetime import datetime

from .base import BaseConnector, DatasetInfo

logger = logging.getLogger(__name__)


class ONSConnector(BaseConnector):
    """
    Connector for UK Office for National Statistics API.

    The ONS API provides access to UK government statistics.
    Uses a unique hierarchical API structure (editions/versions/observations).
    Base URL: https://api.beta.ons.gov.uk/v1

    Note: The ONS API is in beta and may have rate limits.
    """

    BASE_URL = "https://api.beta.ons.gov.uk/v1"

    # Known ONS dataset IDs (these are actual IDs in the ONS system)
    KNOWN_DATASETS = [
        "cpih01",
        "gdp",
        "construction-output-in-great-britain",
        "regional-gross-value-added-balanced-by-industry",
        "mid-year-pop-est",
    ]

    # UK Regions for sample data
    UK_REGIONS = [
        "England", "Scotland", "Wales", "Northern Ireland",
        "North East", "North West", "Yorkshire", "East Midlands",
        "West Midlands", "East of England", "London", "South East", "South West"
    ]

    @property
    def connector_id(self) -> str:
        return "ons"

    @property
    def country(self) -> str:
        return "UK"

    @property
    def name(self) -> str:
        return "Office for National Statistics"

    @property
    def description(self) -> str:
        return "UK Office for National Statistics - Construction, regional, and demographic data"

    async def list_datasets(self) -> List[DatasetInfo]:
        """
        List available datasets by directly fetching known ONS dataset IDs.
        """
        datasets = []
        session = await self._get_session()

        for dataset_id in self.KNOWN_DATASETS:
            try:
                url = f"{self.BASE_URL}/datasets/{dataset_id}"

                async with session.get(url) as response:
                    if response.status == 200:
                        ds = await response.json()
                        datasets.append(DatasetInfo(
                            id=ds.get("id", dataset_id),
                            name=ds.get("title", dataset_id),
                            description=(ds.get("description", "") or "")[:200],
                            asset_type="statistical",
                            estimated_records=ds.get("total_observations", 0),
                            last_updated=ds.get("next_release", "")[:10] if ds.get("next_release") else None,
                        ))
            except Exception as e:
                logger.warning(f"Error fetching ONS dataset {dataset_id}: {e}")
                continue

        return datasets

    async def get_dataset_metadata(self, dataset_id: str) -> Dict[str, Any]:
        """
        Get metadata for a specific dataset.

        Args:
            dataset_id: ONS dataset ID

        Returns:
            Dataset metadata
        """
        session = await self._get_session()

        try:
            url = f"{self.BASE_URL}/datasets/{dataset_id}"

            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                return {}
        except Exception as e:
            logger.warning(f"ONS metadata error: {e}")
            return {}

    async def _get_latest_version_url(self, dataset_id: str, session: aiohttp.ClientSession) -> Optional[str]:
        """
        Get the URL for the latest version of a dataset.
        """
        try:
            # Get editions
            editions_url = f"{self.BASE_URL}/datasets/{dataset_id}/editions"
            async with session.get(editions_url) as response:
                if response.status != 200:
                    return None
                editions_data = await response.json()
                editions = editions_data.get("items", [])
                if not editions:
                    return None

                # Get latest edition (usually "time-series" for time series data)
                latest_edition = editions[0].get("edition", "time-series")

                # Get versions for this edition
                versions_url = f"{self.BASE_URL}/datasets/{dataset_id}/editions/{latest_edition}/versions"
                async with session.get(versions_url) as versions_response:
                    if versions_response.status != 200:
                        return None
                    versions_data = await versions_response.json()
                    versions = versions_data.get("items", [])
                    if not versions:
                        return None

                    # Return the URL of the latest version
                    latest_version = versions[0]
                    return latest_version.get("links", {}).get("self", {}).get("href")
        except Exception as e:
            logger.debug(f"Error getting latest version URL: {e}")
            return None

    async def _fetch_observations(
        self,
        version_url: str,
        session: aiohttp.ClientSession,
        limit: Optional[int] = None  # None means no limit
    ) -> List[Dict[str, Any]]:
        """
        Fetch actual observation data from ONS API.
        """
        records = []

        try:
            # Get dimensions for this version
            dimensions_url = f"{version_url}/dimensions"
            async with session.get(dimensions_url) as response:
                if response.status != 200:
                    return records
                dims_data = await response.json()
                dimensions = dims_data.get("items", [])

            # Build dimension filters - use wildcards (*) for flexible querying
            # Common dimensions: time, geography, aggregate
            dim_params = []
            geography_code = None

            for dim in dimensions:
                dim_name = dim.get("name", "")
                if dim_name.lower() == "geography":
                    # Use K02000001 (UK) or wildcard
                    geography_code = "K02000001"
                    dim_params.append(f"geography={geography_code}")
                elif dim_name.lower() == "time":
                    dim_params.append("time=*")
                else:
                    # Use wildcard for other dimensions
                    dim_params.append(f"{dim_name}=*")

            # Fetch observations
            observations_url = f"{version_url}/observations"
            if dim_params:
                observations_url += "?" + "&".join(dim_params[:3])  # Limit params to avoid complex queries
                if limit is not None:
                    observations_url += f"&limit={limit}"

            async with session.get(observations_url, timeout=aiohttp.ClientTimeout(total=60)) as response:
                if response.status == 200:
                    obs_data = await response.json()
                    observations = obs_data.get("observations", [])

                    for obs in observations[:limit]:
                        record = {
                            "observation": obs.get("observation"),
                        }
                        # Add dimension values
                        for dim in obs.get("dimensions", []):
                            dim_name = dim.get("dimension", "")
                            record[dim_name] = dim.get("label", dim.get("option", ""))
                        records.append(record)
                else:
                    # Try alternative: direct download URL
                    logger.debug(f"Observations endpoint returned {response.status}, trying downloads")

        except Exception as e:
            logger.debug(f"Error fetching observations: {e}")

        return records

    async def import_dataset(
        self,
        dataset_id: str,
        limit: Optional[int] = None  # None means no limit
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Import actual observation data from an ONS dataset.

        Args:
            dataset_id: Real ONS dataset ID
            limit: Maximum records to import
        """
        start_time = datetime.now()

        yield {
            "phase": "starting",
            "progress": 0,
            "message": f"Connecting to ONS API for {dataset_id}..."
        }

        session = await self._get_session()
        records = []

        try:
            # Fetch dataset metadata first
            url = f"{self.BASE_URL}/datasets/{dataset_id}"

            yield {
                "phase": "processing",
                "progress": 10,
                "message": "Fetching dataset metadata..."
            }

            async with session.get(url) as response:
                if response.status != 200:
                    yield {
                        "phase": "error",
                        "progress": 15,
                        "message": f"Dataset not found: HTTP {response.status}"
                    }
                    return

                ds = await response.json()
                dataset_title = ds.get("title", dataset_id)
                total_observations = ds.get("total_observations", 0)

            yield {
                "phase": "processing",
                "progress": 20,
                "message": f"Found: {dataset_title} (~{total_observations:,} observations)..."
            }

            # Get latest version URL
            yield {
                "phase": "processing",
                "progress": 30,
                "message": "Finding latest data version..."
            }

            version_url = await self._get_latest_version_url(dataset_id, session)

            if version_url:
                yield {
                    "phase": "processing",
                    "progress": 50,
                    "message": "Fetching observation data..."
                }

                # Fetch actual observations
                raw_observations = await self._fetch_observations(version_url, session, limit)

                yield {
                    "phase": "processing",
                    "progress": 70,
                    "message": f"Processing {len(raw_observations)} observations..."
                }

                for i, obs in enumerate(raw_observations):
                    records.append({
                        "id": f"{dataset_id}_{i}",
                        "name": dataset_title,
                        "type": "statistical",
                        "value": obs.get("observation"),
                        "time": obs.get("time", obs.get("Time", "")),
                        "geography": obs.get("geography", obs.get("Geography", "United Kingdom")),
                        "source": "Office for National Statistics",
                        "dataset_id": dataset_id,
                        **{k: v for k, v in obs.items() if k not in ["observation", "time", "Time", "geography", "Geography"]}
                    })

                    if i > 0 and i % 100 == 0:
                        yield {
                            "phase": "processing",
                            "progress": 70 + int(25 * i / len(raw_observations)),
                            "message": f"Processed {i} observations..."
                        }

            # If no observations found, provide info about the dataset structure
            if not records:
                yield {
                    "phase": "completed",
                    "progress": 100,
                    "message": f"Dataset {dataset_id} found but observations require specific dimension queries. Total available: ~{total_observations:,}",
                    "records": [],
                    "count": 0,
                    "total_available": total_observations,
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
            logger.exception(f"ONS import error for {dataset_id}")
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
            "message": f"Import complete: {len(records)} observations in {duration_ms}ms",
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
            "datasets": self.KNOWN_DATASETS,
        }
