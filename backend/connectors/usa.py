"""
USA Census Bureau / data.gov Data Connector
============================================
Connects to US government open data sources via CKAN API.

API Documentation:
- data.gov: https://data.gov/
- Census Bureau API: https://api.census.gov/
- USA Spending: https://api.usaspending.gov/

Infrastructure-related datasets:
- Census Bureau demographic data
- Federal infrastructure datasets
- Government spending data
"""

from typing import Dict, Any

from .base import CKANConnector


class CensusConnector(CKANConnector):
    """
    Connector for US government data via Census Bureau and data.gov.

    Uses standard CKAN API.
    data.gov CKAN API: https://catalog.data.gov/api/3/
    """

    BASE_URL = "https://catalog.data.gov/api/3"
    SOURCE_NAME = "data.gov"

    DATASET_SEARCHES = {
        "population": {
            "query": "census population",
            "asset_type": "demographics",
        },
        "infrastructure": {
            "query": "infrastructure federal",
            "asset_type": "infrastructure",
        },
        "transportation": {
            "query": "transportation highways",
            "asset_type": "transport",
        },
        "housing": {
            "query": "housing construction permits",
            "asset_type": "construction",
        },
        "geographic": {
            "query": "geographic boundaries",
            "asset_type": "regional",
        },
    }

    # US states (kept for reference/future use)
    US_STATES = [
        "California", "Texas", "Florida", "New York", "Pennsylvania",
        "Illinois", "Ohio", "Georgia", "North Carolina", "Michigan",
        "New Jersey", "Virginia", "Washington", "Arizona", "Massachusetts",
        "Tennessee", "Indiana", "Missouri", "Maryland", "Wisconsin"
    ]

    @property
    def connector_id(self) -> str:
        return "census"

    @property
    def country(self) -> str:
        return "US"

    @property
    def name(self) -> str:
        return "Census Bureau / data.gov"

    @property
    def description(self) -> str:
        return "US Census Bureau and data.gov - Infrastructure and demographic datasets"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize connector info for API response."""
        base = super().to_dict()
        base["datasets"] = list(self.DATASET_SEARCHES.keys())
        return base
