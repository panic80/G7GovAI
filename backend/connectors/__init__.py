"""
G7 Data Connectors Module
=========================
Real data connectors for G7 government data sources.

Supported Sources:
- StatCan (Statistics Canada) - Canada
- ONS (UK Office for National Statistics) - United Kingdom
- INSEE / data.gouv.fr - France
- Destatis / GovData - Germany
- ISTAT / dati.gov.it - Italy
- e-Gov / e-Stat - Japan
- Census Bureau / data.gov - United States
"""

from .statcan import StatCanConnector
from .ons import ONSConnector
from .france import INSEEConnector
from .germany import DestatisConnector
from .italy import ISTATConnector
from .japan import EGovConnector
from .usa import CensusConnector

# Registry of all available connectors (G7 nations)
CONNECTORS = {
    "CA": {
        "statcan": StatCanConnector(),
    },
    "UK": {
        "ons": ONSConnector(),
    },
    "FR": {
        "insee": INSEEConnector(),
    },
    "DE": {
        "destatis": DestatisConnector(),
    },
    "IT": {
        "istat": ISTATConnector(),
    },
    "JP": {
        "egov": EGovConnector(),
    },
    "US": {
        "census": CensusConnector(),
    },
}

__all__ = [
    "StatCanConnector",
    "ONSConnector",
    "INSEEConnector",
    "DestatisConnector",
    "ISTATConnector",
    "EGovConnector",
    "CensusConnector",
    "CONNECTORS",
]
