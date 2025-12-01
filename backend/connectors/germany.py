"""
Germany Destatis / GovData Connector
====================================
Connects to German government open data sources via CKAN API.

API Documentation:
- Destatis: https://www.destatis.de/
- GovData: https://www.govdata.de/
- DWD Weather: https://www.das-basisdienst.de/

Infrastructure-related datasets:
- Federal Statistical Office data
- Regional and state statistics
- Infrastructure and demographic data
"""

from typing import List, Dict, Any

from .base import CKANConnector


class DestatisConnector(CKANConnector):
    """
    Connector for German government data via Destatis and GovData.

    Uses CKAN API with permissive resource filtering.
    GovData CKAN API: https://www.govdata.de/ckan/api/3/
    """

    BASE_URL = "https://www.govdata.de/ckan/api/3"
    SOURCE_NAME = "GovData.de"

    DATASET_SEARCHES = {
        "bevoelkerung": {
            "query": "bevölkerung statistik",
            "asset_type": "demographics",
        },
        "infrastruktur": {
            "query": "infrastruktur öffentlich",
            "asset_type": "infrastructure",
        },
        "verkehr": {
            "query": "verkehr strassen",
            "asset_type": "transport",
        },
        "bauwesen": {
            "query": "bauwesen konstruktion",
            "asset_type": "construction",
        },
        "regionalstatistik": {
            "query": "regional statistik",
            "asset_type": "regional",
        },
    }

    # German states (Bundesländer)
    GERMAN_REGIONS = [
        "Baden-Württemberg", "Bayern", "Berlin", "Brandenburg",
        "Bremen", "Hamburg", "Hessen", "Mecklenburg-Vorpommern",
        "Niedersachsen", "Nordrhein-Westfalen", "Rheinland-Pfalz",
        "Saarland", "Sachsen", "Sachsen-Anhalt", "Schleswig-Holstein", "Thüringen"
    ]

    @property
    def connector_id(self) -> str:
        return "destatis"

    @property
    def country(self) -> str:
        return "DE"

    @property
    def name(self) -> str:
        return "Destatis / GovData"

    @property
    def description(self) -> str:
        return "German Federal Statistical Office - Infrastructure and demographic datasets"

    def _filter_tabular_resources(self, resources: List[Dict]) -> List[Dict]:
        """
        Override: More permissive filtering for German data.

        German government datasets often have non-standard formats.
        If no tabular resources found, fall back to trying ALL resources.
        """
        # Be more permissive - include TEXT and check URL extensions
        tabular = [
            r for r in resources
            if (r.get("format") or "").upper() in ("CSV", "JSON", "XLSX", "XLS", "TEXT", "")
            or r.get("url", "").lower().endswith(('.csv', '.json', '.txt'))
        ]

        # If no tabular resources found, try all resources
        return tabular if tabular else resources

    def to_dict(self) -> Dict[str, Any]:
        """Serialize connector info for API response."""
        base = super().to_dict()
        base["datasets"] = list(self.DATASET_SEARCHES.keys())
        return base
