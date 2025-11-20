"""
Community Intelligence Sources

Fetches posts from security forums and communities for contextual threat intelligence.
This is for HUMAN CONTEXT, not primary blocking decisions.
"""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from urllib.parse import urljoin
import requests
import feedparser

logger = logging.getLogger(__name__)


@dataclass
class CommunityPost:
    """
    Post from a security community/forum.
    
    Used for building contextual intelligence digests.
    """
    id: str
    title: str
    url: str
    created_at: datetime
    body: str  # Full text or excerpt
    author: Optional[str] = None
    score: Optional[int] = None  # Upvotes/likes
    comments_count: Optional[int] = None
    subreddit_or_forum: str = ""
    tags: List[str] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "created_at": self.created_at.isoformat(),
            "body": self.body[:500],  # Truncate for storage
            "author": self.author,
            "score": self.score,
            "comments_count": self.comments_count,
            "subreddit_or_forum": self.subreddit_or_forum,
            "tags": self.tags,
        }


class CommunitySource(ABC):
    """
    Abstract base class for community threat intelligence sources.
    
    These provide human-readable context, NOT primary IOC feeds.
    """
    
    def __init__(self, source_name: str, enabled: bool = True):
        """
        Initialize community source.
        
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
    def fetch_recent_posts(
        self,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[CommunityPost]:
        """
        Fetch recent posts from community.
        
        Args:
            since: Fetch posts since this time (None = last 24h)
            limit: Maximum number of posts to fetch
            
        Returns:
            List of CommunityPost objects
        """
        pass
    
    def fetch_with_error_handling(
        self,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[CommunityPost]:
        """
        Wrapper that handles errors and tracks statistics.
        
        Returns:
            List of CommunityPost objects (empty on error)
        """
        if not self.enabled:
            logger.debug(f"Community source {self.source_name} is disabled")
            return []
        
        try:
            logger.info(f"Fetching from community: {self.source_name}")
            posts = self.fetch_recent_posts(since=since, limit=limit)
            self.last_fetch = datetime.now()
            self.fetch_count += 1
            logger.info(f"✓ Fetched {len(posts)} posts from {self.source_name}")
            return posts
            
        except Exception as e:
            self.error_count += 1
            logger.error(
                f"Failed to fetch from {self.source_name}: {e}",
                exc_info=True
            )
            return []


class RedditSource(CommunitySource):
    """
    Reddit API source for security subreddits.
    
    Uses Reddit's official API (requires OAuth credentials).
    ToS compliant - uses documented API endpoints only.
    """
    
    def __init__(
        self,
        subreddit: str,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        user_agent: str = "Orion-Sentinel-ThreatIntel/1.0",
        enabled: bool = True
    ):
        """
        Initialize Reddit source.
        
        Args:
            subreddit: Subreddit name (e.g., "netsec")
            client_id: Reddit API client ID
            client_secret: Reddit API client secret
            user_agent: User agent for API requests
            enabled: Whether source is enabled
        """
        super().__init__(f"reddit_{subreddit}", enabled)
        self.subreddit = subreddit
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent
        self.access_token = None
        self.token_expires_at = None
    
    def _get_access_token(self) -> str:
        """
        Get Reddit OAuth access token.
        
        Uses client credentials flow for read-only access.
        
        Returns:
            Access token
        """
        # TODO: Check if token is still valid
        if (self.access_token and self.token_expires_at and 
            datetime.now() < self.token_expires_at):
            return self.access_token
        
        # TODO: Implement actual OAuth flow
        # For now, this is a placeholder showing the structure
        logger.warning("Reddit OAuth not implemented - using placeholder")
        
        # Real implementation would be:
        # auth = requests.auth.HTTPBasicAuth(self.client_id, self.client_secret)
        # data = {'grant_type': 'client_credentials'}
        # headers = {'User-Agent': self.user_agent}
        # response = requests.post(
        #     'https://www.reddit.com/api/v1/access_token',
        #     auth=auth,
        #     data=data,
        #     headers=headers
        # )
        # token_data = response.json()
        # self.access_token = token_data['access_token']
        # self.token_expires_at = datetime.now() + timedelta(seconds=token_data['expires_in'])
        # return self.access_token
        
        return "placeholder_token"
    
    def fetch_recent_posts(
        self,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[CommunityPost]:
        """Fetch recent posts from subreddit."""
        if not self.client_id or not self.client_secret:
            logger.warning(
                f"Reddit API credentials not configured for r/{self.subreddit}"
            )
            # Fall back to RSS feed (no auth required, but limited data)
            return self._fetch_via_rss(limit)
        
        # TODO: Implement full Reddit API fetch
        # For now, fall back to RSS
        return self._fetch_via_rss(limit)
    
    def _fetch_via_rss(self, limit: int = 100) -> List[CommunityPost]:
        """
        Fetch posts via Reddit's RSS feed (no auth required).
        
        Limited data but ToS-compliant and simple.
        """
        feed_url = f"https://www.reddit.com/r/{self.subreddit}/new/.rss"
        
        feed = feedparser.parse(feed_url)
        
        posts = []
        for entry in feed.entries[:limit]:
            # Parse published date
            published = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                try:
                    published = datetime(*entry.published_parsed[:6])
                except (TypeError, ValueError):
                    published = datetime.now()
            
            # Extract content
            content = ""
            if hasattr(entry, 'summary'):
                content = entry.summary
            elif hasattr(entry, 'content'):
                content = entry.content[0].value if entry.content else ""
            
            # Clean HTML tags from content
            content = re.sub(r'<[^>]+>', '', content)
            content = content.strip()
            
            post = CommunityPost(
                id=entry.get('id', ''),
                title=entry.get('title', ''),
                url=entry.get('link', ''),
                created_at=published or datetime.now(),
                body=content,
                author=entry.get('author', ''),
                subreddit_or_forum=f"r/{self.subreddit}",
                raw_data=dict(entry)
            )
            posts.append(post)
        
        return posts


class RSSCommunitySource(CommunitySource):
    """
    Generic RSS feed source for security blogs/forums.
    
    Works with any RSS/Atom feed from security communities.
    """
    
    def __init__(
        self,
        source_name: str,
        feed_url: str,
        forum_name: str = "",
        enabled: bool = True
    ):
        """
        Initialize RSS community source.
        
        Args:
            source_name: Unique name for this source
            feed_url: RSS/Atom feed URL
            forum_name: Display name for the forum/blog
            enabled: Whether source is enabled
        """
        super().__init__(source_name, enabled)
        self.feed_url = feed_url
        self.forum_name = forum_name or source_name
    
    def fetch_recent_posts(
        self,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[CommunityPost]:
        """Fetch recent posts from RSS feed."""
        feed = feedparser.parse(self.feed_url)
        
        if feed.bozo:
            logger.warning(
                f"Feed parsing errors for {self.source_name}: "
                f"{feed.bozo_exception}"
            )
        
        posts = []
        for entry in feed.entries[:limit]:
            # Parse published date
            published = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                try:
                    published = datetime(*entry.published_parsed[:6])
                except (TypeError, ValueError):
                    pass
            
            # Skip old posts if since is specified
            if since and published and published < since:
                continue
            
            # Extract content
            content = ""
            if hasattr(entry, 'summary'):
                content = entry.summary
            elif hasattr(entry, 'description'):
                content = entry.description
            elif hasattr(entry, 'content'):
                content = entry.content[0].value if entry.content else ""
            
            # Clean HTML
            content = re.sub(r'<[^>]+>', '', content)
            content = content.strip()
            
            post = CommunityPost(
                id=entry.get('id', '') or entry.get('link', ''),
                title=entry.get('title', ''),
                url=entry.get('link', ''),
                created_at=published or datetime.now(),
                body=content,
                author=entry.get('author', ''),
                subreddit_or_forum=self.forum_name,
                tags=[tag.term for tag in entry.get('tags', [])],
                raw_data=dict(entry)
            )
            posts.append(post)
        
        return posts


def get_default_community_sources(config: Dict[str, Any]) -> List[CommunitySource]:
    """
    Get list of default community sources.
    
    Args:
        config: Configuration dict with source settings
        
    Returns:
        List of configured CommunitySource instances
    """
    sources = []
    
    # Reddit sources (if credentials provided)
    reddit_client_id = config.get('reddit_client_id')
    reddit_client_secret = config.get('reddit_client_secret')
    
    if config.get('enable_reddit_netsec', True):
        sources.append(RedditSource(
            subreddit='netsec',
            client_id=reddit_client_id,
            client_secret=reddit_client_secret,
            enabled=config.get('enable_reddit_netsec', True)
        ))
    
    if config.get('enable_reddit_threatintel', True):
        sources.append(RedditSource(
            subreddit='threatintel',
            client_id=reddit_client_id,
            client_secret=reddit_client_secret,
            enabled=config.get('enable_reddit_threatintel', True)
        ))
    
    if config.get('enable_reddit_cybersecurity', True):
        sources.append(RedditSource(
            subreddit='cybersecurity',
            client_id=reddit_client_id,
            client_secret=reddit_client_secret,
            enabled=config.get('enable_reddit_cybersecurity', True)
        ))
    
    # Security blogs via RSS
    if config.get('enable_schneier', True):
        sources.append(RSSCommunitySource(
            source_name='schneier_security',
            feed_url='https://www.schneier.com/blog/atom.xml',
            forum_name='Schneier on Security',
            enabled=config.get('enable_schneier', True)
        ))
    
    if config.get('enable_talos', True):
        sources.append(RSSCommunitySource(
            source_name='cisco_talos',
            feed_url='https://blog.talosintelligence.com/rss/',
            forum_name='Cisco Talos Blog',
            enabled=config.get('enable_talos', True)
        ))
    
    logger.info(f"Initialized {len(sources)} community intelligence sources")
    return sources
