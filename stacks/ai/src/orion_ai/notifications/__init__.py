"""
Notifications module.

Handles sending notifications via various providers (email, webhook, Signal, Telegram).
"""

from orion_ai.notifications.models import Notification, NotificationSeverity
from orion_ai.notifications.dispatcher import NotificationDispatcher, send_notification
from orion_ai.notifications.providers import (
    EmailProvider,
    WebhookProvider,
    SignalProvider,
    TelegramProvider,
    NotificationProvider,
)
from orion_ai.notifications.formatters import (
    event_to_notification,
    build_soar_notification,
)

__all__ = [
    "Notification",
    "NotificationSeverity",
    "NotificationDispatcher",
    "send_notification",
    "EmailProvider",
    "WebhookProvider",
    "SignalProvider",
    "TelegramProvider",
    "NotificationProvider",
    "event_to_notification",
    "build_soar_notification",
]
