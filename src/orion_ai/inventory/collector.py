"""
Device inventory data collection from logs.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Set

from .models import Device, DeviceActivity

logger = logging.getLogger(__name__)


class DeviceCollector:
    """
    Collects device information from various log sources.
    """

    def __init__(self):
        """Initialize device collector."""
        self.seen_ips: Set[str] = set()

    def collect_from_loki_events(
        self, events: List[Dict], existing_devices: Dict[str, Device]
    ) -> List[Device]:
        """
        Extract device information from Loki events.
        
        Args:
            events: Raw events from Loki (Suricata, DNS, etc.)
            existing_devices: Current inventory (ip -> Device)
            
        Returns:
            List of updated/new devices
        """
        updated_devices = []
        
        for event in events:
            # TODO: Parse different event types
            # - Suricata events: src_ip, dest_ip, src_port, dest_port, proto
            # - DNS events: client_ip, query_name
            # - Intel events: related IPs
            
            # Extract IPs from event
            ips = self._extract_ips_from_event(event)
            
            for ip in ips:
                if ip in existing_devices:
                    device = existing_devices[ip]
                    device.last_seen = datetime.utcnow()
                else:
                    device = Device(
                        ip=ip,
                        first_seen=datetime.utcnow(),
                        last_seen=datetime.utcnow(),
                    )
                
                # Update device with event information
                self._update_device_from_event(device, event)
                updated_devices.append(device)
        
        return updated_devices

    def _extract_ips_from_event(self, event: Dict) -> List[str]:
        """
        Extract IP addresses from an event.
        
        Args:
            event: Event dictionary
            
        Returns:
            List of IP addresses found
        """
        ips = []
        
        # Common field names for IPs
        ip_fields = [
            "src_ip", "dest_ip", "client_ip", "server_ip",
            "source_ip", "destination_ip", "ip", "host_ip",
        ]
        
        for field in ip_fields:
            if field in event:
                ip = event[field]
                if self._is_internal_ip(ip):
                    ips.append(ip)
        
        return ips

    def _is_internal_ip(self, ip: str) -> bool:
        """
        Check if IP is internal/private.
        
        Args:
            ip: IP address string
            
        Returns:
            True if internal IP
        """
        # Basic check for RFC1918 addresses
        # TODO: Use ipaddress module for proper validation
        parts = ip.split(".")
        if len(parts) != 4:
            return False
        
        try:
            first_octet = int(parts[0])
            second_octet = int(parts[1])
            
            # 10.0.0.0/8
            if first_octet == 10:
                return True
            
            # 172.16.0.0/12
            if first_octet == 172 and 16 <= second_octet <= 31:
                return True
            
            # 192.168.0.0/16
            if first_octet == 192 and second_octet == 168:
                return True
            
        except ValueError:
            return False
        
        return False

    def _update_device_from_event(self, device: Device, event: Dict) -> None:
        """
        Update device information based on event data.
        
        Args:
            device: Device to update
            event: Event containing device information
        """
        # Update MAC address if available
        if "mac" in event and not device.mac:
            device.mac = event["mac"]
        
        # Update hostname if available
        if "hostname" in event and not device.hostname:
            device.hostname = event["hostname"]
        
        # Track ports
        if "dest_port" in event:
            port = int(event["dest_port"])
            if port not in device.open_ports and len(device.open_ports) < 100:
                device.open_ports.append(port)
        
        # Track destinations (domains/IPs)
        if "query_name" in event:  # DNS query
            domain = event["query_name"]
            if domain not in device.common_destinations and len(device.common_destinations) < 50:
                device.common_destinations.append(domain)

    def build_device_activity(
        self, device_ip: str, events: List[Dict], period_start: datetime, period_end: datetime
    ) -> DeviceActivity:
        """
        Build activity summary for a device over a time period.
        
        Args:
            device_ip: IP address of device
            events: Events for this device in the time period
            period_start: Start of time period
            period_end: End of time period
            
        Returns:
            DeviceActivity summary
        """
        activity = DeviceActivity(
            device_ip=device_ip,
            time_period_start=period_start,
            time_period_end=period_end,
        )
        
        unique_dests = set()
        
        for event in events:
            # Count connections
            activity.connection_count += 1
            
            # Track unique destinations
            if "dest_ip" in event:
                unique_dests.add(event["dest_ip"])
            if "query_name" in event:
                unique_dests.add(event["query_name"])
            
            # Protocol counts
            proto = event.get("proto", "").lower()
            if proto == "tcp":
                activity.tcp_connections += 1
            elif proto == "udp":
                activity.udp_connections += 1
            elif proto == "icmp":
                activity.icmp_packets += 1
            
            # Event type counts
            event_type = event.get("event_type", "")
            if event_type == "alert":
                activity.suricata_alerts += 1
            elif "anomaly" in event_type:
                activity.ai_anomalies += 1
            elif event_type == "intel_match":
                activity.intel_matches += 1
            
            # DNS queries
            if "query_name" in event:
                activity.dns_queries += 1
        
        activity.unique_destinations = len(unique_dests)
        
        return activity
