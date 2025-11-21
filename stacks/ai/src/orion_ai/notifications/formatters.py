"""
Notification formatters - convert events to human-readable notifications.
"""

import logging
from typing import Optional, Dict, Any

from orion_ai.core.models import Event, EventSeverity
from orion_ai.notifications.models import Notification, NotificationSeverity

logger = logging.getLogger(__name__)


def event_to_notification(
    event: Event,
    include_device_info: bool = True,
    include_ti_context: bool = True
) -> Notification:
    """
    Convert a security event to a notification.
    
    Builds a human-readable notification from an event, including:
    - Event details (type, severity, description)
    - Device information (IP, tags)
    - Threat intelligence context (IOC matches, sources)
    - Risk scores and reasons
    
    Args:
        event: Event to convert
        include_device_info: Include device details in message
        include_ti_context: Include threat intel context if available
        
    Returns:
        Notification instance
    """
    # Map event severity to notification severity
    severity_map = {
        EventSeverity.INFO: NotificationSeverity.INFO,
        EventSeverity.WARNING: NotificationSeverity.WARNING,
        EventSeverity.CRITICAL: NotificationSeverity.CRITICAL,
    }
    severity = severity_map.get(event.severity, NotificationSeverity.INFO)
    
    # Build subject
    subject = event.title
    
    # Build message body
    message_parts = [event.description]
    
    # Add device information
    if include_device_info and (event.device_id or event.ip):
        device_info = []
        if event.ip:
            device_info.append(f"IP: {event.ip}")
        if event.device_id:
            device_info.append(f"Device: {event.device_id}")
        
        if device_info:
            message_parts.append("\nDevice Information:")
            message_parts.append(" | ".join(device_info))
    
    # Add threat intelligence context
    if include_ti_context and event.metadata:
        ti_context = _extract_ti_context(event.metadata)
        if ti_context:
            message_parts.append("\nThreat Intelligence:")
            message_parts.append(ti_context)
    
    # Add risk score if available
    risk_score = event.metadata.get("risk_score") if event.metadata else None
    if risk_score is not None:
        message_parts.append(f"\nRisk Score: {risk_score:.2f}")
    
    # Add reasons if available
    reasons = event.metadata.get("reasons") if event.metadata else None
    if reasons and isinstance(reasons, list):
        message_parts.append("\nReasons:")
        for reason in reasons:
            message_parts.append(f"  • {reason}")
    
    # Build tags
    tags = []
    tags.append(event.event_type.value)
    if event.source:
        tags.append(event.source)
    
    return Notification(
        subject=subject,
        message="\n".join(message_parts),
        severity=severity,
        tags=tags,
        metadata=event.metadata or {},
        timestamp=event.timestamp
    )


def _extract_ti_context(metadata: Dict[str, Any]) -> Optional[str]:
    """
    Extract threat intelligence context from event metadata.
    
    Args:
        metadata: Event metadata dictionary
        
    Returns:
        Formatted TI context string or None
    """
    ti_parts = []
    
    # Check for IOC matches
    ioc_matches = metadata.get("ioc_matches", [])
    if ioc_matches:
        if isinstance(ioc_matches, list):
            for match in ioc_matches:
                if isinstance(match, dict):
                    source = match.get("source", "Unknown")
                    ioc_type = match.get("type", "")
                    value = match.get("value", "")
                    ti_parts.append(f"  • Matched {ioc_type}: {value} (source: {source})")
        else:
            ti_parts.append(f"  • IOC matches detected: {ioc_matches}")
    
    # Check for TI sources
    ti_sources = metadata.get("ti_sources", [])
    if ti_sources and isinstance(ti_sources, list):
        sources_str = ", ".join(ti_sources)
        ti_parts.append(f"  • Sources: {sources_str}")
    
    # Check for malware family
    malware_family = metadata.get("malware_family")
    if malware_family:
        ti_parts.append(f"  • Malware Family: {malware_family}")
    
    # Check for threat type
    threat_type = metadata.get("threat_type")
    if threat_type:
        ti_parts.append(f"  • Threat Type: {threat_type}")
    
    return "\n".join(ti_parts) if ti_parts else None


def build_soar_notification(
    event: Event,
    playbook_name: str,
    actions_taken: list[str],
    dry_run: bool = False
) -> Notification:
    """
    Build a notification for SOAR playbook execution.
    
    Args:
        event: Event that triggered the playbook
        playbook_name: Name of the playbook executed
        actions_taken: List of action descriptions
        dry_run: Whether this was a dry-run execution
        
    Returns:
        Notification instance
    """
    # Build subject
    prefix = "[DRY RUN] " if dry_run else ""
    subject = f"{prefix}SOAR: {playbook_name}"
    
    # Build message
    message_parts = [
        f"Playbook '{playbook_name}' was triggered.",
        f"\nTriggering Event: {event.title}",
        event.description,
    ]
    
    if event.ip:
        message_parts.append(f"\nDevice IP: {event.ip}")
    
    if actions_taken:
        mode = "would be taken" if dry_run else "taken"
        message_parts.append(f"\nActions {mode}:")
        for action in actions_taken:
            message_parts.append(f"  • {action}")
    
    # Map event severity to notification severity
    severity_map = {
        EventSeverity.INFO: NotificationSeverity.INFO,
        EventSeverity.WARNING: NotificationSeverity.WARNING,
        EventSeverity.CRITICAL: NotificationSeverity.CRITICAL,
    }
    severity = severity_map.get(event.severity, NotificationSeverity.WARNING)
    
    return Notification(
        subject=subject,
        message="\n".join(message_parts),
        severity=severity,
        tags=["soar", playbook_name, "dry_run" if dry_run else "executed"],
        metadata={
            "playbook": playbook_name,
            "event_id": event.event_id,
            "dry_run": dry_run
        },
        timestamp=event.timestamp
    )
