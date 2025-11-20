"""
Core data models for Orion Sentinel AI.

Defines shared data structures used across all modules.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Types of security events."""
    INTEL_MATCH = "intel_match"
    DEVICE_ANOMALY = "device_anomaly"
    DOMAIN_RISK = "domain_risk"
    NEW_DEVICE = "new_device"
    HONEYPOT_HIT = "honeypot_hit"
    CHANGE_EVENT = "change_event"
    SOAR_ACTION = "soar_action"
    SECURITY_HEALTH_UPDATE = "security_health_update"
    THREAT_FEED_UPDATE = "threat_feed_update"
    SURICATA_ALERT = "suricata_alert"


class EventSeverity(str, Enum):
    """Severity levels for events."""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class Device:
    """
    Represents a network device discovered through NSM/DNS logs.
    
    Attributes:
        device_id: Unique identifier (stable hash of MAC/IP or explicit ID)
        ip: IP address
        mac: MAC address (optional)
        hostname: DNS hostname (optional)
        first_seen: First time device was observed
        last_seen: Last time device was observed
        tags: User-defined tags (e.g., "iot", "lab", "tv", "trusted")
        guess_type: Guessed device type (e.g., "TV", "phone", "NAS", "laptop")
        owner: Device owner (optional)
    """
    device_id: str
    ip: str
    mac: Optional[str] = None
    hostname: Optional[str] = None
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    guess_type: Optional[str] = None
    owner: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/serialization."""
        return {
            "device_id": self.device_id,
            "ip": self.ip,
            "mac": self.mac,
            "hostname": self.hostname,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "tags": self.tags,
            "guess_type": self.guess_type,
            "owner": self.owner,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Device':
        """Create Device from dictionary."""
        return cls(
            device_id=data["device_id"],
            ip=data["ip"],
            mac=data.get("mac"),
            hostname=data.get("hostname"),
            first_seen=datetime.fromisoformat(data["first_seen"]),
            last_seen=datetime.fromisoformat(data["last_seen"]),
            tags=data.get("tags", []),
            guess_type=data.get("guess_type"),
            owner=data.get("owner"),
        )


@dataclass
class Event:
    """
    Generic security event structure for the event feed.
    
    All major subsystems emit Event instances to create a unified event stream.
    
    Attributes:
        event_id: Unique event identifier
        event_type: Type of event (from EventType enum)
        timestamp: When the event occurred
        device_id: Associated device ID (optional)
        ip: Associated IP address (optional)
        severity: Event severity level
        title: Short event title
        description: Detailed event description
        source: Module that generated the event (e.g., "ai", "threat_intel", "soar")
        metadata: Additional event-specific data
    """
    event_id: str
    event_type: EventType
    timestamp: datetime
    severity: EventSeverity
    title: str
    description: str
    source: str
    device_id: Optional[str] = None
    ip: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Loki/storage."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "device_id": self.device_id,
            "ip": self.ip,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "source": self.source,
            "metadata": self.metadata,
        }


@dataclass
class HealthMetrics:
    """
    Health metrics for security posture calculation.
    
    Attributes:
        unknown_device_count: Number of unknown/untagged devices
        high_anomaly_count: Number of high-severity anomalies
        intel_matches_count: Number of threat intelligence matches
        new_devices_count: Number of new devices in recent period
        critical_events_count: Number of unresolved critical events
        suricata_alerts_count: Number of Suricata alerts in recent period
    """
    unknown_device_count: int = 0
    high_anomaly_count: int = 0
    intel_matches_count: int = 0
    new_devices_count: int = 0
    critical_events_count: int = 0
    suricata_alerts_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "unknown_device_count": self.unknown_device_count,
            "high_anomaly_count": self.high_anomaly_count,
            "intel_matches_count": self.intel_matches_count,
            "new_devices_count": self.new_devices_count,
            "critical_events_count": self.critical_events_count,
            "suricata_alerts_count": self.suricata_alerts_count,
        }


@dataclass
class HealthScore:
    """
    Overall security health score.
    
    Attributes:
        score: Health score from 0-100 (100 = perfect, 0 = critical)
        timestamp: When the score was calculated
        metrics: Underlying metrics used for calculation
        status: Human-readable status (e.g., "Good", "Fair", "Poor")
        insights: List of key insights/recommendations
    """
    score: int
    timestamp: datetime
    metrics: HealthMetrics
    status: str = "Unknown"
    insights: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "score": self.score,
            "timestamp": self.timestamp.isoformat(),
            "metrics": self.metrics.to_dict(),
            "status": self.status,
            "insights": self.insights,
        }
