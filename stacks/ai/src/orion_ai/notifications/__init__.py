"""
Notifications module.

Handles sending notifications via various providers (email, webhook, etc.).
"""

from orion_ai.notifications.models import Notification, NotificationSeverity
from orion_ai.notifications.dispatcher import NotificationDispatcher
from orion_ai.notifications.providers import (
    EmailProvider,
    WebhookProvider,
    NotificationProvider,
)

__all__ = [
    "Notification",
    "NotificationSeverity",
    "NotificationDispatcher",
    "EmailProvider",
    "WebhookProvider",
    "NotificationProvider",
]
