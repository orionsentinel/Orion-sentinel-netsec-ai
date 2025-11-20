"""
Health score calculation logic.
"""

import logging
from typing import List

from .models import HealthMetrics, HealthScore

logger = logging.getLogger(__name__)


class HealthScoreCalculator:
    """
    Calculates security health score based on metrics.
    
    The score is weighted across four categories:
    - Inventory health (25%)
    - Threat landscape (35%)
    - Change management (20%)
    - Hygiene practices (20%)
    """

    # Weights for each component (must sum to 1.0)
    WEIGHTS = {
        "inventory": 0.25,
        "threat": 0.35,
        "change": 0.20,
        "hygiene": 0.20,
    }

    def compute_health_score(self, metrics: HealthMetrics) -> HealthScore:
        """
        Compute overall health score from metrics.
        
        Args:
            metrics: Input metrics
            
        Returns:
            Computed health score
        """
        # Calculate component scores
        inventory_score = self._calculate_inventory_score(metrics)
        threat_score = self._calculate_threat_score(metrics)
        change_score = self._calculate_change_score(metrics)
        hygiene_score = self._calculate_hygiene_score(metrics)
        
        # Calculate weighted overall score
        overall_score = (
            inventory_score * self.WEIGHTS["inventory"] +
            threat_score * self.WEIGHTS["threat"] +
            change_score * self.WEIGHTS["change"] +
            hygiene_score * self.WEIGHTS["hygiene"]
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(metrics)
        
        # Determine grade
        grade = self._score_to_grade(int(overall_score))
        
        health_score = HealthScore(
            score=int(overall_score),
            inventory_score=inventory_score,
            threat_score=threat_score,
            change_score=change_score,
            hygiene_score=hygiene_score,
            metrics=metrics,
            recommendations=recommendations,
            grade=grade,
        )
        
        logger.info(
            f"Health score calculated: {health_score.score}/100 (Grade: {grade})"
        )
        
        return health_score

    def _calculate_inventory_score(self, metrics: HealthMetrics) -> float:
        """
        Calculate inventory health score.
        
        Penalties for:
        - Unknown devices
        - Untagged devices
        - High-risk devices
        """
        if metrics.total_devices == 0:
            return 100.0
        
        score = 100.0
        
        # Penalty for unknown devices (up to -30)
        unknown_ratio = metrics.unknown_devices / metrics.total_devices
        score -= unknown_ratio * 30
        
        # Penalty for untagged devices (up to -20)
        untagged_ratio = metrics.untagged_devices / metrics.total_devices
        score -= untagged_ratio * 20
        
        # Penalty for high-risk devices (up to -50)
        high_risk_ratio = metrics.high_risk_devices / metrics.total_devices
        score -= high_risk_ratio * 50
        
        return max(0.0, score)

    def _calculate_threat_score(self, metrics: HealthMetrics) -> float:
        """
        Calculate threat landscape score.
        
        Penalties for:
        - High severity anomalies
        - Intel matches
        - Suricata alerts
        - Unresolved incidents
        """
        score = 100.0
        
        # Penalty for high-severity anomalies (each -5, max -40)
        score -= min(metrics.high_severity_anomalies_24h * 5, 40)
        
        # Penalty for intel matches in last 24h (each -10, max -30)
        score -= min(metrics.intel_matches_24h * 10, 30)
        
        # Penalty for intel matches in last 7d (each -2, max -20)
        score -= min(metrics.intel_matches_7d * 2, 20)
        
        # Penalty for Suricata alerts (each -1, max -10)
        score -= min(metrics.suricata_alerts_24h * 1, 10)
        
        # Penalty for unresolved incidents (each -5, max -20)
        score -= min(metrics.unresolved_incidents * 5, 20)
        
        return max(0.0, score)

    def _calculate_change_score(self, metrics: HealthMetrics) -> float:
        """
        Calculate change management score.
        
        Penalties for:
        - Too many new devices
        - High-risk changes
        """
        score = 100.0
        
        # Penalty for too many new devices (each -5, max -30)
        score -= min(metrics.new_devices_7d * 5, 30)
        
        # Penalty for high-risk changes (each -10, max -70)
        score -= min(metrics.high_risk_changes_24h * 10, 70)
        
        return max(0.0, score)

    def _calculate_hygiene_score(self, metrics: HealthMetrics) -> float:
        """
        Calculate hygiene practices score.
        
        Based on manual flags.
        """
        score = 0.0
        
        if metrics.backups_ok:
            score += 40
        
        if metrics.updates_current:
            score += 40
        
        if metrics.firewall_enabled:
            score += 20
        
        return score

    def _generate_recommendations(self, metrics: HealthMetrics) -> List[str]:
        """
        Generate actionable recommendations.
        
        Args:
            metrics: Health metrics
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        # Inventory recommendations
        if metrics.unknown_devices > 0:
            recommendations.append(
                f"Tag or classify {metrics.unknown_devices} unknown device(s)"
            )
        
        if metrics.untagged_devices > 0:
            recommendations.append(
                f"Add tags to {metrics.untagged_devices} device(s)"
            )
        
        if metrics.high_risk_devices > 0:
            recommendations.append(
                f"Investigate {metrics.high_risk_devices} high-risk device(s)"
            )
        
        # Threat recommendations
        if metrics.high_severity_anomalies_24h > 0:
            recommendations.append(
                f"Review {metrics.high_severity_anomalies_24h} high-severity anomaly/anomalies"
            )
        
        if metrics.intel_matches_24h > 0:
            recommendations.append(
                f"Investigate {metrics.intel_matches_24h} recent threat intel match(es)"
            )
        
        if metrics.unresolved_incidents > 0:
            recommendations.append(
                f"Resolve {metrics.unresolved_incidents} open incident(s)"
            )
        
        # Change recommendations
        if metrics.new_devices_7d > 3:
            recommendations.append(
                f"Review {metrics.new_devices_7d} new devices from last week"
            )
        
        if metrics.high_risk_changes_24h > 0:
            recommendations.append(
                f"Review {metrics.high_risk_changes_24h} high-risk change(s)"
            )
        
        # Hygiene recommendations
        if not metrics.backups_ok:
            recommendations.append("Set up or verify backup system")
        
        if not metrics.updates_current:
            recommendations.append("Update systems and apply security patches")
        
        if not metrics.firewall_enabled:
            recommendations.append("Enable firewall on all endpoints")
        
        return recommendations

    def _score_to_grade(self, score: int) -> str:
        """Convert numeric score to letter grade."""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
