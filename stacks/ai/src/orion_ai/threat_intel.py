"""
Threat Intelligence Feed Integration

Fetches and caches indicators of compromise (IOCs) from multiple threat intelligence sources.
Cross-references detected domains/IPs against known threats to boost risk scores.
"""

import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum

import aiohttp

logger = logging.getLogger(__name__)


class ThreatType(Enum):
    """Types of threat indicators"""
    MALICIOUS_DOMAIN = "malicious_domain"
    MALICIOUS_IP = "malicious_ip"
    C2_SERVER = "c2_server"
    PHISHING = "phishing"
    MALWARE_URL = "malware_url"


@dataclass
class ThreatIndicator:
    """Represents a threat indicator"""
    value: str  # Domain, IP, or URL
    threat_type: ThreatType
    source: str  # Feed source name
    confidence: float  # 0.0 to 1.0
    first_seen: datetime
    last_updated: datetime
    description: Optional[str] = None


class ThreatIntelligenceCache:
    """
    SQLite-backed cache for threat intelligence indicators.
    Provides fast lookups during detection pipelines.
    """
    
    def __init__(self, db_path: str = "/var/lib/orion-ai/threat_intel.db"):
        """
        Initialize threat intelligence cache.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS threat_indicators (
                value TEXT PRIMARY KEY,
                threat_type TEXT NOT NULL,
                source TEXT NOT NULL,
                confidence REAL NOT NULL,
                first_seen TEXT NOT NULL,
                last_updated TEXT NOT NULL,
                description TEXT
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_threat_type 
            ON threat_indicators(threat_type)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_last_updated 
            ON threat_indicators(last_updated)
        """)
        
        conn.commit()
        conn.close()
    
    def add_indicators(self, indicators: List[ThreatIndicator]):
        """
        Add or update threat indicators in cache.
        
        Args:
            indicators: List of threat indicators to add
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for indicator in indicators:
            cursor.execute("""
                INSERT OR REPLACE INTO threat_indicators 
                (value, threat_type, source, confidence, first_seen, last_updated, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                indicator.value,
                indicator.threat_type.value,
                indicator.source,
                indicator.confidence,
                indicator.first_seen.isoformat(),
                indicator.last_updated.isoformat(),
                indicator.description
            ))
        
        conn.commit()
        conn.close()
        logger.info(f"Added {len(indicators)} threat indicators to cache")
    
    def lookup(self, value: str) -> Optional[ThreatIndicator]:
        """
        Look up a domain or IP in the threat intelligence cache.
        
        Args:
            value: Domain or IP to check
            
        Returns:
            ThreatIndicator if found, None otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT value, threat_type, source, confidence, first_seen, last_updated, description
            FROM threat_indicators
            WHERE value = ?
        """, (value,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return ThreatIndicator(
                value=row[0],
                threat_type=ThreatType(row[1]),
                source=row[2],
                confidence=row[3],
                first_seen=datetime.fromisoformat(row[4]),
                last_updated=datetime.fromisoformat(row[5]),
                description=row[6]
            )
        return None
    
    def cleanup_old_indicators(self, days: int = 30):
        """
        Remove indicators older than specified days.
        
        Args:
            days: Remove indicators not updated in this many days
        """
        cutoff = datetime.now() - timedelta(days=days)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM threat_indicators
            WHERE last_updated < ?
        """, (cutoff.isoformat(),))
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        logger.info(f"Cleaned up {deleted} old threat indicators")


class ThreatFeedFetcher:
    """
    Fetches threat intelligence from multiple public sources.
    """
    
    def __init__(self, otx_api_key: Optional[str] = None, timeout: int = 30):
        """
        Initialize threat feed fetcher.
        
        Args:
            otx_api_key: AlienVault OTX API key (optional, increases rate limits)
            timeout: HTTP request timeout in seconds
        """
        self.otx_api_key = otx_api_key
        self.timeout = timeout
    
    async def fetch_alienvault_otx_domains(self) -> List[ThreatIndicator]:
        """
        Fetch malicious domains from AlienVault OTX.
        
        Returns:
            List of threat indicators
        """
        indicators = []
        url = "https://otx.alienvault.com/api/v1/pulses/subscribed"
        
        headers = {}
        if self.otx_api_key:
            headers["X-OTX-API-KEY"] = self.otx_api_key
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=self.timeout) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        # Parse pulses and extract domain indicators
                        for pulse in data.get("results", [])[:100]:  # Limit to recent 100
                            for indicator in pulse.get("indicators", []):
                                if indicator.get("type") == "domain":
                                    indicators.append(ThreatIndicator(
                                        value=indicator["indicator"],
                                        threat_type=ThreatType.MALICIOUS_DOMAIN,
                                        source="AlienVault OTX",
                                        confidence=0.8,
                                        first_seen=datetime.now(),
                                        last_updated=datetime.now(),
                                        description=pulse.get("name")
                                    ))
                        
                        logger.info(f"Fetched {len(indicators)} domains from AlienVault OTX")
                    else:
                        logger.warning(f"AlienVault OTX returned status {resp.status}")
        
        except asyncio.TimeoutError:
            logger.error("Timeout fetching from AlienVault OTX")
        except Exception as e:
            logger.error(f"Error fetching from AlienVault OTX: {e}")
        
        return indicators
    
    async def fetch_urlhaus_domains(self) -> List[ThreatIndicator]:
        """
        Fetch malicious domains from abuse.ch URLhaus.
        
        Returns:
            List of threat indicators
        """
        indicators = []
        url = "https://urlhaus.abuse.ch/downloads/csv_recent/"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=self.timeout) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        
                        # Parse CSV (skip comments starting with #)
                        for line in text.split('\n'):
                            if line.startswith('#') or not line.strip():
                                continue
                            
                            parts = line.split(',')
                            if len(parts) >= 3:
                                # Extract domain from URL
                                url_str = parts[2].strip('"')
                                if '://' in url_str:
                                    domain = url_str.split('://')[1].split('/')[0]
                                    
                                    indicators.append(ThreatIndicator(
                                        value=domain,
                                        threat_type=ThreatType.MALWARE_URL,
                                        source="URLhaus",
                                        confidence=0.9,
                                        first_seen=datetime.now(),
                                        last_updated=datetime.now(),
                                        description="Malware distribution"
                                    ))
                        
                        logger.info(f"Fetched {len(indicators)} domains from URLhaus")
                    else:
                        logger.warning(f"URLhaus returned status {resp.status}")
        
        except asyncio.TimeoutError:
            logger.error("Timeout fetching from URLhaus")
        except Exception as e:
            logger.error(f"Error fetching from URLhaus: {e}")
        
        return indicators
    
    async def fetch_feodo_ips(self) -> List[ThreatIndicator]:
        """
        Fetch C2 server IPs from abuse.ch Feodo Tracker.
        
        Returns:
            List of threat indicators
        """
        indicators = []
        url = "https://feodotracker.abuse.ch/downloads/ipblocklist.txt"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=self.timeout) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        
                        # Parse IP list (skip comments starting with #)
                        for line in text.split('\n'):
                            if line.startswith('#') or not line.strip():
                                continue
                            
                            ip = line.strip()
                            if ip:
                                indicators.append(ThreatIndicator(
                                    value=ip,
                                    threat_type=ThreatType.C2_SERVER,
                                    source="Feodo Tracker",
                                    confidence=0.95,
                                    first_seen=datetime.now(),
                                    last_updated=datetime.now(),
                                    description="Botnet C2 server"
                                ))
                        
                        logger.info(f"Fetched {len(indicators)} IPs from Feodo Tracker")
                    else:
                        logger.warning(f"Feodo Tracker returned status {resp.status}")
        
        except asyncio.TimeoutError:
            logger.error("Timeout fetching from Feodo Tracker")
        except Exception as e:
            logger.error(f"Error fetching from Feodo Tracker: {e}")
        
        return indicators
    
    async def fetch_phishtank_domains(self) -> List[ThreatIndicator]:
        """
        Fetch phishing domains from PhishTank.
        Note: Requires API key for full access, using verified list here.
        
        Returns:
            List of threat indicators
        """
        indicators = []
        url = "http://data.phishtank.com/data/online-valid.json"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=self.timeout) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        for entry in data[:1000]:  # Limit to 1000 most recent
                            url_str = entry.get("url", "")
                            if '://' in url_str:
                                domain = url_str.split('://')[1].split('/')[0]
                                
                                indicators.append(ThreatIndicator(
                                    value=domain,
                                    threat_type=ThreatType.PHISHING,
                                    source="PhishTank",
                                    confidence=0.85,
                                    first_seen=datetime.now(),
                                    last_updated=datetime.now(),
                                    description="Phishing site"
                                ))
                        
                        logger.info(f"Fetched {len(indicators)} domains from PhishTank")
                    else:
                        logger.warning(f"PhishTank returned status {resp.status}")
        
        except asyncio.TimeoutError:
            logger.error("Timeout fetching from PhishTank")
        except Exception as e:
            logger.error(f"Error fetching from PhishTank: {e}")
        
        return indicators
    
    async def fetch_all_feeds(self) -> List[ThreatIndicator]:
        """
        Fetch from all configured threat intelligence sources concurrently.
        
        Returns:
            Combined list of all threat indicators
        """
        logger.info("Starting threat intelligence feed fetch from all sources")
        
        # Fetch all feeds concurrently
        results = await asyncio.gather(
            self.fetch_alienvault_otx_domains(),
            self.fetch_urlhaus_domains(),
            self.fetch_feodo_ips(),
            self.fetch_phishtank_domains(),
            return_exceptions=True
        )
        
        # Combine results, filtering out exceptions
        all_indicators = []
        for result in results:
            if isinstance(result, list):
                all_indicators.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Feed fetch failed: {result}")
        
        # Deduplicate by value
        unique_indicators = {}
        for indicator in all_indicators:
            if indicator.value not in unique_indicators:
                unique_indicators[indicator.value] = indicator
            else:
                # Keep the one with higher confidence
                if indicator.confidence > unique_indicators[indicator.value].confidence:
                    unique_indicators[indicator.value] = indicator
        
        logger.info(f"Fetched total of {len(unique_indicators)} unique threat indicators")
        return list(unique_indicators.values())


class ThreatIntelligenceService:
    """
    High-level service for threat intelligence integration.
    Manages cache updates and provides lookup interface for pipelines.
    """
    
    def __init__(
        self,
        cache_path: str = "/var/lib/orion-ai/threat_intel.db",
        otx_api_key: Optional[str] = None,
        refresh_interval_hours: int = 6
    ):
        """
        Initialize threat intelligence service.
        
        Args:
            cache_path: Path to SQLite cache database
            otx_api_key: AlienVault OTX API key (optional)
            refresh_interval_hours: How often to refresh feeds
        """
        self.cache = ThreatIntelligenceCache(cache_path)
        self.fetcher = ThreatFeedFetcher(otx_api_key=otx_api_key)
        self.refresh_interval = timedelta(hours=refresh_interval_hours)
        self.last_refresh: Optional[datetime] = None
    
    async def refresh_feeds(self, force: bool = False):
        """
        Refresh threat intelligence feeds if needed.
        
        Args:
            force: Force refresh even if not due yet
        """
        if not force and self.last_refresh:
            if datetime.now() - self.last_refresh < self.refresh_interval:
                logger.info("Threat feeds not due for refresh yet")
                return
        
        logger.info("Refreshing threat intelligence feeds")
        indicators = await self.fetcher.fetch_all_feeds()
        
        if indicators:
            self.cache.add_indicators(indicators)
            self.last_refresh = datetime.now()
            logger.info(f"Successfully refreshed {len(indicators)} threat indicators")
        else:
            logger.warning("No threat indicators fetched")
    
    def check_domain(self, domain: str) -> Optional[ThreatIndicator]:
        """
        Check if a domain is a known threat.
        
        Args:
            domain: Domain to check
            
        Returns:
            ThreatIndicator if domain is malicious, None otherwise
        """
        return self.cache.lookup(domain)
    
    def check_ip(self, ip: str) -> Optional[ThreatIndicator]:
        """
        Check if an IP is a known threat.
        
        Args:
            ip: IP address to check
            
        Returns:
            ThreatIndicator if IP is malicious, None otherwise
        """
        return self.cache.lookup(ip)
    
    def cleanup_old_data(self, days: int = 30):
        """
        Clean up threat indicators older than specified days.
        
        Args:
            days: Remove data older than this many days
        """
        self.cache.cleanup_old_indicators(days)
