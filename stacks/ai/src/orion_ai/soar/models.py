"""
SOAR data models for playbooks, conditions, and actions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ActionType(str, Enum):
    """Types of SOAR actions."""
    BLOCK_DOMAIN = "BLOCK_DOMAIN"
    TAG_DEVICE = "TAG_DEVICE"
    SEND_NOTIFICATION = "SEND_NOTIFICATION"
    SIMULATE_ONLY = "SIMULATE_ONLY"
    LOG_EVENT = "LOG_EVENT"


class ConditionOperator(str, Enum):
    """Operators for condition evaluation."""
    EQUALS = "=="
    NOT_EQUALS = "!="
    GREATER_THAN = ">"
    LESS_THAN = "<"
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    IN = "in"
    NOT_IN = "not_in"


@dataclass
class Condition:
    """
    Condition for playbook matching.
    
    Evaluates expressions against event fields.
    
    Attributes:
        field: Field name to evaluate (supports dot notation, e.g., "metadata.score")
        operator: Comparison operator
        value: Value to compare against
    """
    field: str
    operator: ConditionOperator
    value: Any
    
    def evaluate(self, event_data: Dict[str, Any]) -> bool:
        """
        Evaluate condition against event data.
        
        Args:
            event_data: Event data dictionary
            
        Returns:
            True if condition matches, False otherwise
        """
        # Get field value (support dot notation)
        field_value = self._get_nested_value(event_data, self.field)
        
        if field_value is None:
            return False
        
        # Evaluate based on operator
        if self.operator == ConditionOperator.EQUALS:
            return field_value == self.value
        elif self.operator == ConditionOperator.NOT_EQUALS:
            return field_value != self.value
        elif self.operator == ConditionOperator.GREATER_THAN:
            return field_value > self.value
        elif self.operator == ConditionOperator.LESS_THAN:
            return field_value < self.value
        elif self.operator == ConditionOperator.GREATER_EQUAL:
            return field_value >= self.value
        elif self.operator == ConditionOperator.LESS_EQUAL:
            return field_value <= self.value
        elif self.operator == ConditionOperator.CONTAINS:
            return self.value in str(field_value)
        elif self.operator == ConditionOperator.NOT_CONTAINS:
            return self.value not in str(field_value)
        elif self.operator == ConditionOperator.IN:
            return field_value in self.value
        elif self.operator == ConditionOperator.NOT_IN:
            return field_value not in self.value
        
        return False
    
    def _get_nested_value(self, data: Dict[str, Any], field: str) -> Any:
        """Get value from nested dictionary using dot notation."""
        parts = field.split(".")
        value = data
        
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        
        return value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "field": self.field,
            "operator": self.operator.value,
            "value": self.value,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Condition':
        """Create Condition from dictionary."""
        return cls(
            field=data["field"],
            operator=ConditionOperator(data["operator"]),
            value=data["value"]
        )


@dataclass
class Action:
    """
    Action to execute when playbook matches.
    
    Attributes:
        type: Type of action
        params: Action-specific parameters
    """
    type: ActionType
    params: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.type.value,
            "params": self.params,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Action':
        """Create Action from dictionary."""
        return cls(
            type=ActionType(data["type"]),
            params=data.get("params", {})
        )


@dataclass
class Playbook:
    """
    SOAR playbook defining conditions and actions.
    
    Attributes:
        id: Unique playbook identifier
        name: Human-readable name
        enabled: Whether playbook is active
        match_event_type: Event type to match (or "*" for all)
        conditions: List of conditions (all must match)
        actions: List of actions to execute
        dry_run: If True, simulate actions without executing
        priority: Execution priority (higher = earlier)
    """
    id: str
    name: str
    enabled: bool
    match_event_type: str
    conditions: List[Condition] = field(default_factory=list)
    actions: List[Action] = field(default_factory=list)
    dry_run: bool = False
    priority: int = 0
    
    def matches(self, event_data: Dict[str, Any]) -> bool:
        """
        Check if event matches this playbook.
        
        Args:
            event_data: Event data dictionary
            
        Returns:
            True if all conditions match, False otherwise
        """
        if not self.enabled:
            return False
        
        # Check event type
        if self.match_event_type != "*":
            if event_data.get("event_type") != self.match_event_type:
                return False
        
        # Evaluate all conditions (AND logic)
        for condition in self.conditions:
            if not condition.evaluate(event_data):
                return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "enabled": self.enabled,
            "match_event_type": self.match_event_type,
            "conditions": [c.to_dict() for c in self.conditions],
            "actions": [a.to_dict() for a in self.actions],
            "dry_run": self.dry_run,
            "priority": self.priority,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Playbook':
        """Create Playbook from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            enabled=data.get("enabled", True),
            match_event_type=data.get("match_event_type", "*"),
            conditions=[Condition.from_dict(c) for c in data.get("conditions", [])],
            actions=[Action.from_dict(a) for a in data.get("actions", [])],
            dry_run=data.get("dry_run", False),
            priority=data.get("priority", 0)
        )


@dataclass
class TriggeredAction:
    """
    Record of an action that was triggered by a playbook.
    
    Attributes:
        playbook_id: ID of playbook that triggered this action
        playbook_name: Name of playbook
        action: Action that was triggered
        event_id: ID of event that triggered the action
        timestamp: When action was triggered
        executed: Whether action was actually executed (False if dry_run)
        success: Whether action execution succeeded (None if not executed)
        error: Error message if action failed
    """
    playbook_id: str
    playbook_name: str
    action: Action
    event_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    executed: bool = False
    success: Optional[bool] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "playbook_id": self.playbook_id,
            "playbook_name": self.playbook_name,
            "action": self.action.to_dict(),
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "executed": self.executed,
            "success": self.success,
            "error": self.error,
        }
