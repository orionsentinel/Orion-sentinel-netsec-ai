"""
Change monitoring service.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta

from .analyzer import ChangeAnalyzer
from .baseline import BaselineBuilder
from .models import ChangeEvent

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ChangeMonitorService:
    """
    Service for continuous change detection.
    
    Periodically:
    1. Build new baseline
    2. Compare with previous baseline
    3. Emit change events to Loki
    """

    def __init__(
        self,
        builder: BaselineBuilder,
        analyzer: ChangeAnalyzer,
        loki_url: str = "http://localhost:3100",
        baseline_interval_hours: int = 24,
        baseline_period_days: int = 7,
    ):
        """
        Initialize change monitor service.
        
        Args:
            builder: Baseline builder
            analyzer: Change analyzer
            loki_url: Loki URL
            baseline_interval_hours: How often to create new baselines
            baseline_period_days: How many days to include in baseline
        """
        self.builder = builder
        self.analyzer = analyzer
        self.loki_url = loki_url
        self.baseline_interval_hours = baseline_interval_hours
        self.baseline_period_days = baseline_period_days
        self.running = False
        self.previous_baseline_id = None

    async def run_once(self) -> int:
        """
        Run one iteration of change detection.
        
        Returns:
            Number of changes detected
        """
        try:
            logger.info("Building new baseline...")
            
            # Build current baseline
            current_baseline = self.builder.build_global_baseline(
                period_days=self.baseline_period_days
            )
            
            # Save it
            self.builder.save_baseline(current_baseline)
            
            changes = []
            
            # Compare with previous if available
            if self.previous_baseline_id:
                logger.info(f"Loading previous baseline: {self.previous_baseline_id}")
                previous_baseline = self.builder.load_baseline(self.previous_baseline_id)
                
                if previous_baseline:
                    logger.info("Analyzing changes...")
                    changes = self.analyzer.compare_baselines(
                        previous_baseline, current_baseline
                    )
                    
                    # Emit change events
                    for change in changes:
                        await self._emit_change_event(change)
            
            # Update previous baseline ID
            self.previous_baseline_id = current_baseline.snapshot_id
            
            logger.info(f"Change detection complete: {len(changes)} changes detected")
            return len(changes)
            
        except Exception as e:
            logger.error(f"Error in change detection: {e}", exc_info=True)
            return 0

    async def _emit_change_event(self, change: ChangeEvent) -> None:
        """
        Emit change event to Loki.
        
        Args:
            change: Change event to emit
        """
        # TODO: Push to Loki
        # POST to {loki_url}/loki/api/v1/push
        # Labels: service=change_monitor, stream=change_event, change_type={change.change_type}
        
        logger.info(
            f"Change detected: {change.change_type} for {change.entity} "
            f"(risk: {change.risk_level})"
        )
        logger.debug(f"Change details: {change.dict()}")

    async def run(self) -> None:
        """Run change monitor service continuously."""
        self.running = True
        logger.info(
            f"Starting change monitor service "
            f"(baseline interval: {self.baseline_interval_hours}h, "
            f"baseline period: {self.baseline_period_days}d)"
        )
        
        iteration = 0
        while self.running:
            iteration += 1
            logger.debug(f"Change monitor iteration {iteration}")
            
            changes_detected = await self.run_once()
            
            # Sleep until next iteration
            sleep_seconds = self.baseline_interval_hours * 3600
            logger.info(f"Sleeping for {self.baseline_interval_hours}h...")
            await asyncio.sleep(sleep_seconds)

    def stop(self) -> None:
        """Stop change monitor service."""
        logger.info("Stopping change monitor service")
        self.running = False


def main() -> None:
    """Main entry point for change monitor service."""
    loki_url = os.getenv("LOKI_URL", "http://localhost:3100")
    baseline_interval_hours = int(os.getenv("CHANGE_MONITOR_INTERVAL_HOURS", "24"))
    baseline_period_days = int(os.getenv("CHANGE_MONITOR_PERIOD_DAYS", "7"))
    
    logger.info("=" * 60)
    logger.info("Orion Sentinel - Change Monitor Service")
    logger.info("=" * 60)
    logger.info(f"Loki URL: {loki_url}")
    logger.info(f"Baseline Interval: {baseline_interval_hours}h")
    logger.info(f"Baseline Period: {baseline_period_days}d")
    logger.info("=" * 60)
    
    builder = BaselineBuilder()
    analyzer = ChangeAnalyzer()
    
    service = ChangeMonitorService(
        builder=builder,
        analyzer=analyzer,
        loki_url=loki_url,
        baseline_interval_hours=baseline_interval_hours,
        baseline_period_days=baseline_period_days,
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
