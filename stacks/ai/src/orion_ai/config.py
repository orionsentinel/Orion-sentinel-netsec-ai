"""
Configuration management for Orion Sentinel AI Service.

DEPRECATED: This module is deprecated. Import from orion_ai.core.config instead.
Kept for backward compatibility.
"""

# Import everything from core.config for backward compatibility
from orion_ai.core.config import (
    LokiConfig,
    PiHoleConfig,
    ModelConfig,
    ThreatIntelConfig,
    DetectionConfig,
    AppConfig,
    get_config,
    reload_config,
)

__all__ = [
    "LokiConfig",
    "PiHoleConfig",
    "ModelConfig",
    "ThreatIntelConfig",
    "DetectionConfig",
    "AppConfig",
    "get_config",
    "reload_config",
]
