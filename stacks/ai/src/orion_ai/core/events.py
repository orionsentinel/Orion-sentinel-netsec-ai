"""
Event emission helpers for creating and pushing events to Loki.

Provides convenience functions for emitting security events from any module.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Optional, Any

from orion_ai.core.models import Event, EventType, EventSeverity
from orion_ai.core.loki_client import LokiClient

logger = logging.getLogger(__name__)

# Global Loki client instance
_loki_client: Optional[LokiClient] = None


def get_loki_client() -> LokiClient:
    """
    Get or create the global Loki client instance.
    
    Returns:
        LokiClient instance
    """
    global _loki_client
    if _loki_client is None:
        _loki_client = LokiClient()
    return _loki_client


def emit_event(event: Event) -> None:
    """
    Emit a security event to Loki.
    
    Converts the Event to JSON and pushes it to Loki with consistent labels.
    
    Args:
        event: Event instance to emit
        
    Labels applied:
        - stream: "events"
        - event_type: event.event_type
        - severity: event.severity
        - source: event.source
    """
    try:
        client = get_loki_client()
        
        # Build labels
        labels = {
            "stream": "events",
            "event_type": event.event_type.value,
            "severity": event.severity.value,
            "source": event.source,
        }
        
        # Add device_id to labels if present
        if event.device_id:
            labels["device_id"] = event.device_id
        
        # Convert event to dict
        log_data = event.to_dict()
        
        # Push to Loki
        client.push_log(labels, log_data, timestamp=event.timestamp)
        
        logger.info(
            f"Emitted event: {event.event_type.value} - {event.title} "
            f"(severity={event.severity.value})"
        )
        
    except Exception as e:
        logger.error(f"Failed to emit event to Loki: {e}")
        # Don't raise - we don't want event emission failures to break the caller


def create_event(
    event_type: EventType,
    severity: EventSeverity,
    title: str,
    description: str,
    source: str,
    device_id: Optional[str] = None,
    ip: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    timestamp: Optional[datetime] = None
) -> Event:
    """
    Create an Event instance with auto-generated ID.
    
    Args:
        event_type: Type of event
        severity: Severity level
        title: Short event title
        description: Detailed description
        source: Source module (e.g., "ai", "threat_intel", "soar")
        device_id: Optional associated device ID
        ip: Optional associated IP address
        metadata: Optional additional event data
        timestamp: Optional timestamp (default: now)
        
    Returns:
        Event instance
    """
    if timestamp is None:
        timestamp = datetime.now()
    
    if metadata is None:
        metadata = {}
    
    event_id = str(uuid.uuid4())
    
    return Event(
        event_id=event_id,
        event_type=event_type,
        timestamp=timestamp,
        severity=severity,
        title=title,
        description=description,
        source=source,
        device_id=device_id,
        ip=ip,
        metadata=metadata
    )


def emit_new_event(
    event_type: EventType,
    severity: EventSeverity,
    title: str,
    description: str,
    source: str,
    device_id: Optional[str] = None,
    ip: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    timestamp: Optional[datetime] = None
) -> Event:
    """
    Create and emit an event in one call.
    
    This is a convenience function that combines create_event and emit_event.
    
    Args:
        event_type: Type of event
        severity: Severity level
        title: Short event title
        description: Detailed description
        source: Source module
        device_id: Optional associated device ID
        ip: Optional associated IP address
        metadata: Optional additional event data
        timestamp: Optional timestamp (default: now)
        
    Returns:
        The created Event instance
    """
    event = create_event(
        event_type=event_type,
        severity=severity,
        title=title,
        description=description,
        source=source,
        device_id=device_id,
        ip=ip,
        metadata=metadata,
        timestamp=timestamp
    )
    
    emit_event(event)
    
    return event
