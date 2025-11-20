"""
Simple assistant API for natural language queries.

Provides basic pattern matching and data retrieval.
For future enhancement with LLM integration.
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assistant", tags=["assistant"])


class AssistantQuery(BaseModel):
    """Query to the assistant."""

    question: str
    context: Optional[Dict[str, Any]] = None


class AssistantResponse(BaseModel):
    """Response from the assistant."""

    answer: str
    data: Optional[Dict[str, Any]] = None
    query_type: str = "unknown"
    confidence: float = 0.0
    suggestions: List[str] = []


class SimpleAssistant:
    """
    Simple pattern-based assistant.
    
    Recognizes common query patterns and executes appropriate Loki queries.
    Can be enhanced later with LLM integration.
    """

    # Pattern definitions
    PATTERNS = [
        {
            "pattern": r"suspicious.*(?:from|for)\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})",
            "query_type": "suspicious_activity",
            "handler": "handle_suspicious_activity",
        },
        {
            "pattern": r"alerts.*(?:from|for)\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})",
            "query_type": "device_alerts",
            "handler": "handle_device_alerts",
        },
        {
            "pattern": r"new devices",
            "query_type": "new_devices",
            "handler": "handle_new_devices",
        },
        {
            "pattern": r"health score",
            "query_type": "health_score",
            "handler": "handle_health_score",
        },
        {
            "pattern": r"top threats",
            "query_type": "top_threats",
            "handler": "handle_top_threats",
        },
    ]

    def process_query(self, query: AssistantQuery) -> AssistantResponse:
        """
        Process a natural language query.
        
        Args:
            query: User query
            
        Returns:
            Assistant response
        """
        question_lower = query.question.lower()
        
        # Try to match patterns
        for pattern_def in self.PATTERNS:
            match = re.search(pattern_def["pattern"], question_lower, re.IGNORECASE)
            if match:
                handler_name = pattern_def["handler"]
                handler = getattr(self, handler_name, None)
                
                if handler:
                    return handler(match, query)
        
        # No pattern matched
        return AssistantResponse(
            answer="I'm not sure how to answer that. Try asking about:\n"
                   "- Suspicious activity from an IP\n"
                   "- New devices\n"
                   "- Health score\n"
                   "- Top threats",
            query_type="unknown",
            confidence=0.0,
            suggestions=[
                "Show me suspicious activity from 192.168.1.50",
                "What are the new devices?",
                "What's the current health score?",
            ],
        )

    def handle_suspicious_activity(
        self, match: re.Match, query: AssistantQuery
    ) -> AssistantResponse:
        """Handle queries about suspicious activity for an IP."""
        ip = match.group(1)
        
        # TODO: Query Loki for:
        # - High-severity Suricata alerts
        # - AI anomalies
        # - Intel matches
        # for this IP in last 24h
        
        logger.info(f"Assistant: Fetching suspicious activity for {ip}")
        
        return AssistantResponse(
            answer=f"Checking suspicious activity for {ip} in the last 24 hours...\n\n"
                   f"TODO: Query Loki for:\n"
                   f"- Suricata alerts\n"
                   f"- AI anomalies\n"
                   f"- Threat intel matches",
            data={"ip": ip, "lookback_hours": 24},
            query_type="suspicious_activity",
            confidence=0.9,
        )

    def handle_device_alerts(
        self, match: re.Match, query: AssistantQuery
    ) -> AssistantResponse:
        """Handle queries about alerts for a device."""
        ip = match.group(1)
        
        logger.info(f"Assistant: Fetching alerts for {ip}")
        
        return AssistantResponse(
            answer=f"Fetching alerts for device {ip}...\n\n"
                   f"TODO: Implement Loki query for alerts",
            data={"ip": ip},
            query_type="device_alerts",
            confidence=0.9,
        )

    def handle_new_devices(
        self, match: re.Match, query: AssistantQuery
    ) -> AssistantResponse:
        """Handle queries about new devices."""
        logger.info("Assistant: Fetching new devices")
        
        # TODO: Query inventory for devices first seen in last 7 days
        
        return AssistantResponse(
            answer="Checking for new devices in the last 7 days...\n\n"
                   "TODO: Query inventory database",
            data={"lookback_days": 7},
            query_type="new_devices",
            confidence=0.95,
        )

    def handle_health_score(
        self, match: re.Match, query: AssistantQuery
    ) -> AssistantResponse:
        """Handle queries about health score."""
        logger.info("Assistant: Fetching health score")
        
        # TODO: Query latest health score from Loki or service
        
        return AssistantResponse(
            answer="Fetching latest security health score...\n\n"
                   "TODO: Query health score service or Loki",
            data={},
            query_type="health_score",
            confidence=0.95,
        )

    def handle_top_threats(
        self, match: re.Match, query: AssistantQuery
    ) -> AssistantResponse:
        """Handle queries about top threats."""
        logger.info("Assistant: Fetching top threats")
        
        # TODO: Query Loki for most common:
        # - Suricata alert signatures
        # - Intel-matched IPs/domains
        # - High-risk devices
        
        return AssistantResponse(
            answer="Analyzing top threats...\n\n"
                   "TODO: Aggregate threat data from Loki",
            data={},
            query_type="top_threats",
            confidence=0.9,
        )


# Global assistant instance
assistant = SimpleAssistant()


@router.post("/query", response_model=AssistantResponse)
async def query_assistant(query: AssistantQuery) -> AssistantResponse:
    """
    Query the assistant with a natural language question.
    
    Args:
        query: User question
        
    Returns:
        Assistant response with answer and data
    
    Example queries:
    - "Show me suspicious activity from 192.168.1.50 in last 24h"
    - "What are the new devices?"
    - "What's the current health score?"
    - "Show me top threats"
    """
    logger.info(f"Assistant query: {query.question}")
    
    response = assistant.process_query(query)
    
    return response


@router.get("/suggestions", response_model=List[str])
async def get_suggestions() -> List[str]:
    """
    Get example queries that the assistant can handle.
    
    Returns:
        List of example questions
    """
    return [
        "Show me suspicious activity from 192.168.1.50",
        "What alerts are there for 192.168.1.100?",
        "What are the new devices?",
        "What's the current health score?",
        "Show me top threats",
    ]
