"""Intent data model and types.

Intents represent user-facing requests that agents need to fulfill.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional
from enum import Enum


class IntentType(str, Enum):
    """Standard intent types."""
    
    REGISTER_EVENT = "register_event"
    CREATE_CAMPAIGN = "create_campaign"
    ANALYZE_EARNINGS = "analyze_earnings"
    REVIEW_CODE = "review_code"
    RUN_TESTS = "run_tests"


@dataclass
class Intent:
    """Represents a high-level request to be fulfilled by agents.
    
    Attributes:
        type: The intent type (e.g., REGISTER_EVENT)
        context: Domain-specific parameters needed to fulfill the intent
        metadata: Optional metadata (user_id, timestamp, priority, etc.)
    """
    
    type: IntentType
    context: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validate intent structure."""
        if not self.context:
            raise ValueError("Intent context cannot be empty")
        if not isinstance(self.context, dict):
            raise TypeError("Intent context must be a dictionary")
