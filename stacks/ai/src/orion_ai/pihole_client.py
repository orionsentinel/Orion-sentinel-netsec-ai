"""
Pi-hole API client for domain blocking.

Provides interface to Pi-hole's HTTP API for adding/removing domains from blocklists.
"""

import logging
import time
from typing import Optional
import requests

from orion_ai.config import get_config

logger = logging.getLogger(__name__)


class PiHoleClient:
    """
    Client for Pi-hole HTTP API.
    
    Supports adding and removing domains from Pi-hole's blacklist.
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_token: Optional[str] = None,
        timeout: Optional[int] = None,
        retry_attempts: Optional[int] = None
    ):
        """
        Initialize Pi-hole API client.
        
        Args:
            base_url: Pi-hole API URL (default from config)
            api_token: API authentication token (default from config)
            timeout: Request timeout in seconds (default from config)
            retry_attempts: Number of retry attempts (default from config)
        """
        config = get_config()
        
        self.base_url = base_url or config.pihole.api_url
        self.api_token = api_token or config.pihole.api_token
        self.timeout = timeout or config.pihole.timeout
        self.retry_attempts = retry_attempts or config.pihole.retry_attempts
        
        # Remove trailing slash from base URL
        self.base_url = self.base_url.rstrip('/')
        
        if not self.api_token:
            logger.warning(
                "Pi-hole API token not configured. "
                "API calls will fail unless token is provided."
            )
        
        logger.info(f"Initialized PiHoleClient with base_url={self.base_url}")
    
    def add_domain(self, domain: str, comment: str = "") -> bool:
        """
        Add a domain to Pi-hole's blacklist.
        
        Args:
            domain: Domain name to block
            comment: Optional comment for the blocklist entry
            
        Returns:
            True if successful, False otherwise
        """
        if not self.api_token:
            logger.error("Cannot add domain: API token not configured")
            return False
        
        params = {
            "list": "black",
            "add": domain,
            "auth": self.api_token
        }
        
        if comment:
            params["comment"] = comment
        
        logger.info(f"Adding domain to Pi-hole blacklist: {domain}")
        
        for attempt in range(1, self.retry_attempts + 1):
            try:
                response = requests.get(
                    self.base_url,
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                # Check response for success
                # Pi-hole typically returns JSON with success indicator
                try:
                    data = response.json()
                    if "success" in data and data["success"]:
                        logger.info(f"Successfully added domain to blacklist: {domain}")
                        return True
                    else:
                        logger.warning(
                            f"Pi-hole returned non-success response for {domain}: {data}"
                        )
                        return False
                except ValueError:
                    # Response not JSON - check status code
                    if response.status_code == 200:
                        logger.info(f"Successfully added domain to blacklist: {domain}")
                        return True
                    else:
                        logger.warning(
                            f"Pi-hole returned status {response.status_code} for {domain}"
                        )
                        return False
                
            except requests.RequestException as e:
                logger.warning(
                    f"Attempt {attempt}/{self.retry_attempts} failed "
                    f"to add domain {domain}: {e}"
                )
                
                if attempt < self.retry_attempts:
                    # Exponential backoff
                    sleep_time = 2 ** attempt
                    logger.debug(f"Retrying in {sleep_time} seconds...")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"Failed to add domain {domain} after {self.retry_attempts} attempts")
                    return False
        
        return False
    
    def remove_domain(self, domain: str) -> bool:
        """
        Remove a domain from Pi-hole's blacklist.
        
        Args:
            domain: Domain name to unblock
            
        Returns:
            True if successful, False otherwise
        """
        if not self.api_token:
            logger.error("Cannot remove domain: API token not configured")
            return False
        
        params = {
            "list": "black",
            "sub": domain,
            "auth": self.api_token
        }
        
        logger.info(f"Removing domain from Pi-hole blacklist: {domain}")
        
        for attempt in range(1, self.retry_attempts + 1):
            try:
                response = requests.get(
                    self.base_url,
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                # Check response for success
                try:
                    data = response.json()
                    if "success" in data and data["success"]:
                        logger.info(f"Successfully removed domain from blacklist: {domain}")
                        return True
                    else:
                        logger.warning(
                            f"Pi-hole returned non-success response for {domain}: {data}"
                        )
                        return False
                except ValueError:
                    # Response not JSON - check status code
                    if response.status_code == 200:
                        logger.info(f"Successfully removed domain from blacklist: {domain}")
                        return True
                    else:
                        logger.warning(
                            f"Pi-hole returned status {response.status_code} for {domain}"
                        )
                        return False
                
            except requests.RequestException as e:
                logger.warning(
                    f"Attempt {attempt}/{self.retry_attempts} failed "
                    f"to remove domain {domain}: {e}"
                )
                
                if attempt < self.retry_attempts:
                    sleep_time = 2 ** attempt
                    logger.debug(f"Retrying in {sleep_time} seconds...")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"Failed to remove domain {domain} after {self.retry_attempts} attempts")
                    return False
        
        return False
    
    def get_status(self) -> Optional[dict]:
        """
        Get Pi-hole status.
        
        Returns:
            Status dictionary or None if failed
        """
        if not self.api_token:
            logger.error("Cannot get status: API token not configured")
            return None
        
        params = {
            "status": "",
            "auth": self.api_token
        }
        
        try:
            response = requests.get(
                self.base_url,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Failed to get Pi-hole status: {e}")
            return None
    
    def test_connection(self) -> bool:
        """
        Test connection to Pi-hole API.
        
        Returns:
            True if connection successful, False otherwise
        """
        logger.info("Testing Pi-hole API connection...")
        
        status = self.get_status()
        if status:
            logger.info(f"Pi-hole API connection successful: {status}")
            return True
        else:
            logger.error("Pi-hole API connection failed")
            return False


class DummyPiHoleClient:
    """
    Dummy Pi-hole client for testing without actual Pi-hole instance.
    
    Logs actions but doesn't make real API calls.
    """
    
    def __init__(self):
        """Initialize dummy Pi-hole client."""
        logger.warning(
            "Using DummyPiHoleClient. "
            "Domain blocking is DISABLED (logging only)."
        )
    
    def add_domain(self, domain: str, comment: str = "") -> bool:
        """Log domain addition (no actual API call)."""
        logger.info(f"[DUMMY] Would add domain to blacklist: {domain} (comment: {comment})")
        return True
    
    def remove_domain(self, domain: str) -> bool:
        """Log domain removal (no actual API call)."""
        logger.info(f"[DUMMY] Would remove domain from blacklist: {domain}")
        return True
    
    def get_status(self) -> Optional[dict]:
        """Return dummy status."""
        return {"status": "enabled", "dummy": True}
    
    def test_connection(self) -> bool:
        """Always return True."""
        logger.info("[DUMMY] Pi-hole API connection test (always succeeds)")
        return True
