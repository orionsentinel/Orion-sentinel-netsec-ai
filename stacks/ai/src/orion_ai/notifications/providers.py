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
    
    Uses signal-cli REST API or HTTP gateway for sending messages.
    
    Configuration via environment variables:
        NOTIFY_SIGNAL_ENABLED: Enable Signal notifications (true/false)
        NOTIFY_SIGNAL_API_URL: signal-cli REST API URL (e.g., http://localhost:8080)
        NOTIFY_SIGNAL_NUMBER: Sender phone number (e.g., +31612345678)
        NOTIFY_SIGNAL_RECIPIENTS: Comma-separated recipient numbers
    """
    
    def __init__(self):
        """Initialize Signal provider from environment variables."""
        self.enabled = os.getenv("NOTIFY_SIGNAL_ENABLED", "false").lower() == "true"
        self.api_url = os.getenv("NOTIFY_SIGNAL_API_URL", "http://localhost:8080")
        self.sender_number = os.getenv("NOTIFY_SIGNAL_NUMBER", "")
        recipients_str = os.getenv("NOTIFY_SIGNAL_RECIPIENTS", "")
        self.recipients = [r.strip() for r in recipients_str.split(",") if r.strip()]
        
        if self.is_enabled():
            logger.info(
                f"SignalProvider configured: {self.sender_number} -> "
                f"{len(self.recipients)} recipients"
            )
    
    def is_enabled(self) -> bool:
        """Check if Signal is configured."""
        return bool(
            self.enabled and 
            self.api_url and 
            self.sender_number and 
            self.recipients
        )
    
    def send(self, notification: Notification) -> bool:
        """
        Send Signal notification.
        
        Args:
            notification: Notification to send
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_enabled():
            logger.warning("Signal provider not properly configured, skipping")
            return False
        
        try:
            # Format message
            severity_emoji = {
                "INFO": "ℹ️",
                "WARNING": "⚠️",
                "CRITICAL": "🚨"
            }.get(notification.severity.value, "📢")
            
            message = f"""{severity_emoji} **Orion Sentinel Alert**

**{notification.subject}**
Severity: {notification.severity.value}
Time: {notification.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

{notification.message}

Tags: {', '.join(notification.tags) if notification.tags else 'None'}"""
            
            # Send to each recipient
            success_count = 0
            for recipient in self.recipients:
                try:
                    # signal-cli REST API v2 format
                    response = requests.post(
                        f"{self.api_url}/v2/send",
                        json={
                            "message": message,
                            "number": self.sender_number,
                            "recipients": [recipient]
                        },
                        headers={"Content-Type": "application/json"},
                        timeout=10
                    )
                    
                    if response.status_code == 201 or response.status_code == 200:
                        success_count += 1
                        logger.debug(f"Sent Signal message to {recipient}")
                    else:
                        logger.warning(
                            f"Failed to send Signal to {recipient}: "
                            f"HTTP {response.status_code}"
                        )
                except Exception as e:
                    logger.error(f"Failed to send Signal to {recipient}: {e}")
            
            if success_count > 0:
                logger.info(
                    f"Sent Signal notification to {success_count}/{len(self.recipients)} "
                    f"recipients: {notification.subject}"
                )
                return True
            else:
                logger.error("Failed to send Signal to any recipients")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send Signal notification: {e}")
            return False


class TelegramProvider(NotificationProvider):
    """
    Telegram notification provider using Bot API.
    
    Configuration via environment variables:
        NOTIFY_TELEGRAM_ENABLED: Enable Telegram notifications (true/false)
        NOTIFY_TELEGRAM_BOT_TOKEN: Telegram Bot API token
        NOTIFY_TELEGRAM_CHAT_ID: Chat ID or comma-separated chat IDs to send to
    """
    
    def __init__(self):
        """Initialize Telegram provider from environment variables."""
        self.enabled = os.getenv("NOTIFY_TELEGRAM_ENABLED", "false").lower() == "true"
        self.bot_token = os.getenv("NOTIFY_TELEGRAM_BOT_TOKEN", "")
        chat_ids_str = os.getenv("NOTIFY_TELEGRAM_CHAT_ID", "")
        self.chat_ids = [c.strip() for c in chat_ids_str.split(",") if c.strip()]
        
        if self.is_enabled():
            logger.info(
                f"TelegramProvider configured: bot -> {len(self.chat_ids)} chats"
            )
    
    def is_enabled(self) -> bool:
        """Check if Telegram is configured."""
        return bool(
            self.enabled and 
            self.bot_token and 
            self.chat_ids
        )
    
    def send(self, notification: Notification) -> bool:
        """
        Send Telegram notification.
        
        Args:
            notification: Notification to send
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_enabled():
            logger.warning("Telegram provider not properly configured, skipping")
            return False
        
        try:
            # Format message using Markdown
            severity_emoji = {
                "INFO": "ℹ️",
                "WARNING": "⚠️",
                "CRITICAL": "🚨"
            }.get(notification.severity.value, "📢")
            
            message = f"""{severity_emoji} **Orion Sentinel Alert**

*{notification.subject}*

**Severity:** {notification.severity.value}
**Time:** {notification.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

{notification.message}

**Tags:** {', '.join(notification.tags) if notification.tags else 'None'}"""
            
            # Send to each chat
            success_count = 0
            for chat_id in self.chat_ids:
                try:
                    # Telegram Bot API sendMessage endpoint
                    url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
                    
                    response = requests.post(
                        url,
                        json={
                            "chat_id": chat_id,
                            "text": message,
                            "parse_mode": "Markdown"
                        },
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        if result.get("ok"):
                            success_count += 1
                            logger.debug(f"Sent Telegram message to chat {chat_id}")
                        else:
                            logger.warning(
                                f"Telegram API error for chat {chat_id}: "
                                f"{result.get('description')}"
                            )
                    else:
                        logger.warning(
                            f"Failed to send Telegram to chat {chat_id}: "
                            f"HTTP {response.status_code}"
                        )
                except Exception as e:
                    logger.error(f"Failed to send Telegram to chat {chat_id}: {e}")
            
            if success_count > 0:
                logger.info(
                    f"Sent Telegram notification to {success_count}/{len(self.chat_ids)} "
                    f"chats: {notification.subject}"
                )
                return True
            else:
                logger.error("Failed to send Telegram to any chats")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            return False
