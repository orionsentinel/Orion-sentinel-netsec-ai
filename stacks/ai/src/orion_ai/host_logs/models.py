"""
Host logs models.

TODO: Implement models for different log types.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class HostLogEvent:
    """
    Represents a normalized host log event.
    
    TODO: Implement normalization from various log formats.
    """
    timestamp: datetime
    hostname: str
    log_type: str  # syslog, auth, etc.
    severity: str
    message: str
    source_ip: Optional[str] = None
