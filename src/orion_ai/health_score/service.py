"""
Health score service.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta

from .calculator import HealthScoreCalculator
from .models import HealthMetrics, HealthScore

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class HealthScoreService:
    """
    Service for continuous health score monitoring.
    
    Periodically:
    1. Collect metrics from various sources
    2. Calculate health score
    3. Emit score to Loki
    """

    def __init__(
        self,
        calculator: HealthScoreCalculator,
        loki_url: str = "http://localhost:3100",
        calculation_interval_hours: int = 1,
    ):
        """
        Initialize health score service.
        
        Args:
            calculator: Health score calculator
            loki_url: Loki URL
            calculation_interval_hours: How often to calculate score
        """
        self.calculator = calculator
        self.loki_url = loki_url
        self.calculation_interval_hours = calculation_interval_hours
        self.running = False

    async def collect_metrics(self) -> HealthMetrics:
        """
        Collect metrics from various sources.
        
        Returns:
            Health metrics
        """
        # TODO: Query various sources for metrics:
        # - Inventory store for device counts
        # - Loki for anomaly/alert counts
        # - Change monitor for change counts
        # - Manual config file for hygiene flags
        
        metrics = HealthMetrics(
            total_devices=0,
            unknown_devices=0,
            untagged_devices=0,
            high_risk_devices=0,
            high_severity_anomalies_24h=0,
            intel_matches_24h=0,
            intel_matches_7d=0,
            suricata_alerts_24h=0,
            new_devices_7d=0,
            high_risk_changes_24h=0,
            backups_ok=False,
            updates_current=False,
            firewall_enabled=True,
            unresolved_incidents=0,
        )
        
        logger.debug(f"Collected metrics: {metrics.dict()}")
        return metrics

    async def emit_health_score(self, health_score: HealthScore) -> None:
        """
        Emit health score to Loki.
        
        Args:
            health_score: Health score to emit
        """
        # TODO: Push to Loki
        # POST to {loki_url}/loki/api/v1/push
        # Labels: service=health_score, stream=health_score
        
        logger.info(
            f"Health Score: {health_score.score}/100 (Grade: {health_score.grade})"
        )
        logger.info(
            f"  Inventory: {health_score.inventory_score:.1f}, "
            f"Threat: {health_score.threat_score:.1f}, "
            f"Change: {health_score.change_score:.1f}, "
            f"Hygiene: {health_score.hygiene_score:.1f}"
        )
        
        if health_score.recommendations:
            logger.info("Recommendations:")
            for rec in health_score.recommendations:
                logger.info(f"  - {rec}")

    async def run_once(self) -> HealthScore:
        """
        Run one iteration of health score calculation.
        
        Returns:
            Calculated health score
        """
        try:
            logger.debug("Collecting metrics...")
            metrics = await self.collect_metrics()
            
            logger.debug("Calculating health score...")
            health_score = self.calculator.compute_health_score(metrics)
            
            await self.emit_health_score(health_score)
            
            return health_score
            
        except Exception as e:
            logger.error(f"Error calculating health score: {e}", exc_info=True)
            # Return a default low score
            return HealthScore(
                score=0,
                metrics=HealthMetrics(),
                grade="F",
            )

    async def run(self) -> None:
        """Run health score service continuously."""
        self.running = True
        logger.info(
            f"Starting health score service "
            f"(calculation interval: {self.calculation_interval_hours}h)"
        )
        
        iteration = 0
        while self.running:
            iteration += 1
            logger.debug(f"Health score iteration {iteration}")
            
            health_score = await self.run_once()
            
            # Sleep until next iteration
            sleep_seconds = self.calculation_interval_hours * 3600
            logger.debug(f"Sleeping for {self.calculation_interval_hours}h...")
            await asyncio.sleep(sleep_seconds)

    def stop(self) -> None:
        """Stop health score service."""
        logger.info("Stopping health score service")
        self.running = False


def main() -> None:
    """Main entry point for health score service."""
    loki_url = os.getenv("LOKI_URL", "http://localhost:3100")
    calculation_interval_hours = int(os.getenv("HEALTH_SCORE_INTERVAL_HOURS", "1"))
    
    logger.info("=" * 60)
    logger.info("Orion Sentinel - Health Score Service")
    logger.info("=" * 60)
    logger.info(f"Loki URL: {loki_url}")
    logger.info(f"Calculation Interval: {calculation_interval_hours}h")
    logger.info("=" * 60)
    
    calculator = HealthScoreCalculator()
    
    service = HealthScoreService(
        calculator=calculator,
        loki_url=loki_url,
        calculation_interval_hours=calculation_interval_hours,
    )
    
    try:
        asyncio.run(service.run())
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
        service.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
