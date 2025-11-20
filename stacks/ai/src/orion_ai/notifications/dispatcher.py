"""
Notification dispatcher - sends notifications via all enabled providers.
"""

import logging
from typing import List

from orion_ai.notifications.models import Notification
from orion_ai.notifications.providers import (
    EmailProvider,
    NotificationProvider,
    SignalProvider,
    TelegramProvider,
    WebhookProvider,
)

logger = logging.getLogger(__name__)


class NotificationDispatcher:
    """
    Dispatches notifications to all enabled providers.
    
    Manages multiple notification providers and sends notifications
    to all that are properly configured.
    """
    
    def __init__(self, providers: List[NotificationProvider] = None):
        """
        Initialize notification dispatcher.
        
        Args:
            providers: Optional list of providers (default: all built-in providers)
        """
        if providers is None:
            # Initialize all built-in providers
            providers = [
                EmailProvider(),
                WebhookProvider(),
                SignalProvider(),
                TelegramProvider(),
            ]
        
        self.providers = providers
        
        # Log enabled providers
        enabled = [p.__class__.__name__ for p in providers if p.is_enabled()]
        logger.info(f"NotificationDispatcher initialized with providers: {enabled}")
    
    def send_notification(self, notification: Notification) -> bool:
        """
        Send notification via all enabled providers.
        
        Args:
            notification: Notification to send
            
        Returns:
            True if at least one provider succeeded, False otherwise
        """
        success_count = 0
        enabled_count = 0
        
        for provider in self.providers:
            if not provider.is_enabled():
                continue
            
            enabled_count += 1
            
            try:
                if provider.send(notification):
                    success_count += 1
            except Exception as e:
                logger.error(
                    f"Provider {provider.__class__.__name__} failed: {e}",
                    exc_info=True
                )
        
        if enabled_count == 0:
            logger.warning("No notification providers enabled")
            return False
        
        logger.info(
            f"Notification sent via {success_count}/{enabled_count} providers: "
            f"{notification.subject}"
        )
        
        return success_count > 0
    
    def add_provider(self, provider: NotificationProvider) -> None:
        """
        Add a notification provider.
        
        Args:
            provider: Provider to add
        """
        self.providers.append(provider)
        logger.info(f"Added notification provider: {provider.__class__.__name__}")
    
    def get_enabled_providers(self) -> List[str]:
        """
        Get list of enabled provider names.
        
        Returns:
            List of enabled provider class names
        """
        return [p.__class__.__name__ for p in self.providers if p.is_enabled()]


# Global dispatcher instance
_dispatcher: NotificationDispatcher = None


def get_dispatcher() -> NotificationDispatcher:
    """
    Get or create the global notification dispatcher.
    
    Returns:
        NotificationDispatcher instance
    """
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = NotificationDispatcher()
    return _dispatcher


def send_notification(notification: Notification) -> bool:
    """
    Convenience function to send notification via global dispatcher.
    
    Args:
        notification: Notification to send
        
    Returns:
        True if at least one provider succeeded, False otherwise
    """
    dispatcher = get_dispatcher()
    return dispatcher.send_notification(notification)
