"""
Device inventory data models.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class Device(BaseModel):
    """
    Represents a network device in the inventory.
    
    Tracks device identity, classification, and metadata.
    """

    ip: str = Field(..., description="IP address of the device")
    mac: Optional[str] = Field(None, description="MAC address if known")
    hostname: Optional[str] = Field(None, description="Hostname if resolved")
    first_seen: datetime = Field(
        default_factory=datetime.utcnow,
        description="When device was first observed",
    )
    last_seen: datetime = Field(
        default_factory=datetime.utcnow,
        description="When device was last observed",
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Tags for categorization (iot, lab, family_tv, etc.)",
    )
    guess_type: Optional[str] = Field(
        None,
        description="Inferred device type (TV, phone, NAS, unknown)",
    )
    owner: Optional[str] = Field(None, description="Device owner/responsible party")
    
    # Additional metadata
    vendor: Optional[str] = Field(None, description="Device vendor (from MAC OUI)")
    os_guess: Optional[str] = Field(None, description="Operating system guess")
    open_ports: List[int] = Field(
        default_factory=list,
        description="Known open ports",
    )
    common_destinations: List[str] = Field(
        default_factory=list,
        description="Frequently contacted domains/IPs",
    )
    
    # Risk scoring
    risk_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Risk score 0-1 based on behavior",
    )
    anomaly_count: int = Field(
        default=0,
        description="Number of anomalies detected for this device",
    )
    intel_match_count: int = Field(
        default=0,
        description="Number of threat intel matches",
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "ip": "192.168.1.50",
                "mac": "aa:bb:cc:dd:ee:ff",
                "hostname": "living-room-tv",
                "first_seen": "2025-01-01T00:00:00Z",
                "last_seen": "2025-01-15T12:00:00Z",
                "tags": ["iot", "tv", "family"],
                "guess_type": "Smart TV",
                "owner": "family",
                "vendor": "Samsung",
                "open_ports": [8008, 8009, 8443],
                "common_destinations": ["youtube.com", "netflix.com"],
                "risk_score": 0.1,
                "anomaly_count": 0,
                "intel_match_count": 0,
            }
        }


class DeviceActivity(BaseModel):
    """
    Summary of device network activity for a time period.
    """

    device_ip: str
    time_period_start: datetime
    time_period_end: datetime
    
    # Activity metrics
    connection_count: int = 0
    unique_destinations: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    dns_queries: int = 0
    
    # Protocol breakdown
    tcp_connections: int = 0
    udp_connections: int = 0
    icmp_packets: int = 0
    
    # Alerts
    suricata_alerts: int = 0
    ai_anomalies: int = 0
    intel_matches: int = 0


class InventoryEvent(BaseModel):
    """
    Event emitted when inventory changes (new device, tag change, etc.).
    """

    event_type: str  # new_device, tag_added, device_updated
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    device_ip: str
    details: dict = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "new_device",
                "timestamp": "2025-01-15T10:30:00Z",
                "device_ip": "192.168.1.100",
                "details": {
                    "mac": "11:22:33:44:55:66",
                    "hostname": "unknown-device",
                },
            }
        }
