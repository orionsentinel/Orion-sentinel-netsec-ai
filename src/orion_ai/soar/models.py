"""
SOAR data models for playbooks, conditions, actions, and events.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Types of events that can trigger playbooks."""

    INTEL_MATCH = "intel_match"
    AI_DEVICE_ANOMALY = "ai-device-anomaly"
    AI_DOMAIN_RISK = "ai-domain-risk"
    INVENTORY_NEW_DEVICE = "inventory_event"
    CHANGE_EVENT = "change_event"
    HONEYPOT_HIT = "honeypot_hit"
    SURICATA_ALERT = "suricata_alert"


class ActionType(str, Enum):
    """Types of actions that can be executed by playbooks."""

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
    GREATER_THAN_OR_EQUAL = ">="
    LESS_THAN = "<"
    LESS_THAN_OR_EQUAL = "<="
    CONTAINS = "contains"
    IN = "in"
    AND = "and"
    OR = "or"


class EventRef(BaseModel):
    """
    Reference to an event in Loki or other log storage.
    
    This is a generic pointer that allows playbooks to reference
    and act upon various types of security events.
    """

    event_type: EventType
    timestamp: datetime
    labels: Dict[str, str] = Field(default_factory=dict)
    fields: Dict[str, Any] = Field(default_factory=dict)
    source: str = "loki"
    stream_id: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "intel_match",
                "timestamp": "2025-01-15T10:30:00Z",
                "labels": {"service": "threat_intel", "severity": "high"},
                "fields": {
                    "ioc_type": "DOMAIN",
                    "ioc_value": "malicious.example.com",
                    "confidence": 0.95,
                    "source": "abuse.ch",
                },
            }
        }


class Condition(BaseModel):
    """
    A condition that must be met for a playbook to trigger.
    
    Supports simple field comparisons and logical operators.
    """

    field: str  # Field name to check (e.g., "fields.confidence", "labels.severity")
    operator: ConditionOperator
    value: Any  # Value to compare against
    negate: bool = False

    def evaluate(self, event: EventRef) -> bool:
        """
        Evaluate this condition against an event.
        
        Args:
            event: The event to evaluate
            
        Returns:
            True if condition matches, False otherwise
        """
        # TODO: Implement full field path resolution (e.g., "fields.confidence")
        # For now, basic implementation
        field_value = self._get_field_value(event, self.field)
        
        if field_value is None:
            return self.negate  # If field doesn't exist, return negate value
        
        result = self._compare(field_value, self.operator, self.value)
        return not result if self.negate else result

    def _get_field_value(self, event: EventRef, field_path: str) -> Any:
        """Extract field value from event using dot notation."""
        parts = field_path.split(".")
        current = event.dict()
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        
        return current

    def _compare(self, field_value: Any, operator: ConditionOperator, target_value: Any) -> bool:
        """Compare field value with target using operator."""
        if operator == ConditionOperator.EQUALS:
            return field_value == target_value
        elif operator == ConditionOperator.NOT_EQUALS:
            return field_value != target_value
        elif operator == ConditionOperator.GREATER_THAN:
            return field_value > target_value
        elif operator == ConditionOperator.GREATER_THAN_OR_EQUAL:
            return field_value >= target_value
        elif operator == ConditionOperator.LESS_THAN:
            return field_value < target_value
        elif operator == ConditionOperator.LESS_THAN_OR_EQUAL:
            return field_value <= target_value
        elif operator == ConditionOperator.CONTAINS:
            return target_value in str(field_value)
        elif operator == ConditionOperator.IN:
            return field_value in target_value
        
        return False


class Action(BaseModel):
    """
    An action to be executed when a playbook triggers.
    """

    action_type: ActionType
    parameters: Dict[str, Any] = Field(default_factory=dict)
    description: str = ""

    class Config:
        json_schema_extra = {
            "example": {
                "action_type": "BLOCK_DOMAIN",
                "parameters": {"domain": "{{fields.ioc_value}}", "reason": "Intel match"},
                "description": "Block malicious domain via Pi-hole",
            }
        }


class Playbook(BaseModel):
    """
    A playbook defines automated responses to security events.
    
    When conditions are met, the playbook executes its defined actions.
    """

    id: str
    name: str
    description: str = ""
    enabled: bool = True
    match_event_type: EventType
    conditions: List[Condition] = Field(default_factory=list)
    actions: List[Action] = Field(default_factory=list)
    dry_run: bool = True  # Safety: default to dry run
    priority: int = 50  # Higher priority playbooks run first

    class Config:
        json_schema_extra = {
            "example": {
                "id": "block-high-confidence-domains",
                "name": "Block High Confidence Malicious Domains",
                "description": "Auto-block domains with intel confidence >= 0.9",
                "enabled": True,
                "match_event_type": "intel_match",
                "conditions": [
                    {
                        "field": "fields.ioc_type",
                        "operator": "==",
                        "value": "DOMAIN",
                    },
                    {
                        "field": "fields.confidence",
                        "operator": ">=",
                        "value": 0.9,
                    },
                ],
                "actions": [
                    {
                        "action_type": "BLOCK_DOMAIN",
                        "parameters": {"domain": "{{fields.ioc_value}}"},
                    },
                    {
                        "action_type": "SEND_NOTIFICATION",
                        "parameters": {
                            "message": "Blocked domain {{fields.ioc_value}}",
                            "severity": "high",
                        },
                    },
                ],
                "dry_run": True,
            }
        }


class TriggeredAction(BaseModel):
    """
    Record of an action that was triggered (or would be in dry run).
    """

    playbook_id: str
    playbook_name: str
    event_ref: EventRef
    action: Action
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    executed: bool = False  # False if dry_run
    success: Optional[bool] = None
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "playbook_id": "block-high-confidence-domains",
                "playbook_name": "Block High Confidence Malicious Domains",
                "event_ref": {
                    "event_type": "intel_match",
                    "timestamp": "2025-01-15T10:30:00Z",
                    "fields": {"ioc_value": "malicious.example.com"},
                },
                "action": {
                    "action_type": "BLOCK_DOMAIN",
                    "parameters": {"domain": "malicious.example.com"},
                },
                "executed": False,
                "success": None,
            }
        }
