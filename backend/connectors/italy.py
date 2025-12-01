"""
Italy ISTAT / dati.gov.it Data Connector
========================================
Connects to Italian government open data sources via CKAN API.

API Documentation:
- ISTAT: https://esploradati.istat.it/
- dati.gov.it: https://www.dati.gov.it/
- Developers Italia: https://developers.italia.it/

Infrastructure-related datasets:
- ISTAT statistical data warehouse
- Geospatial and infrastructure data
- Demographic and socio-economic data
"""

from typing import Dict, Any

from .base import CKANConnector


class ISTATConnector(CKANConnector):
    """
    Connector for Italian government data via ISTAT and dati.gov.it.

    Uses standard CKAN API - simplest implementation.
    dati.gov.it CKAN API: https://www.dati.gov.it/api/3/
    """

    BASE_URL = "https://www.dati.gov.it/api/3"
    SOURCE_NAME = "dati.gov.it"

    DATASET_SEARCHES = {
        "popolazione": {
            "query": "popolazione censimento",
            "asset_type": "demographics",
        },
        "infrastrutture": {
            "query": "infrastrutture pubbliche",
            "asset_type": "infrastructure",
        },
        "trasporti": {
            "query": "trasporti mobilità",
            "asset_type": "transport",
        },
        "protezione-civile": {
            "query": "protezione civile",
            "asset_type": "emergency",
        },
        "edilizia": {
            "query": "edilizia costruzioni",
            "asset_type": "construction",
        },
    }

    # Italian regions (kept for reference/future use)
    ITALIAN_REGIONS = [
        "Lombardia", "Lazio", "Campania", "Sicilia", "Veneto",
        "Emilia-Romagna", "Piemonte", "Puglia", "Toscana", "Calabria",
        "Sardegna", "Liguria", "Marche", "Abruzzo", "Friuli-Venezia Giulia",
        "Trentino-Alto Adige", "Umbria", "Basilicata", "Molise", "Valle d'Aosta"
    ]

    @property
    def connector_id(self) -> str:
        return "istat"

    @property
    def country(self) -> str:
        return "IT"

    @property
    def name(self) -> str:
        return "ISTAT / dati.gov.it"

    @property
    def description(self) -> str:
        return "Italian National Institute of Statistics - Infrastructure and demographic datasets"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize connector info for API response."""
        base = super().to_dict()
        base["datasets"] = list(self.DATASET_SEARCHES.keys())
        return base
