"""
Device profile API endpoints.

Provides detailed per-device views aggregating data from multiple sources.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/device", tags=["device"])


class DeviceProfile(BaseModel):
    """Complete device profile with aggregated data."""

    # Identity
    ip: str
    mac: Optional[str] = None
    hostname: Optional[str] = None
    
    # Classification
    device_type: Optional[str] = None
    tags: List[str] = []
    owner: Optional[str] = None
    
    # Activity summary
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    
    # Recent events (counts)
    suricata_alerts_24h: int = 0
    dns_queries_24h: int = 0
    ai_anomalies_24h: int = 0
    intel_matches_24h: int = 0
    change_events_24h: int = 0
    
    # Risk
    risk_score: float = 0.0
    risk_factors: List[str] = []
    
    # Network behavior
    top_destinations: List[str] = []
    open_ports: List[int] = []
    protocols_used: List[str] = []


class TimelineEvent(BaseModel):
    """Single event in device timeline."""

    timestamp: datetime
    event_type: str  # suricata_alert, dns_query, ai_anomaly, etc.
    severity: str = "info"
    summary: str
    details: Dict[str, Any] = {}


class DeviceTimeline(BaseModel):
    """Timeline of events for a device."""

    device_ip: str
    start_time: datetime
    end_time: datetime
    events: List[TimelineEvent] = []
    total_events: int = 0


@router.get("/{ip}", response_model=DeviceProfile)
async def get_device_profile(ip: str) -> DeviceProfile:
    """
    Get complete profile for a device.
    
    Aggregates data from:
    - Inventory database
    - Loki (Suricata, DNS, AI, Intel events)
    - Change monitor
    
    Args:
        ip: IP address of device
        
    Returns:
        Device profile
    """
    # TODO: Implement actual data fetching
    # 1. Query inventory store for device info
    # 2. Query Loki for recent events (last 24h)
    #    - {src_ip="<ip>"} for Suricata
    #    - {client_ip="<ip>"} for DNS
    #    - {device_ip="<ip>"} for AI/Intel
    # 3. Aggregate and return
    
    logger.info(f"Fetching profile for device: {ip}")
    
    # Placeholder response
    profile = DeviceProfile(
        ip=ip,
        mac="aa:bb:cc:dd:ee:ff",
        hostname="example-device",
        device_type="unknown",
        tags=["lab"],
        risk_score=0.2,
    )
    
    return profile


@router.get("/{ip}/timeline", response_model=DeviceTimeline)
async def get_device_timeline(
    ip: str,
    hours: int = Query(24, ge=1, le=168, description="Hours of history to fetch"),
) -> DeviceTimeline:
    """
    Get timeline of events for a device.
    
    Returns time-ordered list of significant events.
    
    Args:
        ip: IP address of device
        hours: How many hours of history to fetch (1-168)
        
    Returns:
        Device timeline
    """
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)
    
    logger.info(f"Fetching timeline for {ip} ({hours}h)")
    
    # TODO: Implement actual timeline fetching
    # 1. Query Loki for all events related to device
    # 2. Sort by timestamp
    # 3. Format as TimelineEvent objects
    # 4. Return with pagination
    
    timeline = DeviceTimeline(
        device_ip=ip,
        start_time=start_time,
        end_time=end_time,
        events=[],
        total_events=0,
    )
    
    return timeline


@router.get("/{ip}/alerts", response_model=List[Dict[str, Any]])
async def get_device_alerts(
    ip: str,
    hours: int = Query(24, ge=1, le=168),
) -> List[Dict[str, Any]]:
    """
    Get recent alerts for a device.
    
    Args:
        ip: IP address
        hours: Hours of history
        
    Returns:
        List of alerts
    """
    logger.info(f"Fetching alerts for {ip} ({hours}h)")
    
    # TODO: Query Loki for alerts where src_ip or dest_ip matches
    # Service labels: suricata, threat_intel, ai
    
    return []


@router.get("/{ip}/dns", response_model=List[Dict[str, Any]])
async def get_device_dns_queries(
    ip: str,
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(100, ge=1, le=1000),
) -> List[Dict[str, Any]]:
    """
    Get recent DNS queries from a device.
    
    Args:
        ip: IP address
        hours: Hours of history
        limit: Maximum queries to return
        
    Returns:
        List of DNS queries
    """
    logger.info(f"Fetching DNS queries for {ip} ({hours}h, limit={limit})")
    
    # TODO: Query Loki for DNS events where client_ip matches
    
    return []


@router.post("/{ip}/tag")
async def tag_device(ip: str, tag: str) -> Dict[str, str]:
    """
    Add a tag to a device.
    
    Args:
        ip: IP address
        tag: Tag to add
        
    Returns:
        Status message
    """
    logger.info(f"Tagging device {ip} with '{tag}'")
    
    # TODO: Update inventory store
    # from orion_ai.inventory.store import InventoryStore
    # store = InventoryStore()
    # success = store.tag_device(ip, tag)
    
    return {"status": "success", "message": f"Tagged {ip} with '{tag}' (TODO)"}


@router.get("/", response_model=List[DeviceProfile])
async def list_devices(
    tag: Optional[str] = Query(None, description="Filter by tag"),
    limit: int = Query(50, ge=1, le=500),
) -> List[DeviceProfile]:
    """
    List all devices with optional filtering.
    
    Args:
        tag: Optional tag filter
        limit: Maximum devices to return
        
    Returns:
        List of device profiles
    """
    logger.info(f"Listing devices (tag={tag}, limit={limit})")
    
    # TODO: Query inventory store
    # Apply filters and return device profiles
    
    return []
