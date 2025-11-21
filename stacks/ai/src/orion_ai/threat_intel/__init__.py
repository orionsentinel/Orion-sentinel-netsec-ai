"""
Threat Intelligence Module

Ingests external threat intelligence from multiple sources, extracts IOCs,
and correlates them with network/DNS logs for enhanced detection.
"""

from orion_ai.threat_intel.sources import ThreatIntelSource, RSSFeedSource, JSONAPISource
from orion_ai.threat_intel.ioc_models import IOC, IOCType, IntelSource, ThreatType
from orion_ai.threat_intel.store import IOCStore
from orion_ai.threat_intel.ioc_fetchers import (
    AlienVaultOTXFetcher,
    URLhausFetcher,
    FeodoTrackerFetcher,
    PhishTankFetcher,
)
from orion_ai.threat_intel.lookup import ThreatIntelLookup, get_ti_lookup, enrich_event_with_ti
from orion_ai.threat_intel.sync import ThreatIntelSync

__all__ = [
    'ThreatIntelSource',
    'RSSFeedSource',
    'JSONAPISource',
    'IOC',
    'IOCType',
    'IntelSource',
    'ThreatType',
    'IOCStore',
    'AlienVaultOTXFetcher',
    'URLhausFetcher',
    'FeodoTrackerFetcher',
    'PhishTankFetcher',
    'ThreatIntelLookup',
    'get_ti_lookup',
    'enrich_event_with_ti',
    'ThreatIntelSync',
]
