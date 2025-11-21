"""
View logic for UI pages.

Functions that query data and prepare view models for templates.
"""

import logging
import os
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

from orion_ai.core.loki_client import LokiClient
from orion_ai.core.models import Event, EventType, EventSeverity
from orion_ai.health_score.calculator import HealthScoreCalculator
from orion_ai.health_score.service import HealthScoreService
from orion_ai.inventory.store import DeviceStore
from orion_ai.soar.models import Playbook

logger = logging.getLogger(__name__)


def get_dashboard_view() -> Dict[str, Any]:
    """
    Get data for dashboard/home page.
    
    Returns:
        Dictionary with dashboard data
    """
    loki = LokiClient()
    device_store = DeviceStore()
    health_service = HealthScoreService()
    
    # Get current health score
    try:
        health_score = health_service.run_once()
        health_service_instance = health_service
        calculator = health_service_instance.calculator
        metrics = health_service_instance._collect_metrics()
        health_obj = calculator.compute_health_score(metrics)
    except Exception as e:
        logger.error(f"Failed to get health score: {e}")
        health_obj = None
    
    # Get recent events (last 24 hours)
    try:
        recent_events = get_recent_events(limit=10, hours=24)
    except Exception as e:
        logger.error(f"Failed to get recent events: {e}")
        recent_events = []
    
    # Get device stats
    try:
        devices = device_store.list_devices(limit=1000)
        device_stats = {
            "total": len(devices),
            "unknown": sum(1 for d in devices if not d.tags or d.guess_type == "unknown"),
            "recent": sum(1 for d in devices if (datetime.now() - d.last_seen).days < 1),
        }
    except Exception as e:
        logger.error(f"Failed to get device stats: {e}")
        device_stats = {"total": 0, "unknown": 0, "recent": 0}
    
    # Get top suspicious devices (those with most critical events)
    try:
        suspicious_devices = get_suspicious_devices(limit=3)
    except Exception as e:
        logger.error(f"Failed to get suspicious devices: {e}")
        suspicious_devices = []
    
    return {
        "health_score": health_obj,
        "recent_events": recent_events,
        "device_stats": device_stats,
        "suspicious_devices": suspicious_devices,
        "timestamp": datetime.now(),
    }


def get_recent_events(
    limit: int = 50,
    hours: int = 24,
    severity_filter: Optional[List[str]] = None,
    type_filter: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Get recent security events from Loki.
    
    Args:
        limit: Maximum number of events
        hours: How far back to look
        severity_filter: Optional list of severities to include
        type_filter: Optional list of event types to include
        
    Returns:
        List of event dictionaries
    """
    loki = LokiClient()
    
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    
    # Build query
    query = '{stream="events"}'
    
    # TODO: Add label filters for severity and type if provided
    # LogQL filtering would be more efficient than post-processing
    
    try:
        logs = loki.query_range(query, start_time, end_time, limit=limit)
        
        # Filter results if needed
        if severity_filter:
            logs = [l for l in logs if l.get("severity") in severity_filter]
        
        if type_filter:
            logs = [l for l in logs if l.get("event_type") in type_filter]
        
        return logs
    except Exception as e:
        logger.error(f"Failed to query events: {e}")
        return []


def list_devices_view(
    tag_filter: Optional[str] = None,
    search: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get list of devices with summary stats.
    
    Args:
        tag_filter: Optional tag to filter by
        search: Optional search term (IP, hostname, MAC)
        
    Returns:
        List of device view models
    """
    device_store = DeviceStore()
    loki = LokiClient()
    
    # Get devices
    devices = device_store.list_devices(tag_filter=tag_filter, limit=1000)
    
    # Apply search filter
    if search:
        search_lower = search.lower()
        devices = [
            d for d in devices
            if (search_lower in d.ip.lower() or
                (d.hostname and search_lower in d.hostname.lower()) or
                (d.mac and search_lower in d.mac.lower()))
        ]
    
    # Enrich with event counts (simple version - count from last 7 days)
    device_views = []
    for device in devices:
        # TODO: Query event counts per device from Loki
        # For now, just use basic device data
        device_views.append({
            "device": device,
            "alert_count": 0,  # TODO
            "anomaly_count": 0,  # TODO
            "risk_level": "low",  # TODO: calculate based on tags and events
        })
    
    return device_views


def get_device_profile(device_id: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed profile for a specific device.
    
    Args:
        device_id: Device identifier
        
    Returns:
        Device profile dictionary or None if not found
    """
    device_store = DeviceStore()
    loki = LokiClient()
    
    # Get device
    device = device_store.get_device_by_id(device_id)
    if not device:
        return None
    
    # Get recent events for this device
    end_time = datetime.now()
    start_time = end_time - timedelta(days=7)
    
    try:
        # Query events for this device
        query = f'{{stream="events", device_id="{device_id}"}}'
        events = loki.query_range(query, start_time, end_time, limit=100)
    except Exception as e:
        logger.error(f"Failed to query device events: {e}")
        events = []
    
    # TODO: Get recent DNS queries, Suricata alerts, etc. for this device IP
    
    # Categorize events
    event_counts = {
        "intel_match": sum(1 for e in events if e.get("event_type") == "intel_match"),
        "device_anomaly": sum(1 for e in events if e.get("event_type") == "device_anomaly"),
        "domain_risk": sum(1 for e in events if e.get("event_type") == "domain_risk"),
    }
    
    return {
        "device": device,
        "events": events,
        "event_counts": event_counts,
        "dns_queries": [],  # TODO
        "suricata_alerts": [],  # TODO
        "timeline": _build_device_timeline(device, events),
    }


def get_suspicious_devices(limit: int = 5) -> List[Dict[str, Any]]:
    """
    Get devices with the most suspicious activity.
    
    Args:
        limit: Maximum number of devices to return
        
    Returns:
        List of device dictionaries with risk scores
    """
    device_store = DeviceStore()
    loki = LokiClient()
    
    devices = device_store.list_devices(limit=1000)
    
    # Score devices based on tags and recent events
    scored_devices = []
    for device in devices:
        risk_score = 0
        
        # Tags contribute to risk
        if "threat-intel-match" in device.tags:
            risk_score += 50
        if "anomalous" in device.tags:
            risk_score += 30
        if "honeypot-access" in device.tags:
            risk_score += 70
        
        # Unknown devices are slightly suspicious
        if not device.tags or device.guess_type == "unknown":
            risk_score += 10
        
        if risk_score > 0:
            scored_devices.append({
                "device": device,
                "risk_score": risk_score,
            })
    
    # Sort by risk score
    scored_devices.sort(key=lambda x: x["risk_score"], reverse=True)
    
    return scored_devices[:limit]


def _build_device_timeline(device, events: List[Dict]) -> List[Dict[str, Any]]:
    """Build a timeline of device activity."""
    timeline = []
    
    # Add first seen
    timeline.append({
        "timestamp": device.first_seen,
        "type": "first_seen",
        "description": "Device first observed on network",
    })
    
    # Add events
    for event in events:
        timeline.append({
            "timestamp": event.get("_timestamp", datetime.now()),
            "type": event.get("event_type", "unknown"),
            "description": event.get("title", ""),
            "severity": event.get("severity", "INFO"),
        })
    
    # Sort by timestamp
    timeline.sort(key=lambda x: x["timestamp"], reverse=True)
    
    return timeline


def get_playbooks_view() -> Dict[str, Any]:
    """
    Get playbooks data for playbooks page.
    
    Returns:
        Dictionary with playbooks and statistics
    """
    playbooks = _load_playbooks()
    
    # Calculate stats
    enabled_count = sum(1 for pb in playbooks if pb.enabled)
    disabled_count = sum(1 for pb in playbooks if not pb.enabled)
    dry_run_count = sum(1 for pb in playbooks if pb.dry_run)
    
    return {
        "playbooks": playbooks,
        "enabled_count": enabled_count,
        "disabled_count": disabled_count,
        "dry_run_count": dry_run_count,
    }


def get_playbook(playbook_id: str) -> Optional[Playbook]:
    """
    Get a specific playbook by ID.
    
    Args:
        playbook_id: Playbook identifier
        
    Returns:
        Playbook object or None if not found
    """
    playbooks = _load_playbooks()
    
    for pb in playbooks:
        if pb.id == playbook_id:
            return pb
    
    return None


def toggle_playbook(playbook_id: str, enabled: bool) -> bool:
    """
    Toggle a playbook enabled/disabled state.
    
    Updates the playbooks.yml file with the new state.
    
    Args:
        playbook_id: Playbook identifier
        enabled: New enabled state
        
    Returns:
        True if successful, False if playbook not found
    """
    playbooks_file = _get_playbooks_file_path()
    
    try:
        # Load YAML
        with open(playbooks_file, 'r') as f:
            data = yaml.safe_load(f)
        
        # Find and update playbook
        found = False
        playbooks_list = data.get('playbooks', [])
        for pb_dict in playbooks_list:
            if pb_dict.get('id') == playbook_id:
                pb_dict['enabled'] = enabled
                found = True
                break
        
        if not found:
            return False
        
        # Write back
        with open(playbooks_file, 'w') as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Playbook {playbook_id} {'enabled' if enabled else 'disabled'}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to toggle playbook: {e}")
        return False


def _get_playbooks_file_path() -> Path:
    """Get path to playbooks.yml file."""
    # Check environment variable first
    playbooks_file = os.getenv("SOAR_PLAYBOOKS_FILE")
    if playbooks_file:
        return Path(playbooks_file)
    
    # Default paths to check
    possible_paths = [
        Path("/config/playbooks.yml"),
        Path("./config/playbooks.yml"),
        Path("./stacks/ai/config/playbooks.yml"),
        Path(__file__).parent.parent.parent / "config" / "playbooks.yml",
    ]
    
    for path in possible_paths:
        if path.exists():
            return path
    
    # No playbooks file found - raise error with helpful message
    logger.error(
        "Playbooks file not found. Checked paths: " +
        ", ".join(str(p) for p in possible_paths)
    )
    raise FileNotFoundError(
        "Playbooks file not found. Set SOAR_PLAYBOOKS_FILE environment variable "
        "or place playbooks.yml in one of the default locations."
    )


def _load_playbooks() -> List[Playbook]:
    """
    Load playbooks from playbooks.yml.
    
    Returns:
        List of Playbook objects
    """
    playbooks_file = _get_playbooks_file_path()
    
    try:
        with open(playbooks_file, 'r') as f:
            data = yaml.safe_load(f)
        
        playbooks_list = data.get('playbooks', [])
        playbooks = [Playbook.from_dict(pb) for pb in playbooks_list]
        
        # Sort by priority (descending)
        playbooks.sort(key=lambda x: x.priority, reverse=True)
        
        return playbooks
        
    except FileNotFoundError:
        logger.warning(f"Playbooks file not found: {playbooks_file}")
        return []
    except Exception as e:
        logger.error(f"Failed to load playbooks: {e}")
        return []
