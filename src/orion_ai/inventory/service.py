"""
Inventory service for continuous device tracking.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import List

from .collector import DeviceCollector
from .fingerprinting import DeviceFingerprinter
from .models import Device, InventoryEvent
from .store import InventoryStore

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class InventoryService:
    """
    Service for continuous device inventory management.
    
    Periodically:
    1. Collects device data from logs
    2. Updates inventory
    3. Fingerprints new/updated devices
    4. Emits inventory events
    """

    def __init__(
        self,
        store: InventoryStore,
        collector: DeviceCollector,
        fingerprinter: DeviceFingerprinter,
        loki_url: str = "http://localhost:3100",
        poll_interval: int = 300,
    ):
        """
        Initialize inventory service.
        
        Args:
            store: Inventory store
            collector: Device collector
            fingerprinter: Device fingerprinter
            loki_url: Loki URL
            poll_interval: Poll interval in seconds
        """
        self.store = store
        self.collector = collector
        self.fingerprinter = fingerprinter
        self.loki_url = loki_url
        self.poll_interval = poll_interval
        self.running = False

    async def collect_and_update_devices(self) -> List[Device]:
        """
        Collect device data and update inventory.
        
        Returns:
            List of updated devices
        """
        # TODO: Fetch events from Loki
        # Query for Suricata alerts, DNS queries, etc. from last poll_interval
        events = []  # Placeholder
        
        # Get current inventory
        existing_devices = {d.ip: d for d in self.store.list_devices()}
        
        # Collect device info from events
        updated_devices = self.collector.collect_from_loki_events(events, existing_devices)
        
        # Save updated devices
        for device in updated_devices:
            self.store.upsert_device(device)
        
        return updated_devices

    async def fingerprint_devices(self, devices: List[Device]) -> List[Device]:
        """
        Fingerprint devices to determine their type.
        
        Args:
            devices: Devices to fingerprint
            
        Returns:
            Fingerprinted devices
        """
        fingerprinted = []
        
        for device in devices:
            # Skip if already fingerprinted
            if device.guess_type and device.guess_type != "unknown":
                continue
            
            try:
                fingerprinted_device = self.fingerprinter.fingerprint_device(device)
                
                # Suggest tags
                suggested_tags = self.fingerprinter.suggest_tags(fingerprinted_device)
                for tag in suggested_tags:
                    if tag not in fingerprinted_device.tags:
                        fingerprinted_device.tags.append(tag)
                
                self.store.upsert_device(fingerprinted_device)
                fingerprinted.append(fingerprinted_device)
                
            except Exception as e:
                logger.error(f"Failed to fingerprint device {device.ip}: {e}")
        
        return fingerprinted

    async def check_new_devices(self, lookback_hours: int = 24) -> List[Device]:
        """
        Check for new devices.
        
        Args:
            lookback_hours: How far back to look for new devices
            
        Returns:
            List of new devices
        """
        since = datetime.utcnow() - timedelta(hours=lookback_hours)
        new_devices = self.store.list_new_devices_since(since)
        
        if new_devices:
            logger.info(f"Found {len(new_devices)} new devices in last {lookback_hours}h")
            
            # TODO: Emit inventory events to Loki
            for device in new_devices:
                event = InventoryEvent(
                    event_type="new_device",
                    device_ip=device.ip,
                    details={
                        "mac": device.mac,
                        "hostname": device.hostname,
                        "guess_type": device.guess_type,
                    },
                )
                logger.info(f"New device event: {event.dict()}")
                # TODO: Push to Loki
        
        return new_devices

    async def run_once(self) -> None:
        """Run one iteration of inventory update."""
        try:
            logger.debug("Running inventory update")
            
            # Collect and update devices
            updated_devices = await self.collect_and_update_devices()
            
            if updated_devices:
                logger.info(f"Updated {len(updated_devices)} devices")
                
                # Fingerprint new/unknown devices
                await self.fingerprint_devices(updated_devices)
            
            # Check for new devices
            await self.check_new_devices(lookback_hours=24)
            
            # Log stats
            stats = self.store.get_stats()
            logger.info(f"Inventory stats: {stats}")
            
        except Exception as e:
            logger.error(f"Error in inventory update: {e}", exc_info=True)

    async def run(self) -> None:
        """Run inventory service continuously."""
        self.running = True
        logger.info(f"Starting inventory service (poll interval: {self.poll_interval}s)")
        
        iteration = 0
        while self.running:
            iteration += 1
            logger.debug(f"Inventory iteration {iteration}")
            
            await self.run_once()
            
            await asyncio.sleep(self.poll_interval)

    def stop(self) -> None:
        """Stop inventory service."""
        logger.info("Stopping inventory service")
        self.running = False


def main() -> None:
    """Main entry point for inventory service."""
    loki_url = os.getenv("LOKI_URL", "http://localhost:3100")
    poll_interval = int(os.getenv("INVENTORY_POLL_INTERVAL", "300"))
    db_path = os.getenv("INVENTORY_DB_PATH", "/data/inventory.db")
    
    logger.info("=" * 60)
    logger.info("Orion Sentinel - Device Inventory Service")
    logger.info("=" * 60)
    logger.info(f"Loki URL: {loki_url}")
    logger.info(f"Poll Interval: {poll_interval}s")
    logger.info(f"Database: {db_path}")
    logger.info("=" * 60)
    
    # Initialize components
    store = InventoryStore(db_path=db_path)
    collector = DeviceCollector()
    fingerprinter = DeviceFingerprinter()
    
    service = InventoryService(
        store=store,
        collector=collector,
        fingerprinter=fingerprinter,
        loki_url=loki_url,
        poll_interval=poll_interval,
    )
    
    try:
        asyncio.run(service.run())
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
        service.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
