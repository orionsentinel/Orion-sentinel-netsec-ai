"""
Playbook engine for evaluating events against playbooks.
"""

import logging
import yaml
from pathlib import Path
from typing import Dict, List, Any

from orion_ai.core.models import Event
from orion_ai.soar.models import Playbook, TriggeredAction, Action

logger = logging.getLogger(__name__)


class PlaybookEngine:
    """
    Engine for evaluating events against playbooks.
    
    Loads playbooks from configuration and determines which actions
    should be triggered for each event.
    """
    
    def __init__(self, playbooks_path: str = "/etc/orion-ai/playbooks.yml"):
        """
        Initialize playbook engine.
        
        Args:
            playbooks_path: Path to playbooks YAML file
        """
        self.playbooks_path = playbooks_path
        self.playbooks: List[Playbook] = []
        
        # Load playbooks
        self.reload_playbooks()
        
        logger.info(
            f"Initialized PlaybookEngine with {len(self.playbooks)} playbooks "
            f"from {playbooks_path}"
        )
    
    def reload_playbooks(self) -> int:
        """
        Reload playbooks from configuration file.
        
        Returns:
            Number of playbooks loaded
        """
        self.playbooks = []
        
        # Check if file exists
        if not Path(self.playbooks_path).exists():
            logger.warning(f"Playbooks file not found: {self.playbooks_path}")
            return 0
        
        try:
            with open(self.playbooks_path, 'r') as f:
                data = yaml.safe_load(f)
            
            if not data or 'playbooks' not in data:
                logger.warning("No playbooks found in configuration")
                return 0
            
            # Load playbooks
            for playbook_data in data['playbooks']:
                try:
                    playbook = Playbook.from_dict(playbook_data)
                    self.playbooks.append(playbook)
                except Exception as e:
                    logger.error(f"Failed to load playbook: {e}")
            
            # Sort by priority (higher first)
            self.playbooks.sort(key=lambda p: p.priority, reverse=True)
            
            logger.info(f"Loaded {len(self.playbooks)} playbooks")
            return len(self.playbooks)
            
        except Exception as e:
            logger.error(f"Failed to load playbooks: {e}")
            return 0
    
    def evaluate_event(self, event: Event) -> List[TriggeredAction]:
        """
        Evaluate an event against all playbooks.
        
        Args:
            event: Event to evaluate
            
        Returns:
            List of actions that should be triggered
        """
        triggered_actions: List[TriggeredAction] = []
        
        # Convert event to dict for evaluation
        event_data = event.to_dict()
        
        for playbook in self.playbooks:
            if playbook.matches(event_data):
                logger.info(
                    f"Playbook '{playbook.name}' matched event {event.event_id}"
                )
                
                # Create triggered actions for each action in playbook
                for action in playbook.actions:
                    triggered_action = TriggeredAction(
                        playbook_id=playbook.id,
                        playbook_name=playbook.name,
                        action=action,
                        event_id=event.event_id,
                        executed=False
                    )
                    triggered_actions.append(triggered_action)
        
        return triggered_actions
    
    def get_playbook(self, playbook_id: str) -> Playbook:
        """
        Get a playbook by ID.
        
        Args:
            playbook_id: Playbook identifier
            
        Returns:
            Playbook if found, None otherwise
        """
        for playbook in self.playbooks:
            if playbook.id == playbook_id:
                return playbook
        return None
    
    def list_playbooks(self, enabled_only: bool = False) -> List[Playbook]:
        """
        List all playbooks.
        
        Args:
            enabled_only: If True, only return enabled playbooks
            
        Returns:
            List of playbooks
        """
        if enabled_only:
            return [p for p in self.playbooks if p.enabled]
        return self.playbooks.copy()
