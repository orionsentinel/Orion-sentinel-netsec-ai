"""
Change analysis and detection.
"""

import logging
from typing import List
from uuid import uuid4

from .models import Baseline, ChangeEvent, ChangeType

logger = logging.getLogger(__name__)


class ChangeAnalyzer:
    """
    Analyzes differences between baselines to detect changes.
    """

    def compare_baselines(
        self, previous: Baseline, current: Baseline
    ) -> List[ChangeEvent]:
        """
        Compare two baselines and generate change events.
        
        Args:
            previous: Previous baseline
            current: Current baseline
            
        Returns:
            List of detected changes
        """
        changes: List[ChangeEvent] = []
        
        # Detect new devices
        previous_ips = set(previous.device_ips)
        current_ips = set(current.device_ips)
        
        new_devices = current_ips - previous_ips
        for ip in new_devices:
            changes.append(
                ChangeEvent(
                    change_id=str(uuid4()),
                    change_type=ChangeType.NEW_DEVICE,
                    entity=ip,
                    entity_type="device",
                    old_value=None,
                    new_value=ip,
                    details={"first_seen_in_baseline": current.snapshot_id},
                    risk_level="medium",
                    baseline_id=current.snapshot_id,
                )
            )
        
        # Detect disappeared devices
        disappeared_devices = previous_ips - current_ips
        for ip in disappeared_devices:
            changes.append(
                ChangeEvent(
                    change_id=str(uuid4()),
                    change_type=ChangeType.DEVICE_DISAPPEARED,
                    entity=ip,
                    entity_type="device",
                    old_value=ip,
                    new_value=None,
                    details={"last_seen_in_baseline": previous.snapshot_id},
                    risk_level="low",
                    baseline_id=current.snapshot_id,
                )
            )
        
        # Detect per-device changes
        for ip in previous_ips & current_ips:
            device_changes = self._compare_device_baselines(
                ip, 
                previous.device_baselines.get(ip, {}),
                current.device_baselines.get(ip, {}),
                current.snapshot_id
            )
            changes.extend(device_changes)
        
        logger.info(
            f"Detected {len(changes)} changes between {previous.snapshot_id} "
            f"and {current.snapshot_id}"
        )
        
        return changes

    def _compare_device_baselines(
        self, device_ip: str, previous: dict, current: dict, baseline_id: str
    ) -> List[ChangeEvent]:
        """
        Compare device-specific baselines.
        
        Args:
            device_ip: IP of device
            previous: Previous device baseline data
            current: Current device baseline data
            baseline_id: ID of current baseline
            
        Returns:
            List of changes for this device
        """
        changes = []
        
        # New ports
        prev_ports = set(previous.get("observed_ports", []))
        curr_ports = set(current.get("observed_ports", []))
        new_ports = curr_ports - prev_ports
        
        if new_ports:
            changes.append(
                ChangeEvent(
                    change_id=str(uuid4()),
                    change_type=ChangeType.NEW_PORT_FOR_DEVICE,
                    entity=device_ip,
                    entity_type="device",
                    old_value=list(prev_ports),
                    new_value=list(curr_ports),
                    details={"new_ports": list(new_ports)},
                    risk_level=self._assess_port_risk(new_ports),
                    baseline_id=baseline_id,
                )
            )
        
        # New domains
        prev_domains = set(previous.get("observed_domains", []))
        curr_domains = set(current.get("observed_domains", []))
        new_domains = curr_domains - prev_domains
        
        if new_domains:
            changes.append(
                ChangeEvent(
                    change_id=str(uuid4()),
                    change_type=ChangeType.NEW_DOMAIN_FOR_DEVICE,
                    entity=device_ip,
                    entity_type="device",
                    old_value=list(prev_domains)[:10],  # Truncate for readability
                    new_value=list(curr_domains)[:10],
                    details={"new_domains": list(new_domains)[:20]},
                    risk_level="low",
                    baseline_id=baseline_id,
                )
            )
        
        # Risk score changes
        prev_risk = previous.get("risk_score", 0.0)
        curr_risk = current.get("risk_score", 0.0)
        
        if curr_risk > prev_risk + 0.2:  # Significant increase
            changes.append(
                ChangeEvent(
                    change_id=str(uuid4()),
                    change_type=ChangeType.RISK_SCORE_INCREASED,
                    entity=device_ip,
                    entity_type="device",
                    old_value=prev_risk,
                    new_value=curr_risk,
                    details={"increase": curr_risk - prev_risk},
                    risk_level="high" if curr_risk > 0.7 else "medium",
                    baseline_id=baseline_id,
                )
            )
        
        return changes

    def _assess_port_risk(self, ports: set) -> str:
        """
        Assess risk level of new ports.
        
        Args:
            ports: Set of new ports
            
        Returns:
            Risk level string
        """
        # High-risk ports
        high_risk_ports = {22, 23, 3389, 1433, 3306, 5432, 6379, 27017}
        
        if ports & high_risk_ports:
            return "high"
        
        # Medium-risk: any service port
        if any(p < 1024 for p in ports):
            return "medium"
        
        return "low"
