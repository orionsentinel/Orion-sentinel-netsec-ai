"""
Loki client abstraction for querying and writing logs.

Provides a simple interface to Loki for reading logs via LogQL and writing
structured JSON logs with labels.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import requests
from requests.auth import HTTPBasicAuth

from orion_ai.core.config import get_config

logger = logging.getLogger(__name__)


class LokiClient:
    """
    Client for interacting with Grafana Loki.
    
    Provides methods for:
    - Pushing structured logs with labels
    - Querying logs using LogQL
    """
    
    def __init__(
        self,
        url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize Loki client.
        
        Args:
            url: Loki HTTP API URL (default: from config)
            username: Optional HTTP basic auth username
            password: Optional HTTP basic auth password
            timeout: Request timeout in seconds
        """
        config = get_config()
        self.url = url or config.loki.url
        self.username = username
        self.password = password
        self.timeout = timeout
        
        # Strip trailing slash
        self.url = self.url.rstrip('/')
        
        logger.info(f"Initialized LokiClient with URL: {self.url}")
    
    def _get_auth(self) -> Optional[HTTPBasicAuth]:
        """Get HTTP basic auth if credentials are provided."""
        if self.username and self.password:
            return HTTPBasicAuth(self.username, self.password)
        return None
    
    def push_log(
        self,
        labels: Dict[str, str],
        log: Dict[str, Any],
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        Push a structured JSON log to Loki.
        
        Args:
            labels: Label dictionary (e.g., {"stream": "events", "service": "ai"})
            log: Log data as dictionary (will be JSON-encoded)
            timestamp: Optional timestamp (default: now)
            
        Raises:
            requests.RequestException: If push fails
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # Convert timestamp to nanoseconds
        ts_ns = int(timestamp.timestamp() * 1e9)
        
        # Build labels string
        label_str = ",".join([f'{k}="{v}"' for k, v in labels.items()])
        
        # Build Loki push payload
        payload = {
            "streams": [
                {
                    "stream": labels,
                    "values": [
                        [str(ts_ns), json.dumps(log)]
                    ]
                }
            ]
        }
        
        try:
            response = requests.post(
                f"{self.url}/loki/api/v1/push",
                json=payload,
                auth=self._get_auth(),
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            logger.debug(f"Pushed log to Loki: {label_str}")
            
        except requests.RequestException as e:
            logger.error(f"Failed to push log to Loki: {e}")
            raise
    
    def query_range(
        self,
        query: str,
        start: datetime,
        end: datetime,
        limit: int = 1000,
        direction: str = "backward"
    ) -> List[Dict[str, Any]]:
        """
        Query logs from Loki using LogQL.
        
        Args:
            query: LogQL query string (e.g., '{stream="events"}')
            start: Start time
            end: End time
            limit: Maximum number of results
            direction: Query direction ("forward" or "backward")
            
        Returns:
            List of log entries as dictionaries
            
        Raises:
            requests.RequestException: If query fails
            
        Note:
            This is a basic implementation. Complex queries may need tuning.
            TODO: Add support for step parameter and metric queries.
        """
        params = {
            "query": query,
            "start": int(start.timestamp() * 1e9),
            "end": int(end.timestamp() * 1e9),
            "limit": limit,
            "direction": direction
        }
        
        try:
            response = requests.get(
                f"{self.url}/loki/api/v1/query_range",
                params=params,
                auth=self._get_auth(),
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Parse results
            results = []
            if data.get("data", {}).get("result"):
                for stream in data["data"]["result"]:
                    stream_labels = stream.get("stream", {})
                    values = stream.get("values", [])
                    
                    for value in values:
                        ts_ns, log_line = value
                        
                        # Try to parse as JSON
                        try:
                            log_data = json.loads(log_line)
                        except json.JSONDecodeError:
                            log_data = {"message": log_line}
                        
                        # Add metadata
                        log_data["_timestamp"] = datetime.fromtimestamp(int(ts_ns) / 1e9)
                        log_data["_labels"] = stream_labels
                        
                        results.append(log_data)
            
            logger.debug(f"Query returned {len(results)} results")
            return results
            
        except requests.RequestException as e:
            logger.error(f"Failed to query Loki: {e}")
            raise
    
    def query_labels(self, start: datetime, end: datetime) -> List[str]:
        """
        Get available labels in time range.
        
        Args:
            start: Start time
            end: End time
            
        Returns:
            List of label names
            
        TODO: Implement label querying for discovery.
        """
        # This is a placeholder for label discovery
        logger.warning("query_labels not fully implemented")
        return []
    
    def health_check(self) -> bool:
        """
        Check if Loki is reachable.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            response = requests.get(
                f"{self.url}/ready",
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Loki health check failed: {e}")
            return False
