"""
Threat Intelligence Data Models

Defines data structures for IOCs, advisories, and threat intelligence items.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class IntelSource(str, Enum):
    """Supported threat intelligence sources."""
    ABUSE_CH_THREATFOX = "abuse.ch_threatfox"
    ABUSE_CH_URLHAUS = "abuse.ch_urlhaus"
    ABUSE_CH_FEODO = "abuse.ch_feodo"
    ALIENVAULT_OTX = "alienvault_otx"
    CISA_KEV = "cisa_kev"
    SANS_ISC = "sans_isc"
    PHISHTANK = "phishtank"
    CUSTOM = "custom"


class IOCType(str, Enum):
    """Types of Indicators of Compromise."""
    IP = "ip"
    DOMAIN = "domain"
    URL = "url"
    HASH_MD5 = "hash_md5"
    HASH_SHA1 = "hash_sha1"
    HASH_SHA256 = "hash_sha256"
    EMAIL = "email"
    CVE = "cve"


class ThreatType(str, Enum):
    """Types of threats."""
    MALWARE = "malware"
    C2 = "c2"
    PHISHING = "phishing"
    BOTNET = "botnet"
    RANSOMWARE = "ransomware"
    EXPLOIT = "exploit"
    APT = "apt"
    SCANNER = "scanner"
    UNKNOWN = "unknown"


@dataclass
class IOC:
    """
    Indicator of Compromise.
    
    Represents a single threat indicator from any source.
    """
    value: str
    type: IOCType
    source: IntelSource
    first_seen: datetime
    last_seen: datetime
    confidence: float  # 0.0 to 1.0
    threat_type: ThreatType = ThreatType.UNKNOWN
    tags: List[str] = field(default_factory=list)
    raw_ref: str = ""  # URL or ID of source item
    description: Optional[str] = None
    malware_family: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/serialization."""
        return {
            "value": self.value,
            "type": self.type.value,
            "source": self.source.value,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "confidence": self.confidence,
            "threat_type": self.threat_type.value,
            "tags": self.tags,
            "raw_ref": self.raw_ref,
            "description": self.description,
            "malware_family": self.malware_family,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IOC':
        """Create IOC from dictionary."""
        return cls(
            value=data["value"],
            type=IOCType(data["type"]),
            source=IntelSource(data["source"]),
            first_seen=datetime.fromisoformat(data["first_seen"]),
            last_seen=datetime.fromisoformat(data["last_seen"]),
            confidence=data["confidence"],
            threat_type=ThreatType(data.get("threat_type", "unknown")),
            tags=data.get("tags", []),
            raw_ref=data.get("raw_ref", ""),
            description=data.get("description"),
            malware_family=data.get("malware_family"),
        )


@dataclass
class Advisory:
    """
    Threat intelligence advisory (e.g., CISA KEV, CVE).
    
    Represents published security advisories and vulnerabilities.
    """
    advisory_id: str  # e.g., CVE-2024-1234, KEV-2024-001
    title: str
    description: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    source: IntelSource
    published_at: datetime
    updated_at: Optional[datetime] = None
    cve_ids: List[str] = field(default_factory=list)
    affected_products: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    exploit_available: bool = False
    raw_ref: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/serialization."""
        return {
            "advisory_id": self.advisory_id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "source": self.source.value,
            "published_at": self.published_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "cve_ids": self.cve_ids,
            "affected_products": self.affected_products,
            "tags": self.tags,
            "references": self.references,
            "exploit_available": self.exploit_available,
            "raw_ref": self.raw_ref,
        }


@dataclass
class IntelMatch:
    """
    Match between an IOC and observed network/DNS activity.
    
    Represents a correlation hit between threat intel and local logs.
    """
    ioc_value: str
    ioc_type: IOCType
    ioc_source: IntelSource
    ioc_confidence: float
    matched_at: datetime
    log_type: str  # "suricata", "dns", "http"
    device_ip: Optional[str] = None
    dest_ip: Optional[str] = None
    domain: Optional[str] = None
    url: Optional[str] = None
    log_timestamp: Optional[datetime] = None
    log_ref: str = ""  # Reference to original log entry
    threat_type: ThreatType = ThreatType.UNKNOWN
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Loki event."""
        return {
            "ioc_value": self.ioc_value,
            "ioc_type": self.ioc_type.value,
            "ioc_source": self.ioc_source.value,
            "ioc_confidence": self.ioc_confidence,
            "matched_at": self.matched_at.isoformat(),
            "log_type": self.log_type,
            "device_ip": self.device_ip,
            "dest_ip": self.dest_ip,
            "domain": self.domain,
            "url": self.url,
            "log_timestamp": self.log_timestamp.isoformat() if self.log_timestamp else None,
            "log_ref": self.log_ref,
            "threat_type": self.threat_type.value,
            "tags": self.tags,
        }


class RawIntelItem(BaseModel):
    """
    Raw item from threat intelligence source before normalization.
    
    Used during fetch/parse phase before converting to IOC/Advisory.
    """
    source: IntelSource
    fetched_at: datetime = Field(default_factory=datetime.now)
    item_id: Optional[str] = None
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        arbitrary_types_allowed = True
