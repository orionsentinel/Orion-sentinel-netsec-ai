"""
Device collector - discovers and updates devices from logs.

Reads NSM and DNS logs to discover and track network devices.
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

from orion_ai.core.models import Device
from orion_ai.core.loki_client import LokiClient
from orion_ai.inventory.store import DeviceStore

logger = logging.getLogger(__name__)


class DeviceCollector:
    """
    Collects device information from network logs.
    
    Discovers devices from:
    - Suricata flow records
    - DNS queries
    - Suricata alerts
    """
    
    def __init__(
        self,
        loki_client: Optional[LokiClient] = None,
        device_store: Optional[DeviceStore] = None
    ):
        """
        Initialize device collector.
        
        Args:
            loki_client: Loki client for reading logs
            device_store: Device store for persistence
        """
        self.loki = loki_client or LokiClient()
        self.store = device_store or DeviceStore()
        
        logger.info("Initialized DeviceCollector")
    
    def collect_from_logs(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Device]:
        """
        Collect devices from logs in time window.
        
        Args:
            start_time: Start of time window
            end_time: End of time window
            
        Returns:
            List of discovered/updated devices
        """
        discovered_devices: Dict[str, Device] = {}
        
        # Collect from Suricata flows
        try:
            flow_devices = self._collect_from_suricata_flows(start_time, end_time)
            for device in flow_devices:
                discovered_devices[device.device_id] = device
        except Exception as e:
            logger.error(f"Failed to collect from Suricata flows: {e}")
        
        # Collect from DNS logs
        try:
            dns_devices = self._collect_from_dns(start_time, end_time)
            for device in dns_devices:
                # Merge with existing if found
                if device.device_id in discovered_devices:
                    existing = discovered_devices[device.device_id]
                    if device.hostname and not existing.hostname:
                        existing.hostname = device.hostname
                    if device.last_seen > existing.last_seen:
                        existing.last_seen = device.last_seen
                else:
                    discovered_devices[device.device_id] = device
        except Exception as e:
            logger.error(f"Failed to collect from DNS logs: {e}")
        
        # Update store
        devices = list(discovered_devices.values())
        for device in devices:
            # Check if device exists in store
            existing = self.store.get_device_by_id(device.device_id)
            
            if existing:
                # Update last_seen and merge data
                device.first_seen = existing.first_seen
                device.tags = existing.tags or []
                device.guess_type = device.guess_type or existing.guess_type
                device.owner = existing.owner
            
            self.store.upsert_device(device)
        
        logger.info(f"Collected {len(devices)} devices from logs")
        return devices
    
    def _collect_from_suricata_flows(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Device]:
        """
        Collect devices from Suricata flow records.
        
        TODO: Adjust LogQL query based on actual Suricata log format.
        """
        # Query Suricata flows
        query = '{service="suricata", event_type="flow"}'
        
        try:
            logs = self.loki.query_range(query, start_time, end_time, limit=5000)
        except Exception:
            logger.warning("Failed to query Suricata flows, returning empty list")
            return []
        
        devices_by_ip: Dict[str, Device] = {}
        
        for log in logs:
            # Extract source IP
            src_ip = log.get("src_ip")
            if not src_ip or self._is_external_ip(src_ip):
                continue
            
            # Get or create device
            if src_ip not in devices_by_ip:
                device_id = DeviceStore.generate_device_id(src_ip)
                devices_by_ip[src_ip] = Device(
                    device_id=device_id,
                    ip=src_ip,
                    first_seen=log.get("_timestamp", datetime.now()),
                    last_seen=log.get("_timestamp", datetime.now())
                )
            else:
                # Update last_seen
                timestamp = log.get("_timestamp", datetime.now())
                if timestamp > devices_by_ip[src_ip].last_seen:
                    devices_by_ip[src_ip].last_seen = timestamp
        
        return list(devices_by_ip.values())
    
    def _collect_from_dns(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Device]:
        """
        Collect devices and hostnames from DNS logs.
        
        TODO: Adjust LogQL query based on actual DNS log format (Pi-hole/Unbound).
        """
        # Query DNS logs from Pi-hole
        query = '{service="pihole"} |= "query"'
        
        try:
            logs = self.loki.query_range(query, start_time, end_time, limit=5000)
        except Exception:
            logger.warning("Failed to query DNS logs, returning empty list")
            return []
        
        devices_by_ip: Dict[str, Device] = {}
        
        for log in logs:
            # Extract client IP from DNS query
            # Format varies, try to extract IP
            # TODO: Adjust based on actual log format
            client_ip = log.get("client_ip") or log.get("ip")
            
            if not client_ip or self._is_external_ip(client_ip):
                continue
            
            # Get or create device
            if client_ip not in devices_by_ip:
                device_id = DeviceStore.generate_device_id(client_ip)
                devices_by_ip[client_ip] = Device(
                    device_id=device_id,
                    ip=client_ip,
                    first_seen=log.get("_timestamp", datetime.now()),
                    last_seen=log.get("_timestamp", datetime.now())
                )
            else:
                timestamp = log.get("_timestamp", datetime.now())
                if timestamp > devices_by_ip[client_ip].last_seen:
                    devices_by_ip[client_ip].last_seen = timestamp
            
            # Try to extract hostname from reverse DNS if available
            # This is a placeholder - actual implementation depends on log format
            hostname = log.get("hostname") or log.get("client_name")
            if hostname and not devices_by_ip[client_ip].hostname:
                devices_by_ip[client_ip].hostname = hostname
        
        return list(devices_by_ip.values())
    
    def _is_external_ip(self, ip: str) -> bool:
        """
        Check if IP is external (not private/local).
        
        Args:
            ip: IP address to check
            
        Returns:
            True if external, False if internal
        """
        # Check for private IP ranges
        private_patterns = [
            r'^10\.',
            r'^172\.(1[6-9]|2[0-9]|3[01])\.',
            r'^192\.168\.',
            r'^127\.',
            r'^169\.254\.',
            r'^::1$',
            r'^fe80:',
            r'^fc00:',
            r'^fd00:',
        ]
        
        for pattern in private_patterns:
            if re.match(pattern, ip):
                return False
        
        return True
    
    def guess_device_type(self, device: Device) -> Optional[str]:
        """
        Guess device type from hostname and traffic patterns.
        
        Args:
            device: Device to analyze
            
        Returns:
            Guessed device type or None
            
        TODO: Implement heuristics based on:
        - Hostname patterns
        - Traffic patterns
        - Port usage
        - DNS queries
        """
        if not device.hostname:
            return None
        
        hostname_lower = device.hostname.lower()
        
        # Simple heuristics based on hostname
        if any(x in hostname_lower for x in ['iphone', 'ipad', 'android', 'mobile']):
            return "phone"
        elif any(x in hostname_lower for x in ['tv', 'roku', 'chromecast', 'appletv']):
            return "TV"
        elif any(x in hostname_lower for x in ['nas', 'synology', 'qnap']):
            return "NAS"
        elif any(x in hostname_lower for x in ['laptop', 'macbook', 'thinkpad']):
            return "laptop"
        elif any(x in hostname_lower for x in ['desktop', 'pc', 'imac']):
            return "desktop"
        elif any(x in hostname_lower for x in ['iot', 'sensor', 'camera', 'doorbell']):
            return "iot"
        elif any(x in hostname_lower for x in ['printer', 'scanner']):
            return "printer"
        
        return "unknown"
