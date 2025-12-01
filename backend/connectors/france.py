"""
France INSEE / data.gouv.fr Data Connector
==========================================
Connects to French government open data sources.

API Documentation:
- data.gouv.fr: https://www.data.gouv.fr/api/
- INSEE: https://api.insee.fr/

Infrastructure-related datasets:
- National Building Registry (Referentiel National des Batiments)
- Public Service Data
- High-value datasets (infrastructure, demographics)
"""

import aiohttp
import logging
from typing import List, Dict, Any, Optional

from .base import CKANConnector, fetch_csv_preview

logger = logging.getLogger(__name__)


class INSEEConnector(CKANConnector):
    """
    Connector for French government data via data.gouv.fr and INSEE.

    Uses data.gouv.fr API (similar to CKAN but with different structure).
    Also supports data.gouv.fr's unique Tabular API.

    data.gouv.fr API: https://www.data.gouv.fr/api/1/
    Tabular API: https://tabular-api.data.gouv.fr/api/
    """

    BASE_URL = "https://www.data.gouv.fr/api/1"
    SOURCE_NAME = "data.gouv.fr"
    TABULAR_API_URL = "https://tabular-api.data.gouv.fr/api/resources"

    DATASET_SEARCHES = {
        "batiments": {
            "query": "referentiel national batiments",
            "asset_type": "buildings",
        },
        "infrastructure-transport": {
            "query": "infrastructure transport routes",
            "asset_type": "transport",
        },
        "donnees-locales": {
            "query": "donnees locales communes",
            "asset_type": "regional",
        },
        "population-insee": {
            "query": "population recensement insee",
            "asset_type": "demographics",
        },
        "equipements-publics": {
            "query": "equipements publics",
            "asset_type": "facilities",
        },
    }

    # French regions
    FRENCH_REGIONS = [
        "Île-de-France", "Auvergne-Rhône-Alpes", "Nouvelle-Aquitaine",
        "Occitanie", "Hauts-de-France", "Provence-Alpes-Côte d'Azur",
        "Grand Est", "Pays de la Loire", "Bretagne", "Normandie",
        "Bourgogne-Franche-Comté", "Centre-Val de Loire", "Corse"
    ]

    @property
    def connector_id(self) -> str:
        return "insee"

    @property
    def country(self) -> str:
        return "FR"

    @property
    def name(self) -> str:
        return "INSEE / data.gouv.fr"

    @property
    def description(self) -> str:
        return "French government open data - Infrastructure, buildings, and demographic datasets"

    def _get_api_endpoints(self) -> Dict[str, str]:
        """Override: data.gouv.fr uses different API structure than standard CKAN."""
        return {
            "search": f"{self.BASE_URL}/datasets/",
            "show": f"{self.BASE_URL}/datasets/{{id}}/",  # Needs {id} replaced
        }

    def _get_api_result_path(self, response_data: Dict) -> Any:
        """Override: data.gouv.fr returns data in 'data' key, not 'result'."""
        return response_data.get("data", [])

    async def _fetch_tabular_preview(
        self,
        resource_id: str,
        session: aiohttp.ClientSession,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch preview data from data.gouv.fr's unique Tabular API.

        This API provides structured access to CSV data and is specific to France.
        """
        records = []
        try:
            url = f"{self.TABULAR_API_URL}/{resource_id}/data/"
            params = {}
            if limit is not None:
                params["page_size"] = limit

            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    data = await response.json()
                    records = data.get("data", [])
        except Exception as e:
            logger.debug(f"Tabular API error for {resource_id}: {e}")
        return records

    async def _fetch_resource_data(
        self,
        resource: Dict[str, Any],
        dataset_id: str,
        dataset_title: str,
        session: aiohttp.ClientSession,
        limit: Optional[int]
    ) -> List[Dict[str, Any]]:
        """
        Override: Use France's Tabular API before falling back to CSV preview.
        """
        records = []
        resource_id = resource.get("id")
        resource_url = resource.get("url", "")
        resource_format = (resource.get("format") or "").upper()

        # Method 1: Try France's unique Tabular API
        if resource_id:
            tabular_records = await self._fetch_tabular_preview(resource_id, session, limit)
            if tabular_records:
                for row in tabular_records:
                    records.append({
                        "source": self.SOURCE_NAME,
                        "dataset_id": dataset_id,
                        "dataset_title": dataset_title,
                        "resource_id": resource_id,
                        **row
                    })
                return records

        # Method 2: Fall back to CSV preview
        if resource_format == "CSV" and resource_url:
            csv_records = await fetch_csv_preview(resource_url, session, limit, encoding='utf-8')
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

    def to_dict(self) -> Dict[str, Any]:
        """Serialize connector info for API response."""
        base = super().to_dict()
        base["datasets"] = list(self.DATASET_SEARCHES.keys())
        return base
