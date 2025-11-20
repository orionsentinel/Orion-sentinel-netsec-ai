"""
Notification providers for sending notifications via different channels.
"""

import logging
import os
import smtplib
from abc import ABC, abstractmethod
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import requests

from orion_ai.notifications.models import Notification

logger = logging.getLogger(__name__)


class NotificationProvider(ABC):
    """Base class for notification providers."""
    
    @abstractmethod
    def send(self, notification: Notification) -> bool:
        """
        Send a notification.
        
        Args:
            notification: Notification to send
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def is_enabled(self) -> bool:
        """Check if provider is properly configured and enabled."""
        pass


class EmailProvider(NotificationProvider):
    """
    Email notification provider using SMTP.
    
    Configuration via environment variables:
        NOTIFY_SMTP_HOST: SMTP server hostname
        NOTIFY_SMTP_PORT: SMTP server port (default: 587)
        NOTIFY_SMTP_USER: SMTP username
        NOTIFY_SMTP_PASS: SMTP password
        NOTIFY_EMAIL_FROM: Sender email address
        NOTIFY_EMAIL_TO: Recipient email address (comma-separated for multiple)
        NOTIFY_SMTP_USE_TLS: Use TLS (default: true)
    """
    
    def __init__(self):
        """Initialize email provider from environment variables."""
        self.smtp_host = os.getenv("NOTIFY_SMTP_HOST", "")
        self.smtp_port = int(os.getenv("NOTIFY_SMTP_PORT", "587"))
        self.smtp_user = os.getenv("NOTIFY_SMTP_USER", "")
        self.smtp_pass = os.getenv("NOTIFY_SMTP_PASS", "")
        self.email_from = os.getenv("NOTIFY_EMAIL_FROM", "")
        self.email_to = os.getenv("NOTIFY_EMAIL_TO", "")
        self.use_tls = os.getenv("NOTIFY_SMTP_USE_TLS", "true").lower() == "true"
        
        if self.is_enabled():
            logger.info(
                f"EmailProvider configured: {self.smtp_host}:{self.smtp_port} "
                f"-> {self.email_to}"
            )
    
    def is_enabled(self) -> bool:
        """Check if email is properly configured."""
        return bool(
            self.smtp_host and 
            self.smtp_user and 
            self.smtp_pass and 
            self.email_from and 
            self.email_to
        )
    
    def send(self, notification: Notification) -> bool:
        """
        Send email notification.
        
        Args:
            notification: Notification to send
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_enabled():
            logger.warning("Email provider not properly configured, skipping")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[{notification.severity.value}] {notification.subject}"
            msg["From"] = self.email_from
            msg["To"] = self.email_to
            
            # Create plain text body
            text = f"""
Orion Sentinel Security Alert

Severity: {notification.severity.value}
Time: {notification.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
Tags: {', '.join(notification.tags) if notification.tags else 'None'}

{notification.message}
"""
            
            # Create HTML body
            severity_color = {
                "INFO": "#0066cc",
                "WARNING": "#ff9900",
                "CRITICAL": "#cc0000"
            }.get(notification.severity.value, "#0066cc")
            
            html = f"""
<html>
<head></head>
<body style="font-family: Arial, sans-serif;">
    <h2 style="color: {severity_color};">Orion Sentinel Security Alert</h2>
    <table style="border-collapse: collapse; width: 100%;">
        <tr>
            <td style="padding: 8px; font-weight: bold;">Severity:</td>
            <td style="padding: 8px; color: {severity_color};">{notification.severity.value}</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">Time:</td>
            <td style="padding: 8px;">{notification.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">Tags:</td>
            <td style="padding: 8px;">{', '.join(notification.tags) if notification.tags else 'None'}</td>
        </tr>
    </table>
    <div style="margin-top: 20px; padding: 15px; background-color: #f5f5f5; border-left: 4px solid {severity_color};">
        <pre style="white-space: pre-wrap; font-family: monospace;">{notification.message}</pre>
    </div>
</body>
</html>
"""
            
            # Attach parts
            msg.attach(MIMEText(text, "plain"))
            msg.attach(MIMEText(html, "html"))
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
            
            logger.info(f"Sent email notification: {notification.subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False


class WebhookProvider(NotificationProvider):
    """
    Webhook notification provider.
    
    Sends JSON POST requests to a configured webhook URL.
    
    Configuration via environment variables:
        NOTIFY_WEBHOOK_URL: Webhook endpoint URL
        NOTIFY_WEBHOOK_TOKEN: Optional authentication token (Bearer)
    """
    
    def __init__(self):
        """Initialize webhook provider from environment variables."""
        self.webhook_url = os.getenv("NOTIFY_WEBHOOK_URL", "")
        self.webhook_token = os.getenv("NOTIFY_WEBHOOK_TOKEN", "")
        
        if self.is_enabled():
            logger.info(f"WebhookProvider configured: {self.webhook_url}")
    
    def is_enabled(self) -> bool:
        """Check if webhook is properly configured."""
        return bool(self.webhook_url)
    
    def send(self, notification: Notification) -> bool:
        """
        Send webhook notification.
        
        Args:
            notification: Notification to send
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_enabled():
            logger.warning("Webhook provider not properly configured, skipping")
            return False
        
        try:
            # Build headers
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Orion-Sentinel/1.0"
            }
            
            if self.webhook_token:
                headers["Authorization"] = f"Bearer {self.webhook_token}"
            
            # Send POST request
            response = requests.post(
                self.webhook_url,
                json=notification.to_dict(),
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            logger.info(f"Sent webhook notification: {notification.subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")
            return False


class SignalProvider(NotificationProvider):
    """
    Signal messenger notification provider.
    
    TODO: Implement Signal integration using signal-cli or similar.
    This is a stub for future implementation.
    """
    
    def is_enabled(self) -> bool:
        """Check if Signal is configured."""
        # TODO: Implement Signal configuration check
        return False
    
    def send(self, notification: Notification) -> bool:
        """Send Signal notification."""
        logger.warning("Signal notifications not yet implemented")
        return False


class TelegramProvider(NotificationProvider):
    """
    Telegram notification provider.
    
    TODO: Implement Telegram bot integration.
    This is a stub for future implementation.
    """
    
    def is_enabled(self) -> bool:
        """Check if Telegram is configured."""
        # TODO: Implement Telegram configuration check
        return False
    
    def send(self, notification: Notification) -> bool:
        """Send Telegram notification."""
        logger.warning("Telegram notifications not yet implemented")
        return False
