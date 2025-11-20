"""
Host log data models.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class HostEventType(str, Enum):
    """Types of host events."""

    FILE_CREATED = "file_created"
    FILE_MODIFIED = "file_modified"
    FILE_DELETED = "file_deleted"
    PROCESS_STARTED = "process_started"
    PROCESS_TERMINATED = "process_terminated"
    NETWORK_CONNECTION = "network_connection"
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    REGISTRY_CHANGE = "registry_change"  # Windows
    PACKAGE_INSTALLED = "package_installed"
    PACKAGE_REMOVED = "package_removed"
    SERVICE_STARTED = "service_started"
    SERVICE_STOPPED = "service_stopped"
    GENERIC = "generic"


class HostEventSeverity(str, Enum):
    """Severity levels for host events."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class HostEvent(BaseModel):
    """
    Normalized host event from endpoint agents.
    
    This model provides a unified representation of events from
    various sources (Wazuh, osquery, syslog, etc.).
    """

    hostname: str = Field(..., description="Hostname of the endpoint")
    event_type: HostEventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Event-specific details",
    )
    severity: HostEventSeverity = HostEventSeverity.LOW
    source: str = Field(..., description="Source agent (wazuh, osquery, syslog, etc.)")
    
    # Optional fields
    user: Optional[str] = Field(None, description="User associated with event")
    process: Optional[str] = Field(None, description="Process name")
    pid: Optional[int] = Field(None, description="Process ID")
    file_path: Optional[str] = Field(None, description="File path if applicable")
    ip_address: Optional[str] = Field(None, description="IP address if applicable")
    
    # Correlation
    related_alerts: list[str] = Field(
        default_factory=list,
        description="IDs of related alerts/events",
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "hostname": "workstation-01",
                "event_type": "process_started",
                "timestamp": "2025-01-15T10:30:00Z",
                "details": {
                    "command_line": "/usr/bin/python3 suspicious_script.py",
                    "parent_process": "bash",
                },
                "severity": "medium",
                "source": "osquery",
                "user": "john",
                "process": "python3",
                "pid": 12345,
            }
        }
