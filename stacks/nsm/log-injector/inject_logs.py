#!/usr/bin/env python3
"""
Log Injector for Orion Sentinel Development Mode

Reads sample log files and injects them into Loki for testing and development.
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, List

import requests

# Configuration from environment
LOKI_URL = os.getenv("LOKI_URL", "http://loki:3100")
SAMPLES_DIR = os.getenv("SAMPLES_DIR", "/samples")
INJECT_INTERVAL = int(os.getenv("INJECT_INTERVAL", "30"))  # seconds
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("log-injector")


class LokiClient:
    """Simple Loki push API client"""
    
    def __init__(self, url: str):
        self.url = url.rstrip("/")
        self.push_url = f"{self.url}/loki/api/v1/push"
    
    def push_logs(self, streams: List[Dict]) -> bool:
        """
        Push log streams to Loki
        
        Args:
            streams: List of stream objects with labels and values
        
        Returns:
            True if successful, False otherwise
        """
        payload = {"streams": streams}
        
        try:
            response = requests.post(
                self.push_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to push logs to Loki: {e}")
            return False


def read_suricata_samples(filepath: str) -> List[str]:
    """Read Suricata EVE JSON samples (NDJSON format)"""
    logs = []
    try:
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    logs.append(line)
        logger.info(f"Loaded {len(logs)} Suricata events from {filepath}")
    except Exception as e:
        logger.error(f"Error reading Suricata samples: {e}")
    return logs


def read_pihole_samples(filepath: str) -> List[str]:
    """Read Pi-hole DNS log samples"""
    logs = []
    try:
        with open(filepath, "r") as f:
            logs = [line.strip() for line in f if line.strip()]
        logger.info(f"Loaded {len(logs)} Pi-hole DNS entries from {filepath}")
    except Exception as e:
        logger.error(f"Error reading Pi-hole samples: {e}")
    return logs


def read_intel_samples(filepath: str) -> List[Dict]:
    """Read threat intelligence match samples"""
    try:
        with open(filepath, "r") as f:
            intel = json.load(f)
        logger.info(f"Loaded {len(intel)} threat intel matches from {filepath}")
        return intel
    except Exception as e:
        logger.error(f"Error reading intel samples: {e}")
        return []


def create_loki_stream(job: str, labels: Dict[str, str], entries: List[str]) -> Dict:
    """
    Create a Loki stream object
    
    Args:
        job: Job name (e.g., "suricata", "pihole")
        labels: Additional labels for the stream
        entries: Log entries to include
    
    Returns:
        Stream object for Loki push API
    """
    base_labels = {"job": job, "environment": "dev"}
    base_labels.update(labels)
    
    # Convert entries to Loki format: [[timestamp_ns, line], ...]
    now_ns = str(int(time.time() * 1e9))
    values = [[now_ns, entry] for entry in entries]
    
    return {
        "stream": base_labels,
        "values": values
    }


def inject_samples(loki: LokiClient):
    """Main injection loop - reads samples and pushes to Loki"""
    
    # File paths
    suricata_file = os.path.join(SAMPLES_DIR, "suricata-eve.json")
    pihole_file = os.path.join(SAMPLES_DIR, "pihole-dns.log")
    intel_file = os.path.join(SAMPLES_DIR, "intel_matches.json")
    
    logger.info("Starting log injection cycle...")
    
    streams = []
    
    # Inject Suricata logs
    if os.path.exists(suricata_file):
        suricata_logs = read_suricata_samples(suricata_file)
        if suricata_logs:
            stream = create_loki_stream(
                job="suricata",
                labels={"level": "info", "source": "sample"},
                entries=suricata_logs
            )
            streams.append(stream)
    else:
        logger.warning(f"Suricata sample file not found: {suricata_file}")
    
    # Inject Pi-hole logs
    if os.path.exists(pihole_file):
        pihole_logs = read_pihole_samples(pihole_file)
        if pihole_logs:
            stream = create_loki_stream(
                job="pihole",
                labels={"level": "info", "source": "sample"},
                entries=pihole_logs
            )
            streams.append(stream)
    else:
        logger.warning(f"Pi-hole sample file not found: {pihole_file}")
    
    # Inject threat intel matches
    if os.path.exists(intel_file):
        intel_matches = read_intel_samples(intel_file)
        if intel_matches:
            # Convert to JSON strings
            intel_logs = [json.dumps(match) for match in intel_matches]
            stream = create_loki_stream(
                job="threat-intel",
                labels={"level": "warning", "source": "sample"},
                entries=intel_logs
            )
            streams.append(stream)
    else:
        logger.warning(f"Intel sample file not found: {intel_file}")
    
    # Push all streams to Loki
    if streams:
        total_entries = sum(len(s["values"]) for s in streams)
        logger.info(f"Pushing {len(streams)} streams with {total_entries} total entries to Loki")
        
        if loki.push_logs(streams):
            logger.info("✓ Successfully injected sample logs")
        else:
            logger.error("✗ Failed to inject sample logs")
    else:
        logger.warning("No sample data to inject")


def wait_for_loki(loki_url: str, max_retries: int = 30, delay: int = 2):
    """Wait for Loki to be ready"""
    ready_url = f"{loki_url.rstrip('/')}/ready"
    
    logger.info(f"Waiting for Loki at {loki_url}...")
    
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(ready_url, timeout=5)
            if response.status_code == 200:
                logger.info("✓ Loki is ready!")
                return True
        except requests.exceptions.RequestException:
            pass
        
        if attempt < max_retries:
            logger.debug(f"Loki not ready yet (attempt {attempt}/{max_retries}), retrying in {delay}s...")
            time.sleep(delay)
    
    logger.error(f"✗ Loki did not become ready after {max_retries} attempts")
    return False


def main():
    """Main entry point"""
    logger.info("Orion Sentinel Log Injector - Development Mode")
    logger.info(f"Loki URL: {LOKI_URL}")
    logger.info(f"Samples directory: {SAMPLES_DIR}")
    logger.info(f"Injection interval: {INJECT_INTERVAL}s")
    
    # Wait for Loki to be ready
    if not wait_for_loki(LOKI_URL):
        logger.error("Loki is not available. Exiting.")
        return 1
    
    # Create Loki client
    loki = LokiClient(LOKI_URL)
    
    # Continuous injection loop
    logger.info("Starting continuous log injection...")
    
    try:
        while True:
            inject_samples(loki)
            logger.info(f"Sleeping for {INJECT_INTERVAL}s before next injection...")
            time.sleep(INJECT_INTERVAL)
    
    except KeyboardInterrupt:
        logger.info("Received interrupt signal. Shutting down...")
        return 0
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
