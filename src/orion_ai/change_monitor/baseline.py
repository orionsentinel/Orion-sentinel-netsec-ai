"""
Baseline creation for change detection.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any

from .models import Baseline, DeviceBaseline

logger = logging.getLogger(__name__)


class BaselineBuilder:
    """
    Builds baseline snapshots from historical data.
    """

    def build_global_baseline(
        self, period_days: int = 7, end_time: Optional[datetime] = None
    ) -> Baseline:
        """
        Build a baseline snapshot of the entire network.
        
        Args:
            period_days: Number of days to include in baseline
            end_time: End time for baseline period (default: now)
            
        Returns:
            Baseline snapshot
        """
        if end_time is None:
            end_time = datetime.utcnow()
        
        start_time = end_time - timedelta(days=period_days)
        
        # TODO: Query Loki for events in time range
        # TODO: Query inventory for device list
        
        baseline = Baseline(
            snapshot_id=f"baseline_{end_time.strftime('%Y_%m_%d_%H%M%S')}",
            timestamp=datetime.utcnow(),
            period_start=start_time,
            period_end=end_time,
        )
        
        logger.info(
            f"Built global baseline for {start_time} to {end_time} "
            f"({baseline.total_devices} devices)"
        )
        
        return baseline

    def build_device_baseline(
        self, device_ip: str, period_days: int = 7, end_time: Optional[datetime] = None
    ) -> DeviceBaseline:
        """
        Build baseline for a single device.
        
        Args:
            device_ip: IP address of device
            period_days: Number of days to include
            end_time: End time for baseline period
            
        Returns:
            Device baseline
        """
        if end_time is None:
            end_time = datetime.utcnow()
        
        # TODO: Query Loki for device-specific events
        # - Suricata events where src_ip or dest_ip = device_ip
        # - DNS queries from device_ip
        # Extract:
        # - All ports used
        # - All domains queried
        # - All destination IPs
        # - Protocols used
        # - Average connection/byte counts
        
        baseline = DeviceBaseline(
            device_ip=device_ip,
            snapshot_timestamp=datetime.utcnow(),
        )
        
        logger.debug(f"Built baseline for device {device_ip}")
        
        return baseline

    def save_baseline(self, baseline: Baseline, storage_path: str = "/data/baselines") -> None:
        """
        Save baseline to storage.
        
        Args:
            baseline: Baseline to save
            storage_path: Directory to save baselines
        """
        # TODO: Save to JSON file or database
        import json
        from pathlib import Path
        
        Path(storage_path).mkdir(parents=True, exist_ok=True)
        filepath = Path(storage_path) / f"{baseline.snapshot_id}.json"
        
        with open(filepath, "w") as f:
            json.dump(baseline.dict(), f, indent=2, default=str)
        
        logger.info(f"Saved baseline to {filepath}")

    def load_baseline(self, baseline_id: str, storage_path: str = "/data/baselines") -> Optional[Baseline]:
        """
        Load baseline from storage.
        
        Args:
            baseline_id: ID of baseline to load
            storage_path: Directory where baselines are stored
            
        Returns:
            Baseline or None if not found
        """
        import json
        from pathlib import Path
        
        filepath = Path(storage_path) / f"{baseline_id}.json"
        
        if not filepath.exists():
            logger.warning(f"Baseline {baseline_id} not found at {filepath}")
            return None
        
        with open(filepath, "r") as f:
            data = json.load(f)
        
        # Convert datetime strings back to datetime objects
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        data["period_start"] = datetime.fromisoformat(data["period_start"])
        data["period_end"] = datetime.fromisoformat(data["period_end"])
        
        return Baseline(**data)
