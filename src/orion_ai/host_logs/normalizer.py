"""
Host log normalizers for different sources.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from .models import HostEvent, HostEventSeverity, HostEventType

logger = logging.getLogger(__name__)


class HostLogNormalizer:
    """
    Normalizes host logs from various sources into HostEvent format.
    """

    def normalize(self, raw_event: Dict[str, Any], source: str) -> Optional[HostEvent]:
        """
        Normalize a raw event based on its source.
        
        Args:
            raw_event: Raw event dictionary
            source: Source identifier (wazuh, osquery, syslog, etc.)
            
        Returns:
            Normalized HostEvent or None if unable to parse
        """
        try:
            if source == "wazuh":
                return self.normalize_wazuh(raw_event)
            elif source == "osquery":
                return self.normalize_osquery(raw_event)
            elif source == "syslog":
                return self.normalize_syslog(raw_event)
            else:
                return self.normalize_generic(raw_event, source)
        except Exception as e:
            logger.error(f"Failed to normalize event from {source}: {e}")
            return None

    def normalize_wazuh(self, event: Dict[str, Any]) -> Optional[HostEvent]:
        """
        Normalize Wazuh agent event.
        
        Wazuh event structure:
        {
            "agent": {"name": "hostname", ...},
            "rule": {"description": "...", "level": 5, ...},
            "data": {...},
            "timestamp": "...",
        }
        """
        hostname = event.get("agent", {}).get("name", "unknown")
        rule_level = event.get("rule", {}).get("level", 0)
        
        # Map Wazuh rule level to severity
        if rule_level >= 12:
            severity = HostEventSeverity.CRITICAL
        elif rule_level >= 7:
            severity = HostEventSeverity.HIGH
        elif rule_level >= 4:
            severity = HostEventSeverity.MEDIUM
        else:
            severity = HostEventSeverity.LOW
        
        # Determine event type from rule description
        # TODO: More sophisticated mapping
        event_type = HostEventType.GENERIC
        
        return HostEvent(
            hostname=hostname,
            event_type=event_type,
            timestamp=datetime.fromisoformat(event.get("timestamp", datetime.utcnow().isoformat())),
            details=event.get("data", {}),
            severity=severity,
            source="wazuh",
        )

    def normalize_osquery(self, event: Dict[str, Any]) -> Optional[HostEvent]:
        """
        Normalize osquery result.
        
        osquery event structure:
        {
            "name": "query_name",
            "hostIdentifier": "hostname",
            "unixTime": 1234567890,
            "columns": {...},
            "action": "added"
        }
        """
        hostname = event.get("hostIdentifier", "unknown")
        action = event.get("action", "")
        columns = event.get("columns", {})
        
        # Determine event type from query name and action
        event_type = self._map_osquery_event_type(event.get("name", ""), action, columns)
        
        return HostEvent(
            hostname=hostname,
            event_type=event_type,
            timestamp=datetime.fromtimestamp(event.get("unixTime", 0)),
            details=columns,
            severity=HostEventSeverity.LOW,
            source="osquery",
        )

    def normalize_syslog(self, event: Dict[str, Any]) -> Optional[HostEvent]:
        """
        Normalize syslog message.
        
        Syslog event structure:
        {
            "hostname": "...",
            "timestamp": "...",
            "severity": 3,
            "facility": "...",
            "message": "...",
        }
        """
        hostname = event.get("hostname", "unknown")
        syslog_severity = event.get("severity", 6)
        
        # Map syslog severity to our severity
        if syslog_severity <= 2:  # Emergency, Alert, Critical
            severity = HostEventSeverity.CRITICAL
        elif syslog_severity <= 4:  # Error, Warning
            severity = HostEventSeverity.HIGH
        elif syslog_severity == 5:  # Notice
            severity = HostEventSeverity.MEDIUM
        else:  # Informational, Debug
            severity = HostEventSeverity.LOW
        
        return HostEvent(
            hostname=hostname,
            event_type=HostEventType.GENERIC,
            timestamp=datetime.fromisoformat(event.get("timestamp", datetime.utcnow().isoformat())),
            details={"message": event.get("message", ""), "facility": event.get("facility")},
            severity=severity,
            source="syslog",
        )

    def normalize_generic(self, event: Dict[str, Any], source: str) -> HostEvent:
        """
        Generic normalization for unknown sources.
        
        Args:
            event: Raw event
            source: Source identifier
            
        Returns:
            Basic HostEvent
        """
        return HostEvent(
            hostname=event.get("hostname", event.get("host", "unknown")),
            event_type=HostEventType.GENERIC,
            timestamp=datetime.fromisoformat(
                event.get("timestamp", datetime.utcnow().isoformat())
            ),
            details=event,
            severity=HostEventSeverity.LOW,
            source=source,
        )

    def _map_osquery_event_type(
        self, query_name: str, action: str, columns: Dict
    ) -> HostEventType:
        """Map osquery query results to event types."""
        query_lower = query_name.lower()
        
        if "process" in query_lower:
            if action == "added":
                return HostEventType.PROCESS_STARTED
            elif action == "removed":
                return HostEventType.PROCESS_TERMINATED
        
        if "file" in query_lower:
            if action == "added":
                return HostEventType.FILE_CREATED
            elif action == "removed":
                return HostEventType.FILE_DELETED
            else:
                return HostEventType.FILE_MODIFIED
        
        if "package" in query_lower:
            if action == "added":
                return HostEventType.PACKAGE_INSTALLED
            elif action == "removed":
                return HostEventType.PACKAGE_REMOVED
        
        if "login" in query_lower or "auth" in query_lower:
            return HostEventType.LOGIN_SUCCESS
        
        return HostEventType.GENERIC
