"""
Health score calculator.

Computes overall security health score from metrics.
"""

import logging
from datetime import datetime
from typing import List

from orion_ai.core.models import HealthMetrics, HealthScore

logger = logging.getLogger(__name__)


class HealthScoreCalculator:
    """
    Calculates security health score based on various metrics.
    
    Uses weighted scoring to combine multiple security indicators
    into a single 0-100 health score.
    """
    
    # Weights for different metrics (sum should be 1.0)
    WEIGHTS = {
        "unknown_devices": 0.15,
        "high_anomalies": 0.30,
        "intel_matches": 0.35,
        "new_devices": 0.10,
        "critical_events": 0.10,
    }
    
    # Thresholds for penalty calculation
    THRESHOLDS = {
        "unknown_devices": {"low": 2, "high": 5},
        "high_anomalies": {"low": 3, "high": 10},
        "intel_matches": {"low": 1, "high": 5},
        "new_devices": {"low": 3, "high": 10},
        "critical_events": {"low": 2, "high": 8},
    }
    
    def compute_health_score(self, metrics: HealthMetrics) -> HealthScore:
        """
        Compute health score from metrics.
        
        Args:
            metrics: Health metrics
            
        Returns:
            HealthScore with score, status, and insights
        """
        # Start with perfect score
        score = 100.0
        insights = []
        
        # Apply penalties for each metric
        score, insight = self._apply_penalty(
            score,
            metrics.unknown_device_count,
            "unknown_devices",
            "unknown/untagged devices"
        )
        if insight:
            insights.append(insight)
        
        score, insight = self._apply_penalty(
            score,
            metrics.high_anomaly_count,
            "high_anomalies",
            "high-severity anomalies in last 24h"
        )
        if insight:
            insights.append(insight)
        
        score, insight = self._apply_penalty(
            score,
            metrics.intel_matches_count,
            "intel_matches",
            "threat intelligence matches in last 7 days"
        )
        if insight:
            insights.append(insight)
        
        score, insight = self._apply_penalty(
            score,
            metrics.new_devices_count,
            "new_devices",
            "new devices in last 7 days"
        )
        if insight:
            insights.append(insight)
        
        score, insight = self._apply_penalty(
            score,
            metrics.critical_events_count,
            "critical_events",
            "unresolved critical events"
        )
        if insight:
            insights.append(insight)
        
        # Ensure score is in valid range
        score = max(0, min(100, int(score)))
        
        # Determine status
        if score >= 80:
            status = "Good"
        elif score >= 60:
            status = "Fair"
        elif score >= 40:
            status = "Poor"
        else:
            status = "Critical"
        
        # Add general insights if score is low
        if score < 60 and not insights:
            insights.append("Multiple security concerns detected. Review recent events.")
        
        # Create health score
        health_score = HealthScore(
            score=score,
            timestamp=datetime.now(),
            metrics=metrics,
            status=status,
            insights=insights
        )
        
        logger.info(f"Computed health score: {score} ({status})")
        return health_score
    
    def _apply_penalty(
        self,
        current_score: float,
        value: int,
        metric_name: str,
        description: str
    ) -> tuple[float, str]:
        """
        Apply penalty to score based on metric value.
        
        Args:
            current_score: Current score
            value: Metric value
            metric_name: Name of metric (for thresholds)
            description: Human-readable description
            
        Returns:
            Tuple of (new_score, insight_message)
        """
        if value == 0:
            return current_score, None
        
        weight = self.WEIGHTS.get(metric_name, 0.1)
        thresholds = self.THRESHOLDS.get(metric_name, {"low": 5, "high": 10})
        
        # Calculate penalty based on value vs thresholds
        if value <= thresholds["low"]:
            # Minor penalty
            penalty = weight * 30  # 30% of max penalty
            insight = f"{value} {description}"
        elif value <= thresholds["high"]:
            # Moderate penalty
            penalty = weight * 60  # 60% of max penalty
            insight = f"{value} {description} - moderate concern"
        else:
            # High penalty
            penalty = weight * 100  # Full penalty
            insight = f"{value} {description} - high concern"
        
        new_score = current_score - penalty
        return new_score, insight
