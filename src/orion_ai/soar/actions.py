"""
SOAR action executors for automated response.

This module implements concrete actions that can be triggered by playbooks.
All actions respect dry_run mode for safety.
"""

import logging
import os
from typing import Any, Dict, Optional

from .models import Action, ActionType, TriggeredAction

logger = logging.getLogger(__name__)

# Global dry-run mode from environment
SOAR_DRY_RUN = os.getenv("SOAR_DRY_RUN", "1").lower() in ("1", "true", "yes")


class ActionExecutor:
    """
    Executes SOAR actions with safety controls.
    
    Supports both dry-run simulation and actual execution.
    """

    def __init__(
        self,
        dry_run: bool = SOAR_DRY_RUN,
        pihole_url: Optional[str] = None,
        pihole_api_key: Optional[str] = None,
    ):
        """
        Initialize action executor.
        
        Args:
            dry_run: If True, only simulate actions without executing
            pihole_url: URL of Pi-hole instance for blocking
            pihole_api_key: API key for Pi-hole authentication
        """
        self.dry_run = dry_run
        self.pihole_url = pihole_url or os.getenv("PIHOLE_URL", "http://192.168.1.2")
        self.pihole_api_key = pihole_api_key or os.getenv("PIHOLE_API_KEY", "")
        
        if self.dry_run:
            logger.info("ActionExecutor initialized in DRY RUN mode - no actions will be executed")
        else:
            logger.warning("ActionExecutor initialized in LIVE mode - actions WILL be executed")

    def execute(self, triggered_action: TriggeredAction) -> TriggeredAction:
        """
        Execute a triggered action.
        
        Args:
            triggered_action: The action to execute
            
        Returns:
            Updated TriggeredAction with execution results
        """
        action = triggered_action.action
        action_type = action.action_type
        
        logger.info(
            f"{'[DRY RUN] ' if self.dry_run else ''}Executing action: {action_type} "
            f"from playbook {triggered_action.playbook_name}"
        )
        
        try:
            if action_type == ActionType.BLOCK_DOMAIN:
                result = self.execute_block_domain(
                    action.parameters.get("domain", ""),
                    action.parameters.get("reason", "SOAR automated block"),
                )
            elif action_type == ActionType.TAG_DEVICE:
                result = self.execute_tag_device(
                    action.parameters.get("device_ip", ""),
                    action.parameters.get("tag", ""),
                )
            elif action_type == ActionType.SEND_NOTIFICATION:
                result = self.execute_send_notification(
                    action.parameters.get("message", ""),
                    action.parameters.get("severity", "info"),
                )
            elif action_type == ActionType.LOG_EVENT:
                result = self.execute_log_event(action.parameters)
            elif action_type == ActionType.SIMULATE_ONLY:
                result = {"simulated": True, "parameters": action.parameters}
            else:
                raise ValueError(f"Unknown action type: {action_type}")
            
            triggered_action.executed = not self.dry_run
            triggered_action.success = True
            triggered_action.result = result
            
        except Exception as e:
            logger.error(f"Action execution failed: {e}", exc_info=True)
            triggered_action.executed = False
            triggered_action.success = False
            triggered_action.error_message = str(e)
            triggered_action.result = None
        
        return triggered_action

    def execute_block_domain(self, domain: str, reason: str = "") -> Dict[str, Any]:
        """
        Block a domain via Pi-hole.
        
        Args:
            domain: Domain to block
            reason: Reason for blocking (for logging)
            
        Returns:
            Result dictionary with status
        """
        if not domain:
            raise ValueError("Domain parameter is required")
        
        log_msg = f"{'[DRY RUN] Would block' if self.dry_run else 'Blocking'} domain: {domain}"
        if reason:
            log_msg += f" (Reason: {reason})"
        logger.info(log_msg)
        
        if self.dry_run:
            return {
                "action": "block_domain",
                "domain": domain,
                "reason": reason,
                "dry_run": True,
            }
        
        # TODO: Implement actual Pi-hole API call
        # from orion_ai.integrations.pihole import PiHoleClient
        # client = PiHoleClient(self.pihole_url, self.pihole_api_key)
        # result = client.add_to_blacklist(domain, comment=reason)
        # return result
        
        logger.warning(
            "Pi-hole integration not yet implemented - action simulated"
        )
        
        return {
            "action": "block_domain",
            "domain": domain,
            "reason": reason,
            "executed": False,
            "note": "TODO: Implement Pi-hole API integration",
        }

    def execute_tag_device(self, device_ip: str, tag: str) -> Dict[str, Any]:
        """
        Tag a device in the inventory.
        
        Args:
            device_ip: IP address of device
            tag: Tag to add to device
            
        Returns:
            Result dictionary with status
        """
        if not device_ip or not tag:
            raise ValueError("device_ip and tag parameters are required")
        
        logger.info(
            f"{'[DRY RUN] Would tag' if self.dry_run else 'Tagging'} "
            f"device {device_ip} with tag: {tag}"
        )
        
        if self.dry_run:
            return {
                "action": "tag_device",
                "device_ip": device_ip,
                "tag": tag,
                "dry_run": True,
            }
        
        # TODO: Implement inventory integration
        # from orion_ai.inventory.store import InventoryStore
        # store = InventoryStore()
        # device = store.get_device(device_ip)
        # if device and tag not in device.tags:
        #     device.tags.append(tag)
        #     store.upsert_device(device)
        # return {"tagged": True}
        
        logger.warning(
            "Inventory integration not yet fully implemented - action simulated"
        )
        
        return {
            "action": "tag_device",
            "device_ip": device_ip,
            "tag": tag,
            "executed": False,
            "note": "TODO: Implement inventory integration",
        }

    def execute_send_notification(
        self, message: str, severity: str = "info"
    ) -> Dict[str, Any]:
        """
        Send a notification via configured channel.
        
        Args:
            message: Notification message
            severity: Severity level (info, warning, critical)
            
        Returns:
            Result dictionary with status
        """
        if not message:
            raise ValueError("message parameter is required")
        
        logger.info(
            f"{'[DRY RUN] Would send' if self.dry_run else 'Sending'} "
            f"{severity.upper()} notification: {message}"
        )
        
        if self.dry_run:
            return {
                "action": "send_notification",
                "message": message,
                "severity": severity,
                "dry_run": True,
            }
        
        # TODO: Implement notification channels
        # Options: Signal, Telegram, Email, Webhook
        # For now, just log
        logger.warning(
            f"[NOTIFICATION] [{severity.upper()}] {message}"
        )
        
        return {
            "action": "send_notification",
            "message": message,
            "severity": severity,
            "executed": True,
            "channel": "logger",
            "note": "TODO: Implement Signal/Telegram/Email integration",
        }

    def execute_log_event(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Log an event (for audit/tracking).
        
        Args:
            parameters: Event parameters to log
            
        Returns:
            Result dictionary with status
        """
        logger.info(f"Logging SOAR event: {parameters}")
        
        # This action always executes, even in dry run
        return {
            "action": "log_event",
            "parameters": parameters,
            "executed": True,
        }


class ActionLogger:
    """
    Logs action execution to Loki or other backend.
    """

    def __init__(self, loki_url: Optional[str] = None):
        """
        Initialize action logger.
        
        Args:
            loki_url: URL of Loki instance for logging
        """
        self.loki_url = loki_url or os.getenv("LOKI_URL", "http://localhost:3100")

    def log_action(self, triggered_action: TriggeredAction) -> None:
        """
        Log a triggered action to Loki.
        
        Args:
            triggered_action: The action that was triggered/executed
        """
        # TODO: Implement Loki push API call
        # Format as JSON with labels: service=soar, stream=soar_action
        
        log_entry = {
            "playbook_id": triggered_action.playbook_id,
            "playbook_name": triggered_action.playbook_name,
            "action_type": triggered_action.action.action_type,
            "executed": triggered_action.executed,
            "success": triggered_action.success,
            "timestamp": triggered_action.timestamp.isoformat(),
            "event_type": triggered_action.event_ref.event_type,
            "error": triggered_action.error_message,
        }
        
        logger.info(f"SOAR Action Log: {log_entry}")
        
        # TODO: Push to Loki
        # POST to {loki_url}/loki/api/v1/push
        # with labels: {service="soar", stream="soar_action"}
