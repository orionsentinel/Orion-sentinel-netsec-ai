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

from typing import Dict, Any

# Environment configuration defaults
DEFAULT_CONFIG: Dict[str, Any] = {
    "loki_url": "http://localhost:3100",
    "pihole_url": "http://192.168.1.2",
    "soar_dry_run": True,
    "log_level": "INFO",
}

__all__ = ["__version__", "__author__", "DEFAULT_CONFIG"]
