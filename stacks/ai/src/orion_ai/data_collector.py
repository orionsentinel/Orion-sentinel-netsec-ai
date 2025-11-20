"""
Data Collector for Model Training

Collects and stores raw network/DNS data for training baseline models.
Run this for 7-30 days BEFORE training models to establish network baseline.
"""

import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import gzip

from orion_ai.config import get_config
from orion_ai.log_reader import LokiLogReader
from orion_ai.feature_extractor import FeatureExtractor

logger = logging.getLogger(__name__)


class DataCollector:
    """
    Collects and stores raw data for model training.
    
    Data is stored in compressed JSONL format with daily rotation.
    This provides the baseline data needed for training custom models.
    """
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize data collector.
        
        Args:
            output_dir: Directory to store collected data (default: /data/training)
        """
        self.config = get_config()
        self.log_reader = LokiLogReader()
        self.feature_extractor = FeatureExtractor()
        
        # Default output directory
        if output_dir is None:
            output_dir = Path("/data/training")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        self.device_dir = self.output_dir / "device_features"
        self.domain_dir = self.output_dir / "domain_features"
        self.raw_dir = self.output_dir / "raw_logs"
        
        self.device_dir.mkdir(exist_ok=True)
        self.domain_dir.mkdir(exist_ok=True)
        self.raw_dir.mkdir(exist_ok=True)
        
        logger.info(f"Initialized DataCollector with output_dir: {self.output_dir}")
    
    def collect_device_data(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> int:
        """
        Collect device behavioral data for training.
        
        Extracts features per device and stores them for later training.
        
        Args:
            start_time: Start of collection window (default: now - window_minutes)
            end_time: End of collection window (default: now)
            
        Returns:
            Number of device records collected
        """
        # Default time window
        if end_time is None:
            end_time = datetime.now()
        if start_time is None:
            window_minutes = self.config.detection.device_window_minutes
            start_time = end_time - timedelta(minutes=window_minutes)
        
        logger.info(
            f"Collecting device data for window: {start_time} to {end_time}"
        )
        
        try:
            # Read logs from Loki
            suricata_events = self.log_reader.get_suricata_events(start_time, end_time)
            dns_events = self.log_reader.get_dns_events(start_time, end_time)
            
            logger.info(
                f"Retrieved {len(suricata_events)} Suricata events, "
                f"{len(dns_events)} DNS events"
            )
            
            # Extract features per device
            device_features = self.feature_extractor.extract_device_features(
                suricata_events, dns_events
            )
            
            if not device_features:
                logger.warning("No device features extracted")
                return 0
            
            # Store features
            date_str = end_time.strftime("%Y-%m-%d")
            output_file = self.device_dir / f"device_features_{date_str}.jsonl.gz"
            
            records_written = 0
            with gzip.open(output_file, "at", encoding="utf-8") as f:
                for device_ip, features in device_features.items():
                    record = {
                        "timestamp": end_time.isoformat(),
                        "device_ip": device_ip,
                        "window_start": start_time.isoformat(),
                        "window_end": end_time.isoformat(),
                        "features": features.to_dict(),
                        "feature_vector": features.to_array().tolist()
                    }
                    f.write(json.dumps(record) + "\n")
                    records_written += 1
            
            logger.info(
                f"Collected {records_written} device records to {output_file}"
            )
            return records_written
            
        except Exception as e:
            logger.error(f"Failed to collect device data: {e}", exc_info=True)
            return 0
    
    def collect_domain_data(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> int:
        """
        Collect domain data for training.
        
        Extracts features per unique domain for risk scoring training.
        
        Args:
            start_time: Start of collection window
            end_time: End of collection window
            
        Returns:
            Number of domain records collected
        """
        # Default time window
        if end_time is None:
            end_time = datetime.now()
        if start_time is None:
            window_minutes = self.config.detection.domain_window_minutes
            start_time = end_time - timedelta(minutes=window_minutes)
        
        logger.info(
            f"Collecting domain data for window: {start_time} to {end_time}"
        )
        
        try:
            # Read DNS events
            dns_events = self.log_reader.get_dns_events(start_time, end_time)
            
            logger.info(f"Retrieved {len(dns_events)} DNS events")
            
            if not dns_events:
                logger.warning("No DNS events found")
                return 0
            
            # Extract unique domains
            unique_domains = set()
            for event in dns_events:
                domain = event.get("domain") or event.get("query")
                if domain:
                    unique_domains.add(domain)
            
            logger.info(f"Found {len(unique_domains)} unique domains")
            
            # Extract features per domain
            date_str = end_time.strftime("%Y-%m-%d")
            output_file = self.domain_dir / f"domain_features_{date_str}.jsonl.gz"
            
            records_written = 0
            with gzip.open(output_file, "at", encoding="utf-8") as f:
                for domain in unique_domains:
                    features = self.feature_extractor.extract_domain_features(domain)
                    
                    record = {
                        "timestamp": end_time.isoformat(),
                        "domain": domain,
                        "features": features.to_dict(),
                        "feature_vector": features.to_array().tolist()
                    }
                    f.write(json.dumps(record) + "\n")
                    records_written += 1
            
            logger.info(
                f"Collected {records_written} domain records to {output_file}"
            )
            return records_written
            
        except Exception as e:
            logger.error(f"Failed to collect domain data: {e}", exc_info=True)
            return 0
    
    def collect_raw_logs(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, int]:
        """
        Collect raw logs for analysis and debugging.
        
        Stores raw Suricata and DNS events without feature extraction.
        Useful for later re-processing or custom analysis.
        
        Args:
            start_time: Start of collection window
            end_time: End of collection window
            
        Returns:
            Dict with counts of collected logs
        """
        # Default time window
        if end_time is None:
            end_time = datetime.now()
        if start_time is None:
            start_time = end_time - timedelta(hours=1)
        
        logger.info(
            f"Collecting raw logs for window: {start_time} to {end_time}"
        )
        
        counts = {"suricata": 0, "dns": 0}
        date_str = end_time.strftime("%Y-%m-%d")
        
        try:
            # Collect Suricata events
            suricata_events = self.log_reader.get_suricata_events(start_time, end_time)
            if suricata_events:
                output_file = self.raw_dir / f"suricata_{date_str}.jsonl.gz"
                with gzip.open(output_file, "at", encoding="utf-8") as f:
                    for event in suricata_events:
                        f.write(json.dumps(event) + "\n")
                        counts["suricata"] += 1
                logger.info(f"Collected {counts['suricata']} Suricata events")
            
            # Collect DNS events
            dns_events = self.log_reader.get_dns_events(start_time, end_time)
            if dns_events:
                output_file = self.raw_dir / f"dns_{date_str}.jsonl.gz"
                with gzip.open(output_file, "at", encoding="utf-8") as f:
                    for event in dns_events:
                        f.write(json.dumps(event) + "\n")
                        counts["dns"] += 1
                logger.info(f"Collected {counts['dns']} DNS events")
            
        except Exception as e:
            logger.error(f"Failed to collect raw logs: {e}", exc_info=True)
        
        return counts
    
    def get_collection_stats(self) -> Dict:
        """
        Get statistics on collected data.
        
        Returns:
            Dict with file counts, sizes, date ranges
        """
        stats = {
            "device_files": len(list(self.device_dir.glob("*.jsonl.gz"))),
            "domain_files": len(list(self.domain_dir.glob("*.jsonl.gz"))),
            "raw_files": len(list(self.raw_dir.glob("*.jsonl.gz"))),
            "total_size_mb": 0,
            "oldest_data": None,
            "newest_data": None
        }
        
        # Calculate total size
        for f in self.output_dir.rglob("*.jsonl.gz"):
            stats["total_size_mb"] += f.stat().st_size / (1024 * 1024)
        
        # Find date range from filenames
        dates = []
        for f in self.output_dir.rglob("*_????-??-??.jsonl.gz"):
            try:
                date_str = f.stem.split("_")[-1]
                dates.append(datetime.strptime(date_str, "%Y-%m-%d"))
            except (ValueError, IndexError):
                continue
        
        if dates:
            stats["oldest_data"] = min(dates).strftime("%Y-%m-%d")
            stats["newest_data"] = max(dates).strftime("%Y-%m-%d")
            stats["collection_days"] = (max(dates) - min(dates)).days + 1
        
        return stats
