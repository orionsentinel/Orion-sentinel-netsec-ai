#!/usr/bin/env python3
"""
Log Injector for Orion Sentinel Development Mode

Reads sample data files and pushes them to Loki for testing and development.
Supports Suricata EVE JSON, Pi-hole DNS logs, and threat intel matches.
"""

import json
import os
import time
import requests
from datetime import datetime
from typing import Dict, List

# Configuration from environment
LOKI_URL = os.environ.get("LOKI_URL", "http://localhost:3100")
SAMPLES_DIR = os.environ.get("SAMPLES_DIR", "/samples")
INJECT_INTERVAL = int(os.environ.get("INJECT_INTERVAL", "5"))  # seconds
LOOP_ENABLED = os.environ.get("LOOP_ENABLED", "true").lower() == "true"


class LokiClient:
    """Simple Loki push client"""
    
    def __init__(self, url: str):
        self.url = url.rstrip("/")
        self.push_endpoint = f"{self.url}/loki/api/v1/push"
    
    def push_log(self, labels: Dict[str, str], message: str, timestamp_ns: int = None):
        """
        Push a single log line to Loki
        
        Args:
            labels: Dictionary of label key-value pairs
            message: Log message content
            timestamp_ns: Optional timestamp in nanoseconds (defaults to now)
        """
        if timestamp_ns is None:
            timestamp_ns = int(time.time() * 1e9)
        
        # Format labels as {key="value", ...}
        label_str = ", ".join([f'{k}="{v}"' for k, v in labels.items()])
        
        payload = {
            "streams": [
                {
                    "stream": labels,
                    "values": [
                        [str(timestamp_ns), message]
                    ]
                }
            ]
        }
        
        try:
            response = requests.post(
                self.push_endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Error pushing to Loki: {e}")


def inject_suricata_logs(client: LokiClient, filepath: str):
    """Inject Suricata EVE JSON logs"""
    print(f"Injecting Suricata logs from {filepath}")
    
    try:
        with open(filepath, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    event = json.loads(line)
                    
                    # Extract event type
                    event_type = event.get("event_type", "unknown")
                    
                    # Build labels
                    labels = {
                        "job": "suricata",
                        "host": "dev",
                        "event_type": event_type,
                        "source": "sample_data"
                    }
                    
                    # Add source IP if available
                    if "src_ip" in event:
                        labels["src_ip"] = event["src_ip"]
                    
                    # Parse timestamp from event
                    ts = event.get("timestamp")
                    if ts:
                        # Convert ISO timestamp to nanoseconds
                        dt = datetime.fromisoformat(ts.replace("+0000", "+00:00"))
                        timestamp_ns = int(dt.timestamp() * 1e9)
                    else:
                        timestamp_ns = int(time.time() * 1e9)
                    
                    # Push to Loki
                    client.push_log(labels, line, timestamp_ns)
                    print(f"  Pushed Suricata {event_type} event (line {line_num})")
                    
                except json.JSONDecodeError as e:
                    print(f"  Warning: Invalid JSON on line {line_num}: {e}")
                    continue
    
    except FileNotFoundError:
        print(f"  Warning: File not found: {filepath}")


def inject_pihole_logs(client: LokiClient, filepath: str):
    """Inject Pi-hole DNS logs"""
    print(f"Injecting Pi-hole DNS logs from {filepath}")
    
    try:
        with open(filepath, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Skip comments and empty lines
                if not line or line.startswith("#"):
                    continue
                
                # Parse line: timestamp client query_type domain response_type response
                parts = line.split()
                if len(parts) < 6:
                    continue
                
                timestamp_str = f"{parts[0]} {parts[1]}"
                client_ip = parts[2]
                query_type = parts[3]
                domain = parts[4]
                response_type = parts[5]
                response = parts[6] if len(parts) > 6 else ""
                
                # Build labels
                labels = {
                    "job": "dns",
                    "host": "dev",
                    "client": client_ip,
                    "query_type": query_type,
                    "response_type": response_type,
                    "source": "sample_data"
                }
                
                # Format as structured log
                log_message = json.dumps({
                    "timestamp": timestamp_str,
                    "client": client_ip,
                    "query_type": query_type,
                    "domain": domain,
                    "response_type": response_type,
                    "response": response
                })
                
                # Parse timestamp
                try:
                    dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                    timestamp_ns = int(dt.timestamp() * 1e9)
                except ValueError:
                    timestamp_ns = int(time.time() * 1e9)
                
                # Push to Loki
                client.push_log(labels, log_message, timestamp_ns)
                print(f"  Pushed DNS query: {domain} from {client_ip} (line {line_num})")
    
    except FileNotFoundError:
        print(f"  Warning: File not found: {filepath}")


def inject_intel_matches(client: LokiClient, filepath: str):
    """Inject threat intel match events"""
    print(f"Injecting threat intel matches from {filepath}")
    
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        for idx, match in enumerate(data, 1):
            # Build labels
            labels = {
                "job": "threat_intel",
                "host": "dev",
                "source": match.get("source", "unknown"),
                "threat_type": match.get("threat_type", "unknown"),
                "severity": match.get("severity", "unknown"),
                "source_data": "sample_data"
            }
            
            # Parse timestamp
            ts = match.get("timestamp")
            if ts:
                dt = datetime.fromisoformat(ts.replace("+0000", "+00:00"))
                timestamp_ns = int(dt.timestamp() * 1e9)
            else:
                timestamp_ns = int(time.time() * 1e9)
            
            # Push to Loki
            log_message = json.dumps(match)
            client.push_log(labels, log_message, timestamp_ns)
            print(f"  Pushed intel match: {match.get('indicator_value')} ({idx}/{len(data)})")
    
    except FileNotFoundError:
        print(f"  Warning: File not found: {filepath}")
    except json.JSONDecodeError as e:
        print(f"  Warning: Invalid JSON in {filepath}: {e}")


def main():
    """Main injection loop"""
    print("=" * 60)
    print("Orion Sentinel Log Injector")
    print("=" * 60)
    print(f"Loki URL: {LOKI_URL}")
    print(f"Samples directory: {SAMPLES_DIR}")
    print(f"Inject interval: {INJECT_INTERVAL}s")
    print(f"Loop enabled: {LOOP_ENABLED}")
    print("=" * 60)
    
    client = LokiClient(LOKI_URL)
    
    # Wait for Loki to be ready
    print("\nWaiting for Loki to be ready...")
    for attempt in range(30):
        try:
            response = requests.get(f"{LOKI_URL}/ready", timeout=2)
            if response.status_code == 200:
                print("Loki is ready!")
                break
        except requests.RequestException:
            pass
        
        time.sleep(2)
    else:
        print("Warning: Could not confirm Loki is ready, proceeding anyway...")
    
    iteration = 0
    while True:
        iteration += 1
        print(f"\n{'=' * 60}")
        print(f"Injection iteration {iteration}")
        print(f"{'=' * 60}\n")
        
        # Inject Suricata logs
        suricata_file = os.path.join(SAMPLES_DIR, "suricata-eve.json")
        inject_suricata_logs(client, suricata_file)
        
        # Inject Pi-hole DNS logs
        pihole_file = os.path.join(SAMPLES_DIR, "pihole-dns.log")
        inject_pihole_logs(client, pihole_file)
        
        # Inject threat intel matches
        intel_file = os.path.join(SAMPLES_DIR, "intel_matches.json")
        inject_intel_matches(client, intel_file)
        
        print(f"\nIteration {iteration} complete.")
        
        if not LOOP_ENABLED:
            print("Loop disabled, exiting.")
            break
        
        print(f"Waiting {INJECT_INTERVAL} seconds before next iteration...\n")
        time.sleep(INJECT_INTERVAL)


if __name__ == "__main__":
    main()
