"""
Health score service - periodically calculates and emits health scores.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Optional

from orion_ai.core.events import emit_new_event, get_loki_client
from orion_ai.core.models import EventType, EventSeverity, HealthMetrics
from orion_ai.health_score.calculator import HealthScoreCalculator
from orion_ai.inventory.store import DeviceStore

logger = logging.getLogger(__name__)


class HealthScoreService:
    """
    Service for calculating and tracking security health score.
    
    Periodically computes health metrics from various sources and
    calculates an overall security health score.
    """
    
    def __init__(
        self,
        interval_minutes: int = 60,
        calculator: Optional[HealthScoreCalculator] = None,
        device_store: Optional[DeviceStore] = None
    ):
        """
        Initialize health score service.
        
        Args:
            interval_minutes: How often to calculate health score
            calculator: Health score calculator instance
            device_store: Device store for inventory metrics
        """
        self.interval_minutes = interval_minutes
        self.calculator = calculator or HealthScoreCalculator()
        self.device_store = device_store or DeviceStore()
        self.loki_client = get_loki_client()
        
        logger.info(f"Initialized HealthScoreService (interval={interval_minutes}m)")
    
    def run_once(self) -> int:
        """
        Run one iteration of health score calculation.
        
        Returns:
            Current health score (0-100)
        """
        logger.info("Calculating security health score")
        
        # Collect metrics
        metrics = self._collect_metrics()
        
        # Calculate score
        health_score = self.calculator.compute_health_score(metrics)
        
        # Emit health score event
        self._emit_health_score_event(health_score)
        
        logger.info(
            f"Health score calculated: {health_score.score} ({health_score.status})"
        )
        
        return health_score.score
    
    def run_loop(self) -> None:
        """
        Run the health score service in a continuous loop.
        
        This method blocks and runs indefinitely.
        """
        logger.info("Starting health score service loop")
        
        while True:
            try:
                self.run_once()
            except Exception as e:
                logger.error(f"Health score iteration failed: {e}", exc_info=True)
            
            # Sleep until next interval
            logger.debug(f"Sleeping for {self.interval_minutes} minutes")
            time.sleep(self.interval_minutes * 60)
    
    def _collect_metrics(self) -> HealthMetrics:
        """
        Collect health metrics from various sources.
        
        Returns:
            HealthMetrics object
        """
        metrics = HealthMetrics()
        
        # Count unknown/untagged devices
        try:
            all_devices = self.device_store.list_devices()
            metrics.unknown_device_count = sum(
                1 for d in all_devices 
                if not d.tags or d.guess_type == "unknown"
            )
        except Exception as e:
            logger.error(f"Failed to count unknown devices: {e}")
        
        # Count high anomalies in last 24h
        try:
            metrics.high_anomaly_count = self._count_events(
                event_type="device_anomaly",
                severity="CRITICAL",
                hours=24
            )
        except Exception as e:
            logger.error(f"Failed to count high anomalies: {e}")
        
        # Count threat intel matches in last 7 days
        try:
            metrics.intel_matches_count = self._count_events(
                event_type="intel_match",
                hours=24 * 7
            )
        except Exception as e:
            logger.error(f"Failed to count intel matches: {e}")
        
        # Count new devices in last 7 days
        try:
            metrics.new_devices_count = self._count_events(
                event_type="new_device",
                hours=24 * 7
            )
        except Exception as e:
            logger.error(f"Failed to count new devices: {e}")
        
        # Count unresolved critical events
        try:
            metrics.critical_events_count = self._count_events(
                severity="CRITICAL",
                hours=24 * 7
            )
        except Exception as e:
            logger.error(f"Failed to count critical events: {e}")
        
        logger.debug(f"Collected metrics: {metrics.to_dict()}")
        return metrics
    
    def _count_events(
        self,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        hours: int = 24
    ) -> int:
        """
        Count events in Loki matching criteria.
        
        Args:
            event_type: Optional event type filter
            severity: Optional severity filter
            hours: Time window in hours
            
        Returns:
            Event count
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        # Build LogQL query
        query_parts = ['{stream="events"}']
        
        if event_type:
            query_parts.append(f'event_type="{event_type}"')
        
        if severity:
            query_parts.append(f'severity="{severity}"')
        
        query = query_parts[0]
        if len(query_parts) > 1:
            query += ", " + ", ".join(query_parts[1:])
        
        query += "}"
        
        try:
            logs = self.loki_client.query_range(query, start_time, end_time, limit=10000)
            return len(logs)
        except Exception as e:
            logger.warning(f"Failed to query events: {e}")
            return 0
    
    def _emit_health_score_event(self, health_score) -> None:
        """Emit a health score update event."""
        # Determine severity based on score
        if health_score.score >= 80:
            severity = EventSeverity.INFO
        elif health_score.score >= 60:
            severity = EventSeverity.WARNING
        else:
            severity = EventSeverity.CRITICAL
        
        insights_text = "\n".join(f"- {i}" for i in health_score.insights)
        
        emit_new_event(
            event_type=EventType.SECURITY_HEALTH_UPDATE,
            severity=severity,
            title=f"Security Health: {health_score.status} ({health_score.score}/100)",
            description=(
                f"Security health score: {health_score.score}/100\n"
                f"Status: {health_score.status}\n\n"
                f"Key insights:\n{insights_text if insights_text else 'None'}"
            ),
            source="health_score",
            metadata={
                "score": health_score.score,
                "status": health_score.status,
                "metrics": health_score.metrics.to_dict(),
                "insights": health_score.insights,
            }
        )
