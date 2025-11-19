"""
IOC (Indicator of Compromise) Extractor

Extracts IOCs from text using regex patterns.
Supports: domains, IPs (IPv4/IPv6), URLs, file hashes (MD5, SHA1, SHA256), CVEs.
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Set, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class IOCType(Enum):
    """Types of Indicators of Compromise."""
    DOMAIN = "domain"
    IPV4 = "ipv4"
    IPV6 = "ipv6"
    URL = "url"
    MD5 = "md5"
    SHA1 = "sha1"
    SHA256 = "sha256"
    CVE = "cve"
    EMAIL = "email"


@dataclass
class IOC:
    """Indicator of Compromise."""
    type: IOCType
    value: str
    source: str  # Which source found this IOC
    context: Optional[str] = None  # Surrounding text for context
    confidence: float = 1.0  # Confidence score (0-1)


class IOCExtractor:
    """
    Extracts Indicators of Compromise from text.
    
    Uses regex patterns to identify IOCs in unstructured text
    from blogs, advisories, and threat feeds.
    """
    
    # Regex patterns for various IOC types
    PATTERNS = {
        IOCType.IPV4: re.compile(
            r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
            r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
        ),
        
        IOCType.IPV6: re.compile(
            r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b|'
            r'\b(?:[0-9a-fA-F]{1,4}:){1,7}:\b|'
            r'\b::(?:[0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4}\b'
        ),
        
        IOCType.DOMAIN: re.compile(
            r'\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}\b',
            re.IGNORECASE
        ),
        
        IOCType.URL: re.compile(
            r'https?://[^\s<>"{}|\\^`\[\]]+',
            re.IGNORECASE
        ),
        
        IOCType.MD5: re.compile(
            r'\b[a-fA-F0-9]{32}\b'
        ),
        
        IOCType.SHA1: re.compile(
            r'\b[a-fA-F0-9]{40}\b'
        ),
        
        IOCType.SHA256: re.compile(
            r'\b[a-fA-F0-9]{64}\b'
        ),
        
        IOCType.CVE: re.compile(
            r'\bCVE-\d{4}-\d{4,7}\b',
            re.IGNORECASE
        ),
        
        IOCType.EMAIL: re.compile(
            r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'
        ),
    }
    
    # Common false positive patterns to exclude
    EXCLUDE_DOMAINS = {
        # Common non-malicious domains
        'example.com', 'example.org', 'example.net',
        'localhost', 'test.com', 'google.com', 'microsoft.com',
        'apple.com', 'amazon.com', 'facebook.com', 'twitter.com',
        # Documentation domains
        'ietf.org', 'w3.org', 'rfc-editor.org',
        # Common CDNs/services
        'cloudflare.com', 'akamai.com', 'fastly.com',
    }
    
    EXCLUDE_IPS = {
        # Private IP ranges (these are extracted separately from context)
        '127.0.0.1', '0.0.0.0', '255.255.255.255',
        '10.0.0.0', '172.16.0.0', '192.168.0.0',
        '169.254.0.0',  # Link-local
    }
    
    def __init__(
        self,
        extract_types: Optional[Set[IOCType]] = None,
        defang: bool = True
    ):
        """
        Initialize IOC extractor.
        
        Args:
            extract_types: Set of IOC types to extract (None = all)
            defang: Whether to handle defanged IOCs (e.g., example[.]com)
        """
        self.extract_types = extract_types or set(IOCType)
        self.defang = defang
    
    def extract(self, text: str, source: str = "unknown") -> List[IOC]:
        """
        Extract all IOCs from text.
        
        Args:
            text: Text to extract IOCs from
            source: Source name for attribution
            
        Returns:
            List of IOC objects
        """
        if not text:
            return []
        
        # Refang text if defanging is enabled
        if self.defang:
            text = self._refang_text(text)
        
        iocs = []
        
        # Extract each IOC type
        for ioc_type in self.extract_types:
            if ioc_type not in self.PATTERNS:
                continue
            
            pattern = self.PATTERNS[ioc_type]
            matches = pattern.finditer(text)
            
            for match in matches:
                value = match.group(0)
                
                # Validate and filter
                if not self._is_valid_ioc(ioc_type, value):
                    continue
                
                # Get context (50 chars before and after)
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].strip()
                
                # Calculate confidence
                confidence = self._calculate_confidence(ioc_type, value, context)
                
                ioc = IOC(
                    type=ioc_type,
                    value=value.lower() if ioc_type in [IOCType.DOMAIN, IOCType.EMAIL] else value,
                    source=source,
                    context=context,
                    confidence=confidence
                )
                iocs.append(ioc)
        
        # Deduplicate while preserving highest confidence
        iocs = self._deduplicate_iocs(iocs)
        
        logger.debug(f"Extracted {len(iocs)} IOCs from {source}")
        return iocs
    
    def extract_by_type(
        self,
        text: str,
        ioc_type: IOCType,
        source: str = "unknown"
    ) -> List[IOC]:
        """
        Extract only specific IOC type.
        
        Args:
            text: Text to extract IOCs from
            ioc_type: Type of IOC to extract
            source: Source name
            
        Returns:
            List of IOC objects of specified type
        """
        original_types = self.extract_types
        self.extract_types = {ioc_type}
        iocs = self.extract(text, source)
        self.extract_types = original_types
        return iocs
    
    def _refang_text(self, text: str) -> str:
        """
        Convert defanged IOCs back to normal format.
        
        Common defanging patterns:
        - example[.]com -> example.com
        - example[dot]com -> example.com
        - hxxp://example.com -> http://example.com
        - 192[.]168[.]1[.]1 -> 192.168.1.1
        """
        text = re.sub(r'\[\.?\]', '.', text)
        text = re.sub(r'\[dot\]', '.', text, flags=re.IGNORECASE)
        text = re.sub(r'\[@\]', '@', text)
        text = re.sub(r'\[at\]', '@', text, flags=re.IGNORECASE)
        text = re.sub(r'hxxp', 'http', text, flags=re.IGNORECASE)
        text = re.sub(r'h\[tt\]p', 'http', text, flags=re.IGNORECASE)
        return text
    
    def _is_valid_ioc(self, ioc_type: IOCType, value: str) -> bool:
        """
        Validate if extracted value is a legitimate IOC.
        
        Filters out common false positives.
        """
        value_lower = value.lower()
        
        # Domain filtering
        if ioc_type == IOCType.DOMAIN:
            # Skip excluded domains
            if value_lower in self.EXCLUDE_DOMAINS:
                return False
            
            # Skip domains that are too short or long
            if len(value) < 4 or len(value) > 253:
                return False
            
            # Skip domains with invalid TLDs
            parts = value_lower.split('.')
            if len(parts) < 2:
                return False
            
            # TLD should be 2-63 chars
            tld = parts[-1]
            if len(tld) < 2 or len(tld) > 63:
                return False
            
            # Skip numeric-only domains
            if all(p.isdigit() for p in parts):
                return False
        
        # IP filtering
        elif ioc_type == IOCType.IPV4:
            if value in self.EXCLUDE_IPS:
                return False
            
            # Check if it's in private range
            octets = value.split('.')
            first_octet = int(octets[0])
            
            # Skip private IPs (unless from high-confidence source)
            if first_octet == 10:  # 10.0.0.0/8
                return False
            if first_octet == 172 and 16 <= int(octets[1]) <= 31:  # 172.16.0.0/12
                return False
            if first_octet == 192 and int(octets[1]) == 168:  # 192.168.0.0/16
                return False
            if first_octet == 127:  # Loopback
                return False
        
        # URL filtering
        elif ioc_type == IOCType.URL:
            try:
                parsed = urlparse(value)
                domain = parsed.netloc.lower()
                
                # Check if domain is in exclude list
                for excluded in self.EXCLUDE_DOMAINS:
                    if excluded in domain:
                        return False
            except Exception:
                return False
        
        # Hash filtering
        elif ioc_type in [IOCType.MD5, IOCType.SHA1, IOCType.SHA256]:
            # Must be valid hex
            try:
                int(value, 16)
            except ValueError:
                return False
            
            # Skip all-zeros or all-ones (common placeholder values)
            if value in ['0' * len(value), 'f' * len(value), 'F' * len(value)]:
                return False
        
        return True
    
    def _calculate_confidence(
        self,
        ioc_type: IOCType,
        value: str,
        context: str
    ) -> float:
        """
        Calculate confidence score for IOC based on context.
        
        Higher confidence for IOCs mentioned with threat keywords.
        """
        confidence = 0.5  # Base confidence
        
        context_lower = context.lower()
        
        # Boost confidence for threat-related keywords in context
        threat_keywords = [
            'malware', 'malicious', 'c2', 'command and control',
            'exploit', 'vulnerability', 'attack', 'compromise',
            'trojan', 'backdoor', 'ransomware', 'phishing',
            'botnet', 'apt', 'threat actor', 'indicator'
        ]
        
        keyword_count = sum(1 for kw in threat_keywords if kw in context_lower)
        confidence += min(0.4, keyword_count * 0.1)
        
        # Boost for certain IOC types
        if ioc_type in [IOCType.MD5, IOCType.SHA1, IOCType.SHA256]:
            # Hashes are rarely false positives
            confidence += 0.2
        
        if ioc_type == IOCType.CVE:
            # CVEs are specific and rarely false positives
            confidence += 0.3
        
        return min(1.0, confidence)
    
    def _deduplicate_iocs(self, iocs: List[IOC]) -> List[IOC]:
        """
        Deduplicate IOCs, keeping highest confidence for each unique value.
        """
        ioc_map = {}
        
        for ioc in iocs:
            key = (ioc.type, ioc.value)
            if key not in ioc_map or ioc.confidence > ioc_map[key].confidence:
                ioc_map[key] = ioc
        
        return list(ioc_map.values())
