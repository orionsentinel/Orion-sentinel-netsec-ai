"""
Notification data models.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any


class NotificationSeverity(str, Enum):
    """Severity levels for notifications."""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class Notification:
    """
    Notification message to be sent via providers.
    
    Attributes:
        subject: Notification subject/title
        message: Notification body/content
        severity: Severity level
        tags: Optional tags for categorization
        metadata: Additional notification data
        timestamp: When notification was created
    """
    subject: str
    message: str
    severity: NotificationSeverity = NotificationSeverity.INFO
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "subject": self.subject,
            "message": self.message,
            "severity": self.severity.value,
            "tags": self.tags,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }
