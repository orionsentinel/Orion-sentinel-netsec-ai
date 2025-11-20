"""
Change monitoring data models.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChangeType(str, Enum):
    """Types of changes that can be detected."""

    NEW_DEVICE = "new_device"
    DEVICE_DISAPPEARED = "device_disappeared"
    NEW_PORT_FOR_DEVICE = "new_port_for_device"
    NEW_DOMAIN_FOR_DEVICE = "new_domain_for_device"
    NEW_DESTINATION_FOR_DEVICE = "new_destination_for_device"
    TAG_CHANGED = "tag_changed"
    RISK_SCORE_INCREASED = "risk_score_increased"
    TRAFFIC_PATTERN_CHANGED = "traffic_pattern_changed"
    NEW_SERVICE_DETECTED = "new_service_detected"


class Baseline(BaseModel):
    """
    Baseline snapshot of network state at a point in time.
    """

    snapshot_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    period_start: datetime
    period_end: datetime
    
    # Global baseline data
    total_devices: int = 0
    device_ips: List[str] = Field(default_factory=list)
    all_observed_ports: List[int] = Field(default_factory=list)
    all_observed_domains: List[str] = Field(default_factory=list)
    
    # Per-device baselines
    device_baselines: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "snapshot_id": "baseline_2025_01_15",
                "timestamp": "2025-01-15T00:00:00Z",
                "period_start": "2025-01-08T00:00:00Z",
                "period_end": "2025-01-15T00:00:00Z",
                "total_devices": 25,
                "device_ips": ["192.168.1.10", "192.168.1.20"],
                "all_observed_ports": [80, 443, 8080],
                "all_observed_domains": ["google.com", "github.com"],
            }
        }


class DeviceBaseline(BaseModel):
    """Baseline for a single device."""

    device_ip: str
    snapshot_timestamp: datetime
    
    # Behavioral baseline
    observed_ports: List[int] = Field(default_factory=list)
    observed_domains: List[str] = Field(default_factory=list)
    observed_destinations: List[str] = Field(default_factory=list)
    typical_protocols: List[str] = Field(default_factory=list)
    
    # Activity baseline
    avg_connections_per_day: float = 0.0
    avg_bytes_per_day: float = 0.0
    
    # Metadata
    tags: List[str] = Field(default_factory=list)
    risk_score: float = 0.0


class ChangeEvent(BaseModel):
    """
    Represents a detected change in the network.
    """

    change_id: str
    change_type: ChangeType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # What changed
    entity: str  # IP address, device ID, etc.
    entity_type: str = "device"  # device, global, service
    
    # Change details
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    
    # Risk assessment
    risk_level: str = "low"  # low, medium, high, critical
    
    # Context
    baseline_id: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "change_id": "chg_001",
                "change_type": "new_port_for_device",
                "timestamp": "2025-01-15T10:30:00Z",
                "entity": "192.168.1.50",
                "entity_type": "device",
                "old_value": [80, 443],
                "new_value": [80, 443, 22],
                "details": {"new_port": 22, "first_seen": "2025-01-15T10:00:00Z"},
                "risk_level": "medium",
            }
        }
