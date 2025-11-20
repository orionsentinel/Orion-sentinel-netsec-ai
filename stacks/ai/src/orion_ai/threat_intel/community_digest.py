"""
Community Intelligence Digest

Builds human-readable summaries of security community discussions.
Provides context for threat landscape awareness, NOT primary blocking decisions.
"""

import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Set, Optional, Tuple
from collections import Counter

from .community_sources import CommunityPost
from .ioc_extractor import IOCExtractor, IOC, IOCType

logger = logging.getLogger(__name__)


class CommunityDigest:
    """
    Builds digestible summaries from community security posts.
    
    Focuses on providing human-readable context about current threats
    and security discussions.
    """
    
    # Keywords that indicate threat-relevant content
    THREAT_KEYWORDS = {
        # Malware types
        'ransomware', 'trojan', 'backdoor', 'rootkit', 'worm', 'virus',
        'spyware', 'adware', 'cryptominer', 'botnet',
        
        # Attack types
        'phishing', 'exploit', 'zero-day', '0day', 'vulnerability',
        'breach', 'compromise', 'intrusion', 'attack', 'apt',
        
        # Infrastructure
        'c2', 'command and control', 'c&c', 'infrastructure',
        'malicious domain', 'malicious ip',
        
        # Specific threats
        'cve-', 'malware', 'threat actor', 'campaign',
        'supply chain', 'lateral movement',
        
        # Response/detection
        'ioc', 'indicator', 'yara', 'sigma', 'detection',
    }
    
    # Keywords for filtering (must contain at least one)
    RELEVANCE_KEYWORDS = {
        'malware', 'ransomware', 'apt', 'breach', 'exploit',
        'vulnerability', 'cve', 'zero-day', '0day', 'phishing',
        'botnet', 'c2', 'threat', 'attack', 'compromise',
    }
    
    def __init__(
        self,
        extract_iocs: bool = True,
        ioc_confidence_penalty: float = 0.5
    ):
        """
        Initialize community digest builder.
        
        Args:
            extract_iocs: Whether to extract IOCs from posts
            ioc_confidence_penalty: Penalty factor for IOC confidence (0-1)
                                   since community posts are lower confidence
        """
        self.extract_iocs = extract_iocs
        self.ioc_confidence_penalty = ioc_confidence_penalty
        
        if extract_iocs:
            self.ioc_extractor = IOCExtractor()
        else:
            self.ioc_extractor = None
    
    def filter_relevant_posts(
        self,
        posts: List[CommunityPost],
        keywords: Optional[Set[str]] = None,
        min_score: Optional[int] = None
    ) -> List[CommunityPost]:
        """
        Filter posts for threat intelligence relevance.
        
        Args:
            posts: List of community posts
            keywords: Set of keywords to match (None = use defaults)
            min_score: Minimum score/upvotes (None = no filter)
            
        Returns:
            Filtered list of relevant posts
        """
        if keywords is None:
            keywords = self.RELEVANCE_KEYWORDS
        
        relevant = []
        
        for post in posts:
            # Check score threshold
            if min_score and post.score and post.score < min_score:
                continue
            
            # Check for keyword presence
            text_lower = (post.title + " " + post.body).lower()
            
            has_keyword = any(kw in text_lower for kw in keywords)
            
            if has_keyword:
                relevant.append(post)
        
        logger.info(
            f"Filtered {len(relevant)} relevant posts from {len(posts)} total"
        )
        
        return relevant
    
    def extract_iocs_from_posts(
        self,
        posts: List[CommunityPost]
    ) -> List[IOC]:
        """
        Extract IOCs from community posts.
        
        NOTE: IOCs from community posts are LOW CONFIDENCE and should
        be treated as leads for investigation, not automatic blocking.
        
        Args:
            posts: List of community posts
            
        Returns:
            List of IOCs with reduced confidence scores
        """
        if not self.ioc_extractor:
            return []
        
        all_iocs = []
        
        for post in posts:
            text = f"{post.title}\n\n{post.body}"
            
            # Extract IOCs
            iocs = self.ioc_extractor.extract(
                text,
                source=f"community_{post.subreddit_or_forum}"
            )
            
            # Apply confidence penalty
            for ioc in iocs:
                ioc.confidence *= self.ioc_confidence_penalty
                # Add context tag
                if "community_source" not in ioc.tags:
                    ioc.tags.append("community_source")
                if "low_confidence" not in ioc.tags:
                    ioc.tags.append("low_confidence")
            
            all_iocs.extend(iocs)
        
        logger.info(
            f"Extracted {len(all_iocs)} IOCs from {len(posts)} community posts "
            f"(confidence penalty: {self.ioc_confidence_penalty})"
        )
        
        return all_iocs
    
    def build_digest(
        self,
        posts: List[CommunityPost],
        time_range: str = "24h",
        max_posts: int = 10
    ) -> Dict[str, any]:
        """
        Build a human-readable digest from community posts.
        
        Args:
            posts: List of community posts
            time_range: Time range description (e.g., "24h", "7d")
            max_posts: Maximum posts to include in digest
            
        Returns:
            Dict containing digest data
        """
        if not posts:
            return {
                "time_range": time_range,
                "post_count": 0,
                "summary_markdown": "No relevant community discussions found.",
                "top_keywords": [],
                "sources": [],
            }
        
        # Sort by score (if available) and recency
        sorted_posts = sorted(
            posts,
            key=lambda p: (p.score or 0, p.created_at),
            reverse=True
        )[:max_posts]
        
        # Extract top keywords
        top_keywords = self._extract_top_keywords(posts)
        
        # Get source breakdown
        sources = list(set(p.subreddit_or_forum for p in posts))
        
        # Build markdown summary
        summary = self._build_markdown_summary(
            sorted_posts,
            time_range,
            top_keywords
        )
        
        return {
            "time_range": time_range,
            "post_count": len(posts),
            "summary_markdown": summary,
            "top_keywords": top_keywords[:10],
            "sources": sources,
            "posts": [p.to_dict() for p in sorted_posts],
        }
    
    def _extract_top_keywords(
        self,
        posts: List[CommunityPost],
        top_n: int = 10
    ) -> List[Tuple[str, int]]:
        """
        Extract most common threat keywords from posts.
        
        Returns:
            List of (keyword, count) tuples
        """
        keyword_counts = Counter()
        
        for post in posts:
            text_lower = (post.title + " " + post.body).lower()
            
            for keyword in self.THREAT_KEYWORDS:
                if keyword in text_lower:
                    keyword_counts[keyword] += 1
        
        return keyword_counts.most_common(top_n)
    
    def _build_markdown_summary(
        self,
        posts: List[CommunityPost],
        time_range: str,
        top_keywords: List[Tuple[str, int]]
    ) -> str:
        """
        Build markdown-formatted summary.
        
        Returns:
            Markdown string
        """
        lines = []
        
        lines.append(f"# Security Community Intelligence Digest ({time_range})")
        lines.append("")
        lines.append(f"**Posts Analyzed:** {len(posts)}")
        lines.append("")
        
        # Top keywords section
        if top_keywords:
            lines.append("## Trending Topics")
            lines.append("")
            for keyword, count in top_keywords[:5]:
                lines.append(f"- **{keyword}**: {count} mentions")
            lines.append("")
        
        # Top posts section
        lines.append("## Notable Discussions")
        lines.append("")
        
        for i, post in enumerate(posts[:5], 1):
            lines.append(f"### {i}. {post.title}")
            lines.append("")
            lines.append(f"**Source:** {post.subreddit_or_forum}")
            lines.append(f"**URL:** {post.url}")
            
            if post.score:
                lines.append(f"**Score:** {post.score} upvotes")
            
            if post.author:
                lines.append(f"**Author:** u/{post.author}")
            
            lines.append("")
            
            # Truncated body
            body_preview = post.body[:300]
            if len(post.body) > 300:
                body_preview += "..."
            
            lines.append(f"> {body_preview}")
            lines.append("")
            lines.append("---")
            lines.append("")
        
        return "\n".join(lines)
    
    def build_loki_event(
        self,
        digest: Dict[str, any],
        timestamp: Optional[datetime] = None
    ) -> Dict[str, any]:
        """
        Build Loki log event from digest.
        
        Args:
            digest: Digest dictionary from build_digest()
            timestamp: Event timestamp (default: now)
            
        Returns:
            Dict formatted for Loki ingestion
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        return {
            "timestamp": timestamp.isoformat(),
            "type": "community_intel_digest",
            "stream": "community_intel_digest",
            "component": "threat_intel",
            "time_range": digest["time_range"],
            "post_count": digest["post_count"],
            "sources": digest["sources"],
            "top_keywords": [kw for kw, _ in digest["top_keywords"]],
            "summary_markdown": digest["summary_markdown"],
            # Include first 3 posts for quick reference
            "featured_posts": digest["posts"][:3] if digest.get("posts") else [],
        }


def build_community_digest(
    posts: List[CommunityPost],
    time_range: str = "24h",
    extract_iocs: bool = True,
    filter_relevant: bool = True
) -> Tuple[Dict[str, any], List[IOC]]:
    """
    Convenience function to build digest and extract IOCs.
    
    Args:
        posts: List of community posts
        time_range: Time range description
        extract_iocs: Whether to extract IOCs
        filter_relevant: Whether to filter for relevant posts only
        
    Returns:
        Tuple of (digest dict, list of IOCs)
    """
    digest_builder = CommunityDigest(extract_iocs=extract_iocs)
    
    # Filter posts
    if filter_relevant:
        filtered_posts = digest_builder.filter_relevant_posts(posts)
    else:
        filtered_posts = posts
    
    # Build digest
    digest = digest_builder.build_digest(filtered_posts, time_range=time_range)
    
    # Extract IOCs
    iocs = []
    if extract_iocs:
        iocs = digest_builder.extract_iocs_from_posts(filtered_posts)
    
    return digest, iocs
