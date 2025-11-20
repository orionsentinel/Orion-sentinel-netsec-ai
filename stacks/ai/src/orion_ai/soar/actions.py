"""
SOAR action handlers - execute triggered actions.
"""

import logging
import os
from typing import Optional

from orion_ai.inventory.store import DeviceStore
from orion_ai.notifications.dispatcher import send_notification
from orion_ai.notifications.models import Notification, NotificationSeverity
from orion_ai.pihole_client import PiHoleClient
from orion_ai.soar.models import Action, ActionType, TriggeredAction

logger = logging.getLogger(__name__)


class ActionHandler:
    """
    Handles execution of SOAR actions.
    
    Executes different action types with proper error handling and logging.
    """
    
    def __init__(
        self,
        global_dry_run: bool = None,
        device_store: Optional[DeviceStore] = None,
        pihole_client: Optional[PiHoleClient] = None
    ):
        """
        Initialize action handler.
        
        Args:
            global_dry_run: Global dry-run flag (from env SOAR_DRY_RUN)
            device_store: Device store for tagging
            pihole_client: Pi-hole client for blocking
        """
        if global_dry_run is None:
            global_dry_run = os.getenv("SOAR_DRY_RUN", "false").lower() == "true"
        
        self.global_dry_run = global_dry_run
        self.device_store = device_store or DeviceStore()
        self.pihole_client = pihole_client or PiHoleClient()
        
        logger.info(f"Initialized ActionHandler (global_dry_run={global_dry_run})")
    
    def execute(self, triggered_action: TriggeredAction, dry_run: bool = False) -> bool:
        """
        Execute a triggered action.
        
        Args:
            triggered_action: Action to execute
            dry_run: Playbook-level dry-run flag
            
        Returns:
            True if successful, False otherwise
        """
        # Check if we should actually execute
        should_execute = not (self.global_dry_run or dry_run)
        
        action = triggered_action.action
        
        try:
            if action.type == ActionType.BLOCK_DOMAIN:
                success = self._handle_block_domain(action, should_execute)
            elif action.type == ActionType.TAG_DEVICE:
                success = self._handle_tag_device(action, should_execute)
            elif action.type == ActionType.SEND_NOTIFICATION:
                success = self._handle_send_notification(action, should_execute)
            elif action.type == ActionType.SIMULATE_ONLY:
                success = self._handle_simulate(action)
            elif action.type == ActionType.LOG_EVENT:
                success = self._handle_log_event(action, should_execute)
            else:
                logger.error(f"Unknown action type: {action.type}")
                triggered_action.error = f"Unknown action type: {action.type}"
                return False
            
            # Update triggered action record
            triggered_action.executed = should_execute
            triggered_action.success = success
            
            return success
            
        except Exception as e:
            logger.error(f"Action execution failed: {e}", exc_info=True)
            triggered_action.executed = should_execute
            triggered_action.success = False
            triggered_action.error = str(e)
            return False
    
    def _handle_block_domain(self, action: Action, execute: bool) -> bool:
        """Handle BLOCK_DOMAIN action."""
        domain = action.params.get("domain")
        
        if not domain:
            logger.error("BLOCK_DOMAIN action missing 'domain' parameter")
            return False
        
        if execute:
            logger.info(f"Blocking domain via Pi-hole: {domain}")
            # TODO: Implement actual Pi-hole blocking
            # This would use pihole_client to add domain to blocklist
            # For now, just log
            logger.warning("Pi-hole blocking not yet implemented")
            return True
        else:
            logger.info(f"[DRY RUN] Would block domain: {domain}")
            return True
    
    def _handle_tag_device(self, action: Action, execute: bool) -> bool:
        """Handle TAG_DEVICE action."""
        device_id = action.params.get("device_id")
        tag = action.params.get("tag")
        
        if not device_id or not tag:
            logger.error("TAG_DEVICE action missing 'device_id' or 'tag' parameter")
            return False
        
        if execute:
            logger.info(f"Tagging device {device_id} with '{tag}'")
            success = self.device_store.tag_device(device_id, tag)
            return success
        else:
            logger.info(f"[DRY RUN] Would tag device {device_id} with '{tag}'")
            return True
    
    def _handle_send_notification(self, action: Action, execute: bool) -> bool:
        """Handle SEND_NOTIFICATION action."""
        subject = action.params.get("subject", "Security Alert")
        message = action.params.get("message", "")
        severity = action.params.get("severity", "INFO")
        
        if not message:
            logger.error("SEND_NOTIFICATION action missing 'message' parameter")
            return False
        
        # Map severity string to enum
        try:
            severity_enum = NotificationSeverity(severity)
        except ValueError:
            logger.warning(f"Invalid severity '{severity}', using INFO")
            severity_enum = NotificationSeverity.INFO
        
        if execute:
            logger.info(f"Sending notification: {subject}")
            notification = Notification(
                subject=subject,
                message=message,
                severity=severity_enum
            )
            success = send_notification(notification)
            return success
        else:
            logger.info(f"[DRY RUN] Would send notification: {subject}")
            return True
    
    def _handle_simulate(self, action: Action) -> bool:
        """Handle SIMULATE_ONLY action (always dry-run)."""
        message = action.params.get("message", "Simulated action")
        logger.info(f"[SIMULATE] {message}")
        return True
    
    def _handle_log_event(self, action: Action, execute: bool) -> bool:
        """Handle LOG_EVENT action."""
        message = action.params.get("message", "")
        level = action.params.get("level", "INFO").upper()
        
        if execute or True:  # Always log, even in dry-run
            log_func = getattr(logger, level.lower(), logger.info)
            log_func(f"[SOAR] {message}")
            return True
        
        return True
