"""
Health score data models.
"""

from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, Field


class HealthMetrics(BaseModel):
    """
    Input metrics for health score calculation.
    """

    # Device inventory metrics
    total_devices: int = 0
    unknown_devices: int = 0
    untagged_devices: int = 0
    high_risk_devices: int = 0
    
    # Security event metrics
    high_severity_anomalies_24h: int = 0
    intel_matches_24h: int = 0
    intel_matches_7d: int = 0
    suricata_alerts_24h: int = 0
    
    # Change metrics
    new_devices_7d: int = 0
    high_risk_changes_24h: int = 0
    
    # Manual hygiene flags
    backups_ok: bool = False
    updates_current: bool = False
    firewall_enabled: bool = True
    
    # SOAR metrics
    unresolved_incidents: int = 0
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_devices": 25,
                "unknown_devices": 3,
                "untagged_devices": 5,
                "high_risk_devices": 1,
                "high_severity_anomalies_24h": 2,
                "intel_matches_24h": 0,
                "intel_matches_7d": 1,
                "suricata_alerts_24h": 5,
                "new_devices_7d": 1,
                "high_risk_changes_24h": 0,
                "backups_ok": True,
                "updates_current": True,
                "firewall_enabled": True,
                "unresolved_incidents": 0,
            }
        }


class HealthScore(BaseModel):
    """
    Calculated health score with breakdown.
    """

    score: int = Field(..., ge=0, le=100, description="Overall health score 0-100")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Component scores (each 0-100)
    inventory_score: float = 0.0
    threat_score: float = 0.0
    change_score: float = 0.0
    hygiene_score: float = 0.0
    
    # Metrics used
    metrics: HealthMetrics
    
    # Recommendations
    recommendations: list[str] = Field(default_factory=list)
    
    # Grade
    grade: str = "F"  # A, B, C, D, F
    
    class Config:
        json_schema_extra = {
            "example": {
                "score": 82,
                "timestamp": "2025-01-15T10:30:00Z",
                "inventory_score": 85.0,
                "threat_score": 90.0,
                "change_score": 75.0,
                "hygiene_score": 80.0,
                "metrics": {},
                "recommendations": [
                    "Tag 5 unknown devices",
                    "Investigate 2 high-severity anomalies",
                ],
                "grade": "B",
            }
        }
