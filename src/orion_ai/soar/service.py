"""
SOAR service for continuous monitoring and automated response.

This service periodically fetches events from Loki and executes playbooks.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from .actions import ActionExecutor, ActionLogger
from .engine import PlaybookEngine
from .models import EventRef, EventType, TriggeredAction

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class SoarService:
    """
    SOAR service that monitors events and executes playbooks.
    
    The service:
    1. Fetches recent events from Loki
    2. Evaluates them against playbooks
    3. Executes triggered actions
    4. Logs action results back to Loki
    """

    def __init__(
        self,
        engine: PlaybookEngine,
        executor: ActionExecutor,
        action_logger: ActionLogger,
        loki_url: str = "http://localhost:3100",
        poll_interval: int = 60,
    ):
        """
        Initialize SOAR service.
        
        Args:
            engine: Playbook engine
            executor: Action executor
            action_logger: Action logger
            loki_url: URL of Loki instance
            poll_interval: How often to poll for events (seconds)
        """
        self.engine = engine
        self.executor = executor
        self.action_logger = action_logger
        self.loki_url = loki_url
        self.poll_interval = poll_interval
        self.running = False

    async def fetch_events_from_loki(
        self, lookback_seconds: int = 300
    ) -> List[EventRef]:
        """
        Fetch recent events from Loki.
        
        Args:
            lookback_seconds: How far back to look for events
            
        Returns:
            List of events to process
        """
        # TODO: Implement actual Loki query
        # Use LogQL to query for events of interest:
        # - {service="threat_intel", stream="intel_match"}
        # - {service="ai", stream=~"ai-device-anomaly|ai-domain-risk"}
        # - {service="inventory", stream="inventory_event"}
        # - {service="honeypot"}
        
        logger.debug(
            f"Fetching events from Loki (last {lookback_seconds}s) - NOT IMPLEMENTED"
        )
        
        # Placeholder: return empty list
        # In production, this would make HTTP requests to Loki query API
        return []

    async def process_events(self, events: List[EventRef]) -> List[TriggeredAction]:
        """
        Process events through playbook engine and execute actions.
        
        Args:
            events: Events to process
            
        Returns:
            List of triggered actions
        """
        if not events:
            logger.debug("No events to process")
            return []
        
        logger.info(f"Processing {len(events)} events")
        
        # Evaluate events against playbooks
        triggered_actions = self.engine.run_playbooks_on_events(events)
        
        if not triggered_actions:
            logger.info("No playbooks matched")
            return []
        
        logger.info(f"Executing {len(triggered_actions)} triggered actions")
        
        # Execute actions
        results = []
        for triggered_action in triggered_actions:
            result = self.executor.execute(triggered_action)
            results.append(result)
            
            # Log to Loki
            try:
                self.action_logger.log_action(result)
            except Exception as e:
                logger.error(f"Failed to log action to Loki: {e}")
        
        return results

    async def run_once(self) -> int:
        """
        Run one iteration of the SOAR loop.
        
        Returns:
            Number of actions executed
        """
        try:
            # Fetch events from Loki
            events = await self.fetch_events_from_loki(
                lookback_seconds=self.poll_interval + 60
            )
            
            # Process events
            triggered_actions = await self.process_events(events)
            
            return len(triggered_actions)
            
        except Exception as e:
            logger.error(f"Error in SOAR loop iteration: {e}", exc_info=True)
            return 0

    async def run(self) -> None:
        """
        Run the SOAR service continuously.
        """
        self.running = True
        logger.info(
            f"Starting SOAR service (poll interval: {self.poll_interval}s, "
            f"dry_run: {self.executor.dry_run})"
        )
        logger.info(f"Loaded {len(self.engine.get_enabled_playbooks())} enabled playbooks")
        
        iteration = 0
        while self.running:
            iteration += 1
            logger.debug(f"SOAR iteration {iteration}")
            
            try:
                actions_executed = await self.run_once()
                logger.debug(f"Iteration {iteration} complete: {actions_executed} actions")
            except Exception as e:
                logger.error(f"Error in SOAR iteration {iteration}: {e}", exc_info=True)
            
            # Sleep until next iteration
            await asyncio.sleep(self.poll_interval)

    def stop(self) -> None:
        """Stop the SOAR service."""
        logger.info("Stopping SOAR service")
        self.running = False


def main() -> None:
    """
    Main entry point for SOAR service.
    """
    # Load configuration from environment
    loki_url = os.getenv("LOKI_URL", "http://localhost:3100")
    poll_interval = int(os.getenv("SOAR_POLL_INTERVAL", "60"))
    dry_run = os.getenv("SOAR_DRY_RUN", "1").lower() in ("1", "true", "yes")
    playbooks_file = os.getenv("SOAR_PLAYBOOKS_FILE", "/config/playbooks.yml")
    
    logger.info("=" * 60)
    logger.info("Orion Sentinel - SOAR Service")
    logger.info("=" * 60)
    logger.info(f"Loki URL: {loki_url}")
    logger.info(f"Poll Interval: {poll_interval}s")
    logger.info(f"Dry Run Mode: {dry_run}")
    logger.info(f"Playbooks File: {playbooks_file}")
    logger.info("=" * 60)
    
    # Initialize components
    engine = PlaybookEngine()
    
    # Load playbooks if file exists
    if Path(playbooks_file).exists():
        try:
            engine.load_playbooks_from_file(Path(playbooks_file))
        except Exception as e:
            logger.error(f"Failed to load playbooks: {e}")
            if not os.getenv("SOAR_ALLOW_EMPTY_PLAYBOOKS"):
                sys.exit(1)
    else:
        logger.warning(f"Playbooks file not found: {playbooks_file}")
        if not os.getenv("SOAR_ALLOW_EMPTY_PLAYBOOKS"):
            logger.error("Set SOAR_ALLOW_EMPTY_PLAYBOOKS=1 to start without playbooks")
            sys.exit(1)
    
    executor = ActionExecutor(dry_run=dry_run)
    action_logger = ActionLogger(loki_url=loki_url)
    
    # Create and run service
    service = SoarService(
        engine=engine,
        executor=executor,
        action_logger=action_logger,
        loki_url=loki_url,
        poll_interval=poll_interval,
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
