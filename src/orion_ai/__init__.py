"""
Orion Sentinel NSM + AI - Security & Monitoring mini-SOC Platform

This package provides comprehensive network security monitoring, AI-powered
anomaly detection, SOAR automation, device inventory, and EDR-lite capabilities
for home/lab environments.

Main modules:
- soar: SOAR-lite automation and response playbooks
- inventory: Device inventory and fingerprinting
- host_logs: EDR-lite host log ingestion and normalization
- honeypot: Deception and honeypot integration
- change_monitor: Change detection and baseline tracking
- health_score: Security health score calculation
- ui: User interface APIs (device profiles, assistant)
"""

__version__ = "0.2.0"
__author__ = "Orion Sentinel Team"

import os
from typing import Dict, Any

# Environment configuration defaults
DEFAULT_CONFIG: Dict[str, Any] = {
    "loki_url": "http://localhost:3100",
    "pihole_url": "http://192.168.1.2",
    "soar_dry_run": True,
    "log_level": "INFO",
}


def get_loki_url() -> str:
    """
    Get the Loki URL from environment or configuration.
    
    This is a convenience helper for components that need to connect to Loki.
    Priority order:
    1. LOKI_URL environment variable (for SPoG/standalone mode switching)
    2. Default fallback (http://localhost:3100)
    
    In SPoG mode, this points to CoreSrv Loki (e.g., http://192.168.8.XXX:3100).
    In dev/lab mode, this points to local Loki (http://loki:3100).
    
    Returns:
        str: The Loki HTTP API URL
    """
    return os.getenv("LOKI_URL", DEFAULT_CONFIG["loki_url"])


__all__ = ["__version__", "__author__", "DEFAULT_CONFIG", "get_loki_url"]
