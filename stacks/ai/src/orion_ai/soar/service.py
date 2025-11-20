"""
SOAR service - orchestrates playbook evaluation and action execution.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import List, Optional

from orion_ai.core.events import emit_new_event, get_loki_client
from orion_ai.core.models import Event, EventType, EventSeverity
from orion_ai.soar.actions import ActionHandler
from orion_ai.soar.engine import PlaybookEngine
from orion_ai.soar.models import TriggeredAction

logger = logging.getLogger(__name__)


class SOARService:
    """
    SOAR service that evaluates events and executes playbook actions.
    
    Periodically fetches recent events from Loki and runs them through
    the playbook engine.
    """
    
    def __init__(
        self,
        interval_minutes: int = 5,
        lookback_minutes: int = 10,
        playbooks_path: str = "/etc/orion-ai/playbooks.yml",
        engine: Optional[PlaybookEngine] = None,
        action_handler: Optional[ActionHandler] = None
    ):
        """
        Initialize SOAR service.
        
        Args:
            interval_minutes: How often to run SOAR evaluation
            lookback_minutes: How far back to look for events
            playbooks_path: Path to playbooks configuration
            engine: Playbook engine instance
            action_handler: Action handler instance
        """
        self.interval_minutes = interval_minutes
        self.lookback_minutes = lookback_minutes
        
        self.engine = engine or PlaybookEngine(playbooks_path)
        self.action_handler = action_handler or ActionHandler()
        self.loki_client = get_loki_client()
        
        # Track processed events to avoid duplicates
        self.processed_event_ids = set()
        
        logger.info(
            f"Initialized SOARService "
            f"(interval={interval_minutes}m, lookback={lookback_minutes}m)"
        )
    
    def run_once(self) -> int:
        """
        Run one iteration of SOAR evaluation.
        
        Returns:
            Number of actions executed
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=self.lookback_minutes)
        
        logger.info(f"Running SOAR evaluation from {start_time} to {end_time}")
        
        # Fetch recent events from Loki
        events = self._fetch_events(start_time, end_time)
        
        # Filter out already processed events
        new_events = [e for e in events if e.event_id not in self.processed_event_ids]
        
        logger.info(f"Evaluating {len(new_events)} new events")
        
        # Evaluate events and execute actions
        total_actions = 0
        for event in new_events:
            triggered_actions = self.engine.evaluate_event(event)
            
            if triggered_actions:
                logger.info(
                    f"Event {event.event_id} triggered {len(triggered_actions)} actions"
                )
                
                # Execute actions
                for triggered_action in triggered_actions:
                    # Check if playbook is in dry-run mode
                    playbook = self.engine.get_playbook(triggered_action.playbook_id)
                    dry_run = playbook.dry_run if playbook else False
                    
                    success = self.action_handler.execute(triggered_action, dry_run)
                    
                    if success:
                        total_actions += 1
                    
                    # Emit SOAR action event
                    self._emit_soar_action_event(triggered_action, event)
            
            # Mark as processed
            self.processed_event_ids.add(event.event_id)
        
        # Cleanup old processed IDs (keep last 10000)
        if len(self.processed_event_ids) > 10000:
            # Convert to list, keep last 5000
            self.processed_event_ids = set(list(self.processed_event_ids)[-5000:])
        
        logger.info(f"SOAR evaluation complete: {total_actions} actions executed")
        return total_actions
    
    def run_loop(self) -> None:
        """
        Run the SOAR service in a continuous loop.
        
        This method blocks and runs indefinitely.
        """
        logger.info("Starting SOAR service loop")
        
        while True:
            try:
                self.run_once()
            except Exception as e:
                logger.error(f"SOAR service iteration failed: {e}", exc_info=True)
            
            # Sleep until next interval
            logger.debug(f"Sleeping for {self.interval_minutes} minutes")
            time.sleep(self.interval_minutes * 60)
    
    def _fetch_events(self, start_time: datetime, end_time: datetime) -> List[Event]:
        """
        Fetch events from Loki.
        
        Args:
            start_time: Start of time window
            end_time: End of time window
            
        Returns:
            List of Event objects
        """
        # Query events stream
        query = '{stream="events"}'
        
        try:
            logs = self.loki_client.query_range(query, start_time, end_time, limit=1000)
        except Exception as e:
            logger.error(f"Failed to fetch events from Loki: {e}")
            return []
        
        # Convert log entries to Event objects
        events = []
        for log in logs:
            try:
                # Reconstruct Event from log data
                event = Event(
                    event_id=log.get("event_id", "unknown"),
                    event_type=EventType(log.get("event_type", "UNKNOWN")),
                    timestamp=log.get("_timestamp", datetime.now()),
                    device_id=log.get("device_id"),
                    ip=log.get("ip"),
                    severity=EventSeverity(log.get("severity", "INFO")),
                    title=log.get("title", ""),
                    description=log.get("description", ""),
                    source=log.get("source", ""),
                    metadata=log.get("metadata", {})
                )
                events.append(event)
            except Exception as e:
                logger.warning(f"Failed to parse event from log: {e}")
        
        return events
    
    def _emit_soar_action_event(
        self,
        triggered_action: TriggeredAction,
        original_event: Event
    ) -> None:
        """Emit an event recording a SOAR action."""
        severity = EventSeverity.INFO
        if not triggered_action.executed:
            severity = EventSeverity.INFO  # Dry-run
        elif not triggered_action.success:
            severity = EventSeverity.WARNING  # Failed
        
        emit_new_event(
            event_type=EventType.SOAR_ACTION,
            severity=severity,
            title=f"SOAR action: {triggered_action.action.type.value}",
            description=(
                f"Playbook '{triggered_action.playbook_name}' triggered action.\n"
                f"Action: {triggered_action.action.type.value}\n"
                f"Executed: {triggered_action.executed}\n"
                f"Success: {triggered_action.success}\n"
                f"Original event: {original_event.title}"
            ),
            source="soar",
            device_id=original_event.device_id,
            ip=original_event.ip,
            metadata={
                "playbook_id": triggered_action.playbook_id,
                "playbook_name": triggered_action.playbook_name,
                "action_type": triggered_action.action.type.value,
                "action_params": triggered_action.action.params,
                "original_event_id": original_event.event_id,
                "executed": triggered_action.executed,
                "success": triggered_action.success,
                "error": triggered_action.error,
            }
        )
