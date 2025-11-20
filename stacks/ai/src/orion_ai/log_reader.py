"""
Log reader for querying Suricata and DNS logs from Loki.

Provides abstraction layer for reading NSM and DNS events.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests

from orion_ai.config import get_config

logger = logging.getLogger(__name__)


class LokiLogReader:
    """
    Client for reading logs from Loki using LogQL queries.
    
    Attributes:
        base_url: Loki HTTP API base URL
        timeout: Request timeout in seconds
    """
    
    def __init__(self, base_url: Optional[str] = None, timeout: Optional[int] = None):
        """
        Initialize Loki log reader.
        
        Args:
            base_url: Loki API URL (default from config)
            timeout: Request timeout (default from config)
        """
        config = get_config()
        self.base_url = base_url or config.loki.url
        self.timeout = timeout or config.loki.timeout
        
        # Ensure base_url doesn't end with slash
        self.base_url = self.base_url.rstrip('/')
        
        logger.info(f"Initialized LokiLogReader with base_url={self.base_url}")
    
    def _query_range(
        self,
        query: str,
        start: datetime,
        end: datetime,
        limit: int = 5000
    ) -> List[Dict]:
        """
        Execute a LogQL range query.
        
        Args:
            query: LogQL query string
            start: Start time for query
            end: End time for query
            limit: Maximum number of results
            
        Returns:
            List of log entries as dictionaries
            
        Raises:
            requests.RequestException: If query fails
        """
        url = f"{self.base_url}/loki/api/v1/query_range"
        
        params = {
            "query": query,
            "start": int(start.timestamp() * 1e9),  # Nanoseconds
            "end": int(end.timestamp() * 1e9),
            "limit": limit
        }
        
        logger.debug(f"Executing Loki query: {query}")
        logger.debug(f"Time range: {start} to {end}")
        
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract log entries from Loki response
            entries = []
            if data.get("status") == "success":
                result = data.get("data", {}).get("result", [])
                for stream in result:
                    for value in stream.get("values", []):
                        # value is [timestamp_ns, log_line]
                        timestamp_ns, log_line = value
                        entries.append({
                            "timestamp": datetime.fromtimestamp(int(timestamp_ns) / 1e9),
                            "log": log_line,
                            "labels": stream.get("stream", {})
                        })
            
            logger.info(f"Retrieved {len(entries)} log entries from Loki")
            return entries
            
        except requests.RequestException as e:
            logger.error(f"Failed to query Loki: {e}")
            raise
    
    def get_suricata_flows(
        self,
        start: datetime,
        end: datetime,
        limit: int = 5000
    ) -> List[Dict]:
        """
        Get Suricata flow events for a time window.
        
        Args:
            start: Start time
            end: End time
            limit: Maximum results
            
        Returns:
            List of flow events
        """
        query = '{service="suricata", event_type="flow"}'
        return self._query_range(query, start, end, limit)
    
    def get_suricata_alerts(
        self,
        start: datetime,
        end: datetime,
        limit: int = 5000
    ) -> List[Dict]:
        """
        Get Suricata alert events for a time window.
        
        Args:
            start: Start time
            end: End time
            limit: Maximum results
            
        Returns:
            List of alert events
        """
        query = '{service="suricata", event_type="alert"}'
        return self._query_range(query, start, end, limit)
    
    def get_dns_queries(
        self,
        start: datetime,
        end: datetime,
        limit: int = 5000
    ) -> List[Dict]:
        """
        Get DNS query events from Suricata and Pi-hole.
        
        Args:
            start: Start time
            end: End time
            limit: Maximum results
            
        Returns:
            List of DNS query events
        """
        # Query both Suricata DNS events and Pi-hole logs
        suricata_query = '{service="suricata", event_type="dns"}'
        pihole_query = '{service="pihole"}'
        
        # Combine queries with logical OR
        combined_query = f'{suricata_query} or {pihole_query}'
        
        return self._query_range(combined_query, start, end, limit)
    
    def get_logs_by_device(
        self,
        device_ip: str,
        start: datetime,
        end: datetime,
        limit: int = 5000
    ) -> Dict[str, List[Dict]]:
        """
        Get all logs for a specific device (by IP).
        
        Args:
            device_ip: Device IP address
            start: Start time
            end: End time
            limit: Maximum results per log type
            
        Returns:
            Dictionary with keys: flows, alerts, dns_queries
        """
        result = {
            "flows": [],
            "alerts": [],
            "dns_queries": []
        }
        
        # Query flows for this device (as source)
        flow_query = f'{{service="suricata", event_type="flow"}} |= "{device_ip}"'
        result["flows"] = self._query_range(flow_query, start, end, limit)
        
        # Query alerts for this device
        alert_query = f'{{service="suricata", event_type="alert"}} |= "{device_ip}"'
        result["alerts"] = self._query_range(alert_query, start, end, limit)
        
        # Query DNS for this device
        dns_query = f'{{service="suricata", event_type="dns"}} |= "{device_ip}"'
        result["dns_queries"] = self._query_range(dns_query, start, end, limit)
        
        logger.info(
            f"Retrieved logs for device {device_ip}: "
            f"{len(result['flows'])} flows, "
            f"{len(result['alerts'])} alerts, "
            f"{len(result['dns_queries'])} DNS queries"
        )
        
        return result
    
    def get_recent_logs(
        self,
        minutes: int = 10,
        log_type: str = "all"
    ) -> List[Dict]:
        """
        Get recent logs for the last N minutes.
        
        Args:
            minutes: Number of minutes to look back
            log_type: Type of logs (all, flow, alert, dns)
            
        Returns:
            List of log entries
        """
        end = datetime.now()
        start = end - timedelta(minutes=minutes)
        
        if log_type == "flow":
            return self.get_suricata_flows(start, end)
        elif log_type == "alert":
            return self.get_suricata_alerts(start, end)
        elif log_type == "dns":
            return self.get_dns_queries(start, end)
        else:  # all
            query = '{service="suricata"}'
            return self._query_range(query, start, end)


# TODO: Add support for reading from local JSONL files for offline testing
class FileLogReader:
    """
    Reader for local log files (for testing without Loki).
    
    This is a stub implementation. Can be extended to read from
    local JSONL files for offline development/testing.
    """
    
    def __init__(self, log_dir: str):
        """
        Initialize file log reader.
        
        Args:
            log_dir: Directory containing log files
        """
        self.log_dir = log_dir
        logger.info(f"Initialized FileLogReader with log_dir={log_dir}")
    
    def get_suricata_flows(self, start: datetime, end: datetime) -> List[Dict]:
        """Get flows from file (stub)."""
        logger.warning("FileLogReader.get_suricata_flows not implemented")
        return []
    
    def get_dns_queries(self, start: datetime, end: datetime) -> List[Dict]:
        """Get DNS queries from file (stub)."""
        logger.warning("FileLogReader.get_dns_queries not implemented")
        return []
