"""
IOC Feed Fetchers

Specialized fetchers for well-known IOC feeds:
- AlienVault OTX
- abuse.ch URLhaus
- abuse.ch Feodo Tracker
- PhishTank

All fetchers respect ToS and rate limits.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import requests

from orion_ai.threat_intel.ioc_models import (
    IOC,
    IOCType,
    IntelSource,
    ThreatType,
)

logger = logging.getLogger(__name__)


class AlienVaultOTXFetcher:
    """
    Fetcher for AlienVault Open Threat Exchange (OTX).
    
    Requires API key (free registration at otx.alienvault.com).
    """
    
    def __init__(self, api_key: str):
        """
        Initialize OTX fetcher.
        
        Args:
            api_key: OTX API key
        """
        self.api_key = api_key
        self.base_url = "https://otx.alienvault.com/api/v1"
        self.headers = {
            "X-OTX-API-KEY": api_key,
            "User-Agent": "Orion-Sentinel-ThreatIntel/1.0"
        }
    
    def fetch_recent_pulses(
        self,
        hours: int = 24,
        limit: int = 50
    ) -> List[IOC]:
        """
        Fetch recent threat pulses from OTX.
        
        Args:
            hours: Look back this many hours
            limit: Maximum number of pulses to fetch
            
        Returns:
            List of IOC objects
        """
        try:
            # Get subscribed pulses (most relevant to user)
            url = f"{self.base_url}/pulses/subscribed"
            params = {
                "limit": limit,
                "modified_since": (
                    datetime.now() - timedelta(hours=hours)
                ).isoformat()
            }
            
            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            pulses = data.get("results", [])
            
            iocs = []
            for pulse in pulses:
                # Extract IOCs from pulse indicators
                indicators = pulse.get("indicators", [])
                pulse_tags = pulse.get("tags", [])
                
                for indicator in indicators:
                    ioc_type_str = indicator.get("type", "").lower()
                    value = indicator.get("indicator", "")
                    
                    if not value:
                        continue
                    
                    # Map OTX type to our IOCType
                    ioc_type = self._map_otx_type(ioc_type_str)
                    if not ioc_type:
                        continue
                    
                    # Determine threat type from tags
                    threat_type = self._determine_threat_type(pulse_tags)
                    
                    # Create IOC
                    ioc = IOC(
                        value=value.lower(),
                        type=ioc_type,
                        source=IntelSource.ALIENVAULT_OTX,
                        first_seen=datetime.fromisoformat(
                            pulse.get("created", datetime.now().isoformat()).replace("Z", "+00:00")
                        ),
                        last_seen=datetime.fromisoformat(
                            pulse.get("modified", datetime.now().isoformat()).replace("Z", "+00:00")
                        ),
                        confidence=0.8,  # OTX is generally high quality
                        threat_type=threat_type,
                        tags=pulse_tags[:5],  # Limit tags
                        raw_ref=pulse.get("id", ""),
                        description=pulse.get("name", "")
                    )
                    iocs.append(ioc)
            
            logger.info(f"Fetched {len(iocs)} IOCs from AlienVault OTX")
            return iocs
            
        except Exception as e:
            logger.error(f"Failed to fetch from AlienVault OTX: {e}")
            return []
    
    def _map_otx_type(self, otx_type: str) -> Optional[IOCType]:
        """Map OTX indicator type to IOCType."""
        type_map = {
            "ipv4": IOCType.IP,
            "ipv6": IOCType.IP,
            "domain": IOCType.DOMAIN,
            "hostname": IOCType.DOMAIN,
            "url": IOCType.URL,
            "md5": IOCType.HASH_MD5,
            "sha1": IOCType.HASH_SHA1,
            "sha256": IOCType.HASH_SHA256,
            "email": IOCType.EMAIL,
            "cve": IOCType.CVE,
        }
        return type_map.get(otx_type)
    
    def _determine_threat_type(self, tags: List[str]) -> ThreatType:
        """Determine threat type from pulse tags."""
        tags_lower = [t.lower() for t in tags]
        
        if any(t in tags_lower for t in ["malware", "trojan", "virus"]):
            return ThreatType.MALWARE
        elif any(t in tags_lower for t in ["c2", "c&c", "command and control"]):
            return ThreatType.C2
        elif any(t in tags_lower for t in ["phishing", "phish"]):
            return ThreatType.PHISHING
        elif any(t in tags_lower for t in ["botnet", "bot"]):
            return ThreatType.BOTNET
        elif any(t in tags_lower for t in ["ransomware", "ransom"]):
            return ThreatType.RANSOMWARE
        elif any(t in tags_lower for t in ["apt", "advanced persistent"]):
            return ThreatType.APT
        elif any(t in tags_lower for t in ["exploit", "vulnerability"]):
            return ThreatType.EXPLOIT
        else:
            return ThreatType.UNKNOWN


class URLhausFetcher:
    """
    Fetcher for abuse.ch URLhaus (malicious URL database).
    
    No API key required.
    """
    
    def __init__(self):
        """Initialize URLhaus fetcher."""
        self.base_url = "https://urlhaus-api.abuse.ch/v1"
        self.headers = {
            "User-Agent": "Orion-Sentinel-ThreatIntel/1.0"
        }
    
    def fetch_recent_urls(
        self,
        hours: int = 24,
        limit: int = 100
    ) -> List[IOC]:
        """
        Fetch recent malicious URLs.
        
        Args:
            hours: Look back this many hours
            limit: Maximum number of URLs
            
        Returns:
            List of IOC objects
        """
        try:
            # URLhaus recent URLs endpoint
            url = f"{self.base_url}/urls/recent/"
            
            response = requests.post(
                url,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            urls = data.get("urls", [])
            
            iocs = []
            cutoff = datetime.now() - timedelta(hours=hours)
            
            for url_data in urls[:limit]:
                # Parse timestamp
                date_added = url_data.get("dateadded")
                if date_added:
                    try:
                        timestamp = datetime.strptime(
                            date_added,
                            "%Y-%m-%d %H:%M:%S"
                        )
                        if timestamp < cutoff:
                            continue  # Too old
                    except ValueError:
                        timestamp = datetime.now()
                else:
                    timestamp = datetime.now()
                
                url_value = url_data.get("url", "")
                if not url_value:
                    continue
                
                # Determine threat type from tags
                threat = url_data.get("threat", "malware")
                threat_type = self._map_threat(threat)
                
                # Create IOC
                ioc = IOC(
                    value=url_value.lower(),
                    type=IOCType.URL,
                    source=IntelSource.ABUSE_CH_URLHAUS,
                    first_seen=timestamp,
                    last_seen=timestamp,
                    confidence=0.9,  # abuse.ch is very reliable
                    threat_type=threat_type,
                    tags=[threat, url_data.get("url_status", "")],
                    raw_ref=url_data.get("id", ""),
                    description=f"URLhaus: {threat}",
                    malware_family=url_data.get("tags")
                )
                iocs.append(ioc)
            
            logger.info(f"Fetched {len(iocs)} IOCs from URLhaus")
            return iocs
            
        except Exception as e:
            logger.error(f"Failed to fetch from URLhaus: {e}")
            return []
    
    def _map_threat(self, threat: str) -> ThreatType:
        """Map URLhaus threat to ThreatType."""
        threat_lower = threat.lower()
        
        if "ransomware" in threat_lower:
            return ThreatType.RANSOMWARE
        elif "trojan" in threat_lower or "malware" in threat_lower:
            return ThreatType.MALWARE
        elif "phish" in threat_lower:
            return ThreatType.PHISHING
        else:
            return ThreatType.MALWARE  # Default for URLhaus


class FeodoTrackerFetcher:
    """
    Fetcher for abuse.ch Feodo Tracker (botnet C2 servers).
    
    No API key required.
    """
    
    def __init__(self):
        """Initialize Feodo Tracker fetcher."""
        self.feed_url = "https://feodotracker.abuse.ch/downloads/ipblocklist.json"
        self.headers = {
            "User-Agent": "Orion-Sentinel-ThreatIntel/1.0"
        }
    
    def fetch_c2_servers(self) -> List[IOC]:
        """
        Fetch active botnet C2 server IPs.
        
        Returns:
            List of IOC objects
        """
        try:
            response = requests.get(
                self.feed_url,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            iocs = []
            for entry in data:
                ip = entry.get("ip_address")
                if not ip:
                    continue
                
                # Parse timestamp
                first_seen_str = entry.get("first_seen")
                last_online_str = entry.get("last_online")
                
                try:
                    first_seen = datetime.strptime(
                        first_seen_str,
                        "%Y-%m-%d %H:%M:%S"
                    ) if first_seen_str else datetime.now()
                except ValueError:
                    first_seen = datetime.now()
                
                try:
                    last_seen = datetime.strptime(
                        last_online_str,
                        "%Y-%m-%d %H:%M:%S"
                    ) if last_online_str else datetime.now()
                except ValueError:
                    last_seen = datetime.now()
                
                malware = entry.get("malware", "botnet")
                
                # Create IOC
                ioc = IOC(
                    value=ip,
                    type=IOCType.IP,
                    source=IntelSource.ABUSE_CH_FEODO,
                    first_seen=first_seen,
                    last_seen=last_seen,
                    confidence=0.95,  # Feodo is very high confidence
                    threat_type=ThreatType.C2,
                    tags=["c2", "botnet", malware],
                    raw_ref="",
                    description=f"Feodo Tracker: {malware} C2",
                    malware_family=malware
                )
                iocs.append(ioc)
            
            logger.info(f"Fetched {len(iocs)} IOCs from Feodo Tracker")
            return iocs
            
        except Exception as e:
            logger.error(f"Failed to fetch from Feodo Tracker: {e}")
            return []


class PhishTankFetcher:
    """
    Fetcher for PhishTank (verified phishing sites).
    
    No API key required for basic feed, but rate-limited.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize PhishTank fetcher.
        
        Args:
            api_key: Optional API key for higher rate limits
        """
        self.api_key = api_key
        self.feed_url = "https://data.phishtank.com/data/online-valid.json"
        self.headers = {
            "User-Agent": "Orion-Sentinel-ThreatIntel/1.0"
        }
        if api_key:
            self.feed_url += f"?apikey={api_key}"
    
    def fetch_phishing_urls(
        self,
        hours: int = 24,
        limit: int = 100
    ) -> List[IOC]:
        """
        Fetch verified phishing URLs.
        
        Args:
            hours: Look back this many hours
            limit: Maximum number of URLs
            
        Returns:
            List of IOC objects
        """
        try:
            # PhishTank recommends caching and limiting requests
            response = requests.get(
                self.feed_url,
                headers=self.headers,
                timeout=60  # Large feed, may take time
            )
            response.raise_for_status()
            
            data = response.json()
            
            iocs = []
            cutoff = datetime.now() - timedelta(hours=hours)
            
            for entry in data[:limit]:
                # Parse verification time
                verification_time = entry.get("verification_time")
                if verification_time:
                    try:
                        # PhishTank uses ISO format
                        timestamp = datetime.fromisoformat(
                            verification_time.replace("Z", "+00:00")
                        )
                        if timestamp < cutoff:
                            continue  # Too old
                    except (ValueError, AttributeError):
                        timestamp = datetime.now()
                else:
                    timestamp = datetime.now()
                
                url_value = entry.get("url", "")
                if not url_value or not entry.get("verified", False):
                    continue  # Only use verified entries
                
                # Create IOC
                ioc = IOC(
                    value=url_value.lower(),
                    type=IOCType.URL,
                    source=IntelSource.PHISHTANK,
                    first_seen=timestamp,
                    last_seen=timestamp,
                    confidence=0.9,  # PhishTank verified entries are reliable
                    threat_type=ThreatType.PHISHING,
                    tags=["phishing", "verified"],
                    raw_ref=str(entry.get("phish_id", "")),
                    description=f"PhishTank verified phishing site",
                    malware_family=None
                )
                iocs.append(ioc)
            
            logger.info(f"Fetched {len(iocs)} IOCs from PhishTank")
            return iocs
            
        except Exception as e:
            logger.error(f"Failed to fetch from PhishTank: {e}")
            return []
