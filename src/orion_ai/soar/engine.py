"""
SOAR playbook engine for evaluating events and triggering actions.
"""

import logging
from typing import List, Optional
from pathlib import Path
import yaml

from .models import (
    EventRef,
    Playbook,
    TriggeredAction,
    Condition,
)

logger = logging.getLogger(__name__)


class PlaybookEngine:
    """
    Engine for evaluating playbooks against events and determining actions.
    
    The engine:
    1. Loads playbooks from configuration
    2. Evaluates incoming events against playbook conditions
    3. Generates TriggeredAction records for matching playbooks
    """

    def __init__(self, playbooks: Optional[List[Playbook]] = None):
        """
        Initialize the playbook engine.
        
        Args:
            playbooks: List of playbooks to use. If None, starts empty.
        """
        self.playbooks: List[Playbook] = playbooks or []
        self._sort_playbooks()

    def _sort_playbooks(self) -> None:
        """Sort playbooks by priority (higher first)."""
        self.playbooks.sort(key=lambda p: p.priority, reverse=True)

    def load_playbooks_from_file(self, filepath: Path) -> None:
        """
        Load playbooks from a YAML or JSON file.
        
        Args:
            filepath: Path to playbook configuration file
            
        Example YAML format:
            playbooks:
              - id: block-high-confidence
                name: Block High Confidence Threats
                enabled: true
                match_event_type: intel_match
                conditions:
                  - field: fields.confidence
                    operator: ">="
                    value: 0.9
                actions:
                  - action_type: BLOCK_DOMAIN
                    parameters:
                      domain: "{{fields.ioc_value}}"
        """
        try:
            with open(filepath, "r") as f:
                data = yaml.safe_load(f)
            
            if not data or "playbooks" not in data:
                logger.warning(f"No playbooks found in {filepath}")
                return
            
            for pb_data in data["playbooks"]:
                try:
                    playbook = Playbook(**pb_data)
                    self.playbooks.append(playbook)
                    logger.info(f"Loaded playbook: {playbook.id} - {playbook.name}")
                except Exception as e:
                    logger.error(f"Failed to load playbook {pb_data.get('id', 'unknown')}: {e}")
            
            self._sort_playbooks()
            logger.info(f"Loaded {len(self.playbooks)} playbooks from {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to load playbooks from {filepath}: {e}")
            raise

    def add_playbook(self, playbook: Playbook) -> None:
        """Add a playbook to the engine."""
        self.playbooks.append(playbook)
        self._sort_playbooks()

    def remove_playbook(self, playbook_id: str) -> bool:
        """Remove a playbook by ID."""
        initial_len = len(self.playbooks)
        self.playbooks = [p for p in self.playbooks if p.id != playbook_id]
        return len(self.playbooks) < initial_len

    def evaluate_event(self, event: EventRef) -> List[TriggeredAction]:
        """
        Evaluate a single event against all playbooks.
        
        Args:
            event: The event to evaluate
            
        Returns:
            List of triggered actions from matching playbooks
        """
        triggered_actions: List[TriggeredAction] = []
        
        for playbook in self.playbooks:
            if not playbook.enabled:
                continue
            
            # Check if event type matches
            if playbook.match_event_type != event.event_type:
                continue
            
            # Evaluate all conditions
            if not self._evaluate_conditions(playbook, event):
                continue
            
            # Playbook matched! Generate triggered actions
            logger.info(
                f"Playbook '{playbook.name}' (ID: {playbook.id}) matched event "
                f"{event.event_type} at {event.timestamp}"
            )
            
            for action in playbook.actions:
                # Resolve template parameters
                resolved_action = self._resolve_action_parameters(action, event)
                
                triggered_action = TriggeredAction(
                    playbook_id=playbook.id,
                    playbook_name=playbook.name,
                    event_ref=event,
                    action=resolved_action,
                    executed=False,  # Will be set by action executor
                )
                triggered_actions.append(triggered_action)
        
        return triggered_actions

    def run_playbooks_on_events(self, events: List[EventRef]) -> List[TriggeredAction]:
        """
        Evaluate multiple events against all playbooks.
        
        Args:
            events: List of events to evaluate
            
        Returns:
            List of all triggered actions from all matching playbooks
        """
        all_triggered_actions: List[TriggeredAction] = []
        
        for event in events:
            triggered_actions = self.evaluate_event(event)
            all_triggered_actions.extend(triggered_actions)
        
        logger.info(
            f"Processed {len(events)} events, triggered {len(all_triggered_actions)} actions"
        )
        
        return all_triggered_actions

    def _evaluate_conditions(self, playbook: Playbook, event: EventRef) -> bool:
        """
        Evaluate all conditions in a playbook against an event.
        
        All conditions must be true (AND logic by default).
        
        Args:
            playbook: The playbook with conditions
            event: The event to evaluate
            
        Returns:
            True if all conditions match
        """
        if not playbook.conditions:
            return True  # No conditions means always match
        
        for condition in playbook.conditions:
            try:
                if not condition.evaluate(event):
                    return False
            except Exception as e:
                logger.warning(
                    f"Condition evaluation failed for playbook {playbook.id}: {e}"
                )
                return False
        
        return True

    def _resolve_action_parameters(self, action, event: EventRef):
        """
        Resolve template parameters in action using event data.
        
        Supports simple {{field.path}} syntax.
        
        Args:
            action: The action with potential template parameters
            event: The event containing data for templates
            
        Returns:
            Action with resolved parameters
        """
        # TODO: Implement proper template resolution
        # For now, return action as-is
        # Future: Support {{fields.ioc_value}}, {{labels.severity}}, etc.
        return action

    def get_enabled_playbooks(self) -> List[Playbook]:
        """Get all enabled playbooks."""
        return [p for p in self.playbooks if p.enabled]

    def get_playbook(self, playbook_id: str) -> Optional[Playbook]:
        """Get a playbook by ID."""
        for playbook in self.playbooks:
            if playbook.id == playbook_id:
                return playbook
        return None
