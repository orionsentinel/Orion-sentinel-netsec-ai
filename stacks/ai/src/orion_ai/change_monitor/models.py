"""
Change monitoring models.

TODO: Implement ChangeEvent and baseline models.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any


@dataclass
class ChangeEvent:
    """
    Represents a detected change in network behavior.
    
    TODO: Implement change detection logic.
    """
    device_id: str
    change_type: str
    timestamp: datetime
    description: str
    metadata: Dict[str, Any]
