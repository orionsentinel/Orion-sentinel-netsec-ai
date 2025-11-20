"""
Orion Sentinel AI Service

AI-powered threat detection for network security monitoring.
Provides device anomaly detection and domain risk scoring.
"""

__version__ = "0.1.0"
__author__ = "Orion Sentinel Project"

from orion_ai.config import get_config

__all__ = ["get_config"]
