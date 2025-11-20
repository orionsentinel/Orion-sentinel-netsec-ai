"""
Threat Intelligence Module

Ingests external threat intelligence from multiple sources, extracts IOCs,
and correlates them with network/DNS logs for enhanced detection.
"""

from .sources import ThreatIntelSource, RSSFeedSource, JSONAPISource
from .ioc_extractor import IOCExtractor, IOC, IOCType
from .store import IOCStore
from .correlator import ThreatCorrelator
from .service import ThreatIntelService

__all__ = [
    'ThreatIntelSource',
    'RSSFeedSource',
    'JSONAPISource',
    'IOCExtractor',
    'IOC',
    'IOCType',
    'IOCStore',
    'ThreatCorrelator',
    'ThreatIntelService',
]
