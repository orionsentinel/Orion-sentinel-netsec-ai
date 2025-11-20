"""
Inventory service - orchestrates device discovery and tracking.

Runs periodically to update device inventory from logs.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Optional

from orion_ai.core.events import emit_new_event
from orion_ai.core.models import EventType, EventSeverity
from orion_ai.inventory.collector import DeviceCollector
from orion_ai.inventory.store import DeviceStore

logger = logging.getLogger(__name__)


class InventoryService:
    """
    Service for managing device inventory.
    
    Periodically discovers devices from logs and emits new device events.
    """
    
    def __init__(
        self,
        interval_minutes: int = 10,
        lookback_minutes: int = 15,
        device_store: Optional[DeviceStore] = None,
        device_collector: Optional[DeviceCollector] = None
    ):
        """
        Initialize inventory service.
        
        Args:
            interval_minutes: How often to run discovery
            lookback_minutes: How far back to look for devices
            device_store: Device store instance
            device_collector: Device collector instance
        """
        self.interval_minutes = interval_minutes
        self.lookback_minutes = lookback_minutes
        self.store = device_store or DeviceStore()
        self.collector = device_collector or DeviceCollector(device_store=self.store)
        
        # Track known devices to detect new ones
        self.known_device_ids = set(d.device_id for d in self.store.list_devices())
        
        logger.info(
            f"Initialized InventoryService "
            f"(interval={interval_minutes}m, lookback={lookback_minutes}m)"
        )
    
    def run_once(self) -> int:
        """
        Run one iteration of device discovery.
        
        Returns:
            Number of new devices discovered
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=self.lookback_minutes)
        
        logger.info(f"Running device discovery from {start_time} to {end_time}")
        
        # Collect devices
        devices = self.collector.collect_from_logs(start_time, end_time)
        
        # Check for new devices
        new_device_count = 0
        for device in devices:
            if device.device_id not in self.known_device_ids:
                # New device discovered
                self._emit_new_device_event(device)
                self.known_device_ids.add(device.device_id)
                new_device_count += 1
                
                # Try to guess device type if not set
                if not device.guess_type:
                    guess_type = self.collector.guess_device_type(device)
                    if guess_type:
                        device.guess_type = guess_type
                        self.store.upsert_device(device)
        
        logger.info(
            f"Device discovery complete: {len(devices)} total, "
            f"{new_device_count} new"
        )
        
        return new_device_count
    
    def run_loop(self) -> None:
        """
        Run the inventory service in a continuous loop.
        
        This method blocks and runs indefinitely.
        """
        logger.info("Starting inventory service loop")
        
        while True:
            try:
                self.run_once()
            except Exception as e:
                logger.error(f"Inventory service iteration failed: {e}", exc_info=True)
            
            # Sleep until next interval
            logger.debug(f"Sleeping for {self.interval_minutes} minutes")
            time.sleep(self.interval_minutes * 60)
    
    def _emit_new_device_event(self, device) -> None:
        """Emit an event for a newly discovered device."""
        emit_new_event(
            event_type=EventType.NEW_DEVICE,
            severity=EventSeverity.INFO,
            title=f"New device discovered: {device.ip}",
            description=(
                f"A new device has been discovered on the network.\n"
                f"IP: {device.ip}\n"
                f"MAC: {device.mac or 'Unknown'}\n"
                f"Hostname: {device.hostname or 'Unknown'}\n"
                f"Type: {device.guess_type or 'Unknown'}"
            ),
            source="inventory",
            device_id=device.device_id,
            ip=device.ip,
            metadata={
                "mac": device.mac,
                "hostname": device.hostname,
                "guess_type": device.guess_type,
                "first_seen": device.first_seen.isoformat()
            }
        )
