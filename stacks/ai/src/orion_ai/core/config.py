"""
Configuration management for Orion Sentinel AI Service.

Uses Pydantic Settings for environment variable validation and type safety.
"""

import os
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class LokiConfig(BaseSettings):
    """Loki connection configuration."""
    
    url: str = Field(
        default="http://loki:3100",
        description="Loki HTTP API URL"
    )
    timeout: int = Field(
        default=30,
        description="Query timeout in seconds"
    )
    
    class Config:
        env_prefix = "LOKI_"


class PiHoleConfig(BaseSettings):
    """Pi-hole API configuration."""
    
    api_url: str = Field(
        default="http://192.168.1.10/admin/api.php",
        description="Pi-hole API endpoint URL"
    )
    api_token: str = Field(
        default="",
        description="Pi-hole API authentication token"
    )
    timeout: int = Field(
        default=10,
        description="API request timeout in seconds"
    )
    retry_attempts: int = Field(
        default=3,
        description="Number of retry attempts for failed API calls"
    )
    
    class Config:
        env_prefix = "PIHOLE_"


class ModelConfig(BaseSettings):
    """ML model configuration."""
    
    device_anomaly_model: str = Field(
        default="/models/device_anomaly.onnx",
        description="Path to device anomaly detection model"
    )
    domain_risk_model: str = Field(
        default="/models/domain_risk.onnx",
        description="Path to domain risk scoring model"
    )
    device_anomaly_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Threshold for device anomaly alerts"
    )
    domain_risk_threshold: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Threshold for domain blocking"
    )
    
    @field_validator("device_anomaly_threshold", "domain_risk_threshold")
    @classmethod
    def validate_threshold(cls, v: float) -> float:
        """Validate threshold is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0")
        return v
    
    class Config:
        env_prefix = ""


class ThreatIntelConfig(BaseSettings):
    """Threat intelligence feed configuration."""
    
    enable_threat_intel: bool = Field(
        default=True,
        description="Enable threat intelligence feed integration"
    )
    cache_path: str = Field(
        default="/var/lib/orion-ai/threat_intel.db",
        description="Path to threat intelligence cache database"
    )
    otx_api_key: Optional[str] = Field(
        default=None,
        description="AlienVault OTX API key (optional, increases rate limits)"
    )
    refresh_interval_hours: int = Field(
        default=6,
        ge=1,
        description="How often to refresh threat feeds (hours)"
    )
    ioc_score_boost: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Score boost when IOC match is found"
    )
    cleanup_days: int = Field(
        default=30,
        ge=1,
        description="Remove threat data older than this many days"
    )
    
    class Config:
        env_prefix = "THREAT_INTEL_"


class DetectionConfig(BaseSettings):
    """Detection pipeline configuration."""
    
    device_window_minutes: int = Field(
        default=10,
        ge=1,
        description="Time window for device anomaly detection (minutes)"
    )
    domain_window_minutes: int = Field(
        default=60,
        ge=1,
        description="Time window for domain risk scoring (minutes)"
    )
    batch_interval: int = Field(
        default=10,
        ge=1,
        description="Batch processing interval (minutes)"
    )
    enable_blocking: bool = Field(
        default=False,
        description="Enable automatic domain blocking via Pi-hole"
    )
    streaming_mode: bool = Field(
        default=False,
        description="Enable real-time streaming mode (vs batch)"
    )
    
    class Config:
        env_prefix = ""


class AppConfig(BaseSettings):
    """Main application configuration."""
    
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    log_output_dir: str = Field(
        default="/var/log/ai",
        description="Directory for AI result logs"
    )
    
    # Nested configurations
    loki: LokiConfig = Field(default_factory=LokiConfig)
    pihole: PiHoleConfig = Field(default_factory=PiHoleConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    detection: DetectionConfig = Field(default_factory=DetectionConfig)
    threat_intel: ThreatIntelConfig = Field(default_factory=ThreatIntelConfig)
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global config instance
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """
    Get the global configuration instance.
    
    Lazily loads configuration on first access.
    
    Returns:
        AppConfig: The global configuration instance
    """
    global _config
    if _config is None:
        _config = AppConfig(
            loki=LokiConfig(),
            pihole=PiHoleConfig(),
            model=ModelConfig(),
            detection=DetectionConfig(),
            threat_intel=ThreatIntelConfig()
        )
    return _config


def reload_config() -> AppConfig:
    """
    Reload configuration from environment variables.
    
    Useful for testing or when environment changes.
    
    Returns:
        AppConfig: The reloaded configuration instance
    """
    global _config
    _config = None
    return get_config()


def get_loki_url() -> str:
    """
    Get the Loki URL from environment or configuration.
    
    This is a convenience helper for components that need to connect to Loki.
    Priority order:
    1. LOKI_URL environment variable (for SPoG/standalone mode switching)
    2. Configuration system default
    
    In SPoG mode, this points to CoreSrv Loki (e.g., http://192.168.8.XXX:3100).
    In dev/lab mode, this points to local Loki (http://loki:3100).
    
    Returns:
        str: The Loki HTTP API URL
    """
    # Check environment variable first to allow runtime override
    env_url = os.getenv("LOKI_URL")
    if env_url:
        return env_url
    
    # Fall back to configuration system
    return get_config().loki.url
