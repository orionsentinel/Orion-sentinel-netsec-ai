"""
Basic smoke tests for Orion Sentinel modules.

Run with: pytest tests/
"""

import pytest
from datetime import datetime

from orion_ai.soar.models import (
    Playbook, EventType, ActionType, EventRef,
    Condition, ConditionOperator, Action
)
from orion_ai.soar.engine import PlaybookEngine
from orion_ai.inventory.models import Device
from orion_ai.health_score.models import HealthMetrics
from orion_ai.health_score.calculator import HealthScoreCalculator
from orion_ai.change_monitor.analyzer import ChangeAnalyzer
from orion_ai.change_monitor.models import Baseline


class TestModels:
    """Test basic model creation."""
    
    def test_device_creation(self):
        device = Device(ip="192.168.1.50", mac="aa:bb:cc:dd:ee:ff")
        assert device.ip == "192.168.1.50"
        assert device.mac == "aa:bb:cc:dd:ee:ff"
    
    def test_playbook_creation(self):
        playbook = Playbook(
            id="test",
            name="Test Playbook",
            match_event_type=EventType.INTEL_MATCH,
            enabled=True
        )
        assert playbook.id == "test"
        assert playbook.enabled is True


class TestSOAREngine:
    """Test SOAR playbook engine."""
    
    def test_playbook_evaluation(self):
        # Create playbook
        playbook = Playbook(
            id="test-playbook",
            name="Test Playbook",
            enabled=True,
            match_event_type=EventType.INTEL_MATCH,
            conditions=[
                Condition(
                    field="fields.confidence",
                    operator=ConditionOperator.GREATER_THAN_OR_EQUAL,
                    value=0.9
                )
            ],
            actions=[
                Action(
                    action_type=ActionType.BLOCK_DOMAIN,
                    parameters={"domain": "test.com"}
                )
            ],
            dry_run=True
        )
        
        # Create engine
        engine = PlaybookEngine()
        engine.add_playbook(playbook)
        
        # Create event that matches
        event = EventRef(
            event_type=EventType.INTEL_MATCH,
            timestamp=datetime.now(),
            fields={"confidence": 0.95}
        )
        
        # Evaluate
        triggered = engine.evaluate_event(event)
        
        assert len(triggered) == 1
        assert triggered[0].action.action_type == ActionType.BLOCK_DOMAIN
    
    def test_playbook_no_match(self):
        # Create playbook with high threshold
        playbook = Playbook(
            id="test-playbook",
            name="Test Playbook",
            enabled=True,
            match_event_type=EventType.INTEL_MATCH,
            conditions=[
                Condition(
                    field="fields.confidence",
                    operator=ConditionOperator.GREATER_THAN_OR_EQUAL,
                    value=0.9
                )
            ],
            actions=[],
            dry_run=True
        )
        
        engine = PlaybookEngine()
        engine.add_playbook(playbook)
        
        # Event with low confidence
        event = EventRef(
            event_type=EventType.INTEL_MATCH,
            timestamp=datetime.now(),
            fields={"confidence": 0.5}
        )
        
        triggered = engine.evaluate_event(event)
        
        assert len(triggered) == 0


class TestHealthScore:
    """Test health score calculator."""
    
    def test_perfect_score(self):
        calculator = HealthScoreCalculator()
        
        perfect_metrics = HealthMetrics(
            total_devices=10,
            unknown_devices=0,
            untagged_devices=0,
            high_risk_devices=0,
            backups_ok=True,
            updates_current=True,
            firewall_enabled=True
        )
        
        score = calculator.compute_health_score(perfect_metrics)
        
        assert score.score == 100
        assert score.grade == "A"
    
    def test_degraded_score(self):
        calculator = HealthScoreCalculator()
        
        problem_metrics = HealthMetrics(
            total_devices=10,
            unknown_devices=3,
            high_severity_anomalies_24h=2,
            intel_matches_24h=1,
            backups_ok=False
        )
        
        score = calculator.compute_health_score(problem_metrics)
        
        assert score.score < 100
        assert len(score.recommendations) > 0


class TestChangeAnalyzer:
    """Test change detection."""
    
    def test_new_device_detection(self):
        analyzer = ChangeAnalyzer()
        
        previous = Baseline(
            snapshot_id="baseline_1",
            timestamp=datetime.now(),
            period_start=datetime.now(),
            period_end=datetime.now(),
            device_ips=["192.168.1.10"]
        )
        
        current = Baseline(
            snapshot_id="baseline_2",
            timestamp=datetime.now(),
            period_start=datetime.now(),
            period_end=datetime.now(),
            device_ips=["192.168.1.10", "192.168.1.20"]
        )
        
        changes = analyzer.compare_baselines(previous, current)
        
        new_device_changes = [c for c in changes if c.change_type.value == "new_device"]
        assert len(new_device_changes) == 1
        assert new_device_changes[0].entity == "192.168.1.20"
