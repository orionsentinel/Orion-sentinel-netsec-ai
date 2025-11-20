"""
Threat Intelligence Sources

Pluggable source classes for ingesting threat intelligence from various feeds.
All sources respect ToS and use documented APIs/RSS feeds only.
"""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional, Any
from urllib.parse import urlparse
import feedparser
import requests

logger = logging.getLogger(__name__)


@dataclass
class ThreatIntelItem:
    """Raw threat intelligence item from a source."""
    source_name: str
    title: str
    content: str
    url: Optional[str]
    published: Optional[datetime]
    metadata: Dict[str, Any]


class ThreatIntelSource(ABC):
    """
    Abstract base class for threat intelligence sources.
    
    Implementations must respect source ToS and use only documented APIs.
    """
    
    def __init__(self, source_name: str, enabled: bool = True):
        """
        Initialize threat intelligence source.
        
        Args:
            source_name: Unique name for this source
            enabled: Whether source is enabled
        """
        self.source_name = source_name
        self.enabled = enabled
        self.last_fetch = None
        self.fetch_count = 0
        self.error_count = 0
    
    @abstractmethod
    def fetch(self) -> List[ThreatIntelItem]:
        """
        Fetch latest threat intelligence items.
        
        Returns:
            List of ThreatIntelItem objects
        """
        pass
    
    def fetch_with_error_handling(self) -> List[ThreatIntelItem]:
        """
        Wrapper that handles errors and tracks statistics.
        
        Returns:
            List of ThreatIntelItem objects (empty list on error)
        """
        if not self.enabled:
            logger.debug(f"Source {self.source_name} is disabled")
            return []
        
        try:
            logger.info(f"Fetching from source: {self.source_name}")
            items = self.fetch()
            self.last_fetch = datetime.now()
            self.fetch_count += 1
            logger.info(f"✓ Fetched {len(items)} items from {self.source_name}")
            return items
            
        except Exception as e:
            self.error_count += 1
            logger.error(
                f"Failed to fetch from {self.source_name}: {e}",
                exc_info=True
            )
            return []


class RSSFeedSource(ThreatIntelSource):
    """
    RSS/Atom feed source for threat intelligence.
    
    Uses feedparser library to parse standard RSS/Atom feeds.
    Common sources: security blogs, CERT advisories, vendor feeds.
    """
    
    def __init__(
        self,
        source_name: str,
        feed_url: str,
        enabled: bool = True,
        max_items: int = 50,
        timeout: int = 30
    ):
        """
        Initialize RSS feed source.
        
        Args:
            source_name: Unique name for this source
            feed_url: RSS/Atom feed URL
            enabled: Whether source is enabled
            max_items: Maximum items to fetch per request
            timeout: HTTP timeout in seconds
        """
        super().__init__(source_name, enabled)
        self.feed_url = feed_url
        self.max_items = max_items
        self.timeout = timeout
    
    def fetch(self) -> List[ThreatIntelItem]:
        """Fetch items from RSS feed."""
        # Parse feed with timeout
        feed = feedparser.parse(
            self.feed_url,
            request_headers={
                'User-Agent': 'Orion-Sentinel-ThreatIntel/1.0'
            }
        )
        
        if feed.bozo:
            # Feed has parsing errors
            logger.warning(
                f"Feed parsing errors for {self.source_name}: "
                f"{feed.bozo_exception}"
            )
        
        items = []
        for entry in feed.entries[:self.max_items]:
            # Extract content (try multiple fields)
            content = ""
            if hasattr(entry, 'summary'):
                content = entry.summary
            elif hasattr(entry, 'description'):
                content = entry.description
            elif hasattr(entry, 'content'):
                content = entry.content[0].value if entry.content else ""
            
            # Parse published date
            published = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                try:
                    published = datetime(*entry.published_parsed[:6])
                except (TypeError, ValueError):
                    pass
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                try:
                    published = datetime(*entry.updated_parsed[:6])
                except (TypeError, ValueError):
                    pass
            
            # Create item
            item = ThreatIntelItem(
                source_name=self.source_name,
                title=entry.get('title', ''),
                content=content,
                url=entry.get('link'),
                published=published,
                metadata={
                    'author': entry.get('author', ''),
                    'tags': [tag.term for tag in entry.get('tags', [])],
                }
            )
            items.append(item)
        
        return items


class JSONAPISource(ThreatIntelSource):
    """
    JSON API source for threat intelligence.
    
    Fetches threat intelligence from JSON REST APIs.
    Requires API documentation and ToS compliance.
    """
    
    def __init__(
        self,
        source_name: str,
        api_url: str,
        enabled: bool = True,
        api_key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        item_path: str = "items"  # JSON path to items array
    ):
        """
        Initialize JSON API source.
        
        Args:
            source_name: Unique name for this source
            api_url: API endpoint URL
            enabled: Whether source is enabled
            api_key: Optional API key for authentication
            headers: Optional custom HTTP headers
            timeout: HTTP timeout in seconds
            item_path: JSON path to items array (dot-notation)
        """
        super().__init__(source_name, enabled)
        self.api_url = api_url
        self.api_key = api_key
        self.timeout = timeout
        self.item_path = item_path
        
        # Build headers
        self.headers = {
            'User-Agent': 'Orion-Sentinel-ThreatIntel/1.0',
            'Accept': 'application/json',
        }
        if headers:
            self.headers.update(headers)
        if api_key:
            # Common API key header patterns
            self.headers['X-API-Key'] = api_key
            self.headers['Authorization'] = f'Bearer {api_key}'
    
    def fetch(self) -> List[ThreatIntelItem]:
        """Fetch items from JSON API."""
        response = requests.get(
            self.api_url,
            headers=self.headers,
            timeout=self.timeout
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Navigate to items array using path
        items_data = self._get_nested_value(data, self.item_path)
        if not isinstance(items_data, list):
            logger.warning(
                f"Item path '{self.item_path}' did not return a list"
            )
            items_data = [data]  # Treat whole response as single item
        
        items = []
        for item_data in items_data:
            # Extract common fields (customize per API)
            item = ThreatIntelItem(
                source_name=self.source_name,
                title=item_data.get('title') or item_data.get('name', ''),
                content=item_data.get('description') or item_data.get('content', ''),
                url=item_data.get('url') or item_data.get('link'),
                published=self._parse_timestamp(
                    item_data.get('published') or item_data.get('created_at')
                ),
                metadata=item_data
            )
            items.append(item)
        
        return items
    
    def _get_nested_value(self, data: Dict, path: str) -> Any:
        """Get nested value from dict using dot notation."""
        keys = path.split('.')
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key, {})
            else:
                return value
        return value
    
    def _parse_timestamp(self, ts: Optional[str]) -> Optional[datetime]:
        """Parse various timestamp formats."""
        if not ts:
            return None
        
        # Try ISO format
        try:
            return datetime.fromisoformat(ts.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            pass
        
        # Try Unix timestamp
        try:
            return datetime.fromtimestamp(float(ts))
        except (ValueError, TypeError):
            pass
        
        return None


# Preconfigured sources (can be enabled via config)

def get_builtin_sources(config: Dict[str, Any]) -> List[ThreatIntelSource]:
    """
    Get list of built-in threat intelligence sources.
    
    Args:
        config: Configuration dict with source settings
        
    Returns:
        List of configured ThreatIntelSource instances
    """
    sources = []
    
    # US-CERT Alerts (RSS)
    if config.get('enable_uscert', True):
        sources.append(RSSFeedSource(
            source_name='us-cert-alerts',
            feed_url='https://www.cisa.gov/cybersecurity-advisories/all.xml',
            enabled=config.get('enable_uscert', True)
        ))
    
    # SANS Internet Storm Center (RSS)
    if config.get('enable_sans', True):
        sources.append(RSSFeedSource(
            source_name='sans-isc',
            feed_url='https://isc.sans.edu/rssfeed.xml',
            enabled=config.get('enable_sans', True)
        ))
    
    # Krebs on Security (RSS)
    if config.get('enable_krebs', True):
        sources.append(RSSFeedSource(
            source_name='krebs-security',
            feed_url='https://krebsonsecurity.com/feed/',
            enabled=config.get('enable_krebs', True)
        ))
    
    # Threatpost (RSS)
    if config.get('enable_threatpost', True):
        sources.append(RSSFeedSource(
            source_name='threatpost',
            feed_url='https://threatpost.com/feed/',
            enabled=config.get('enable_threatpost', True)
        ))
    
    # Bleeping Computer (RSS)
    if config.get('enable_bleeping', True):
        sources.append(RSSFeedSource(
            source_name='bleeping-computer',
            feed_url='https://www.bleepingcomputer.com/feed/',
            enabled=config.get('enable_bleeping', True)
        ))
    
    # AlienVault OTX (API - if key provided)
    otx_key = config.get('otx_api_key')
    if otx_key:
        sources.append(JSONAPISource(
            source_name='alienvault-otx',
            api_url='https://otx.alienvault.com/api/v1/pulses/subscribed',
            api_key=otx_key,
            enabled=True,
            item_path='results'
        ))
    
    # abuse.ch URLhaus (JSON API - no key required)
    if config.get('enable_urlhaus', True):
        sources.append(JSONAPISource(
            source_name='urlhaus-recent',
            api_url='https://urlhaus-api.abuse.ch/v1/urls/recent/',
            enabled=config.get('enable_urlhaus', True),
            item_path='urls',
            headers={'Content-Type': 'application/json'}
        ))
    
    logger.info(f"Initialized {len(sources)} threat intelligence sources")
    return sources
