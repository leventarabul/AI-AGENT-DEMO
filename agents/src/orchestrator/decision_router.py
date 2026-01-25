"""Decision router: Maps intents to execution plans.

Pure routing logic—no agent invocation, no LLMs.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Set


class MissingContextError(Exception):
    """Raised when intent context is missing required fields."""
    pass


class UnknownIntentError(Exception):
    """Raised when intent type is not registered."""
    pass


@dataclass
class AgentTask:
    """Represents a single agent task in an execution plan.
    
    Attributes:
        agent: Agent type/name (e.g., "event_agent")
        task: Human-readable description of what this agent does
        params: Parameters to pass to this agent
    """
    agent: str
    task: str
    params: Dict[str, Any]


@dataclass
class ExecutionPlan:
    """Ordered sequence of agents to execute.
    
    Attributes:
        intent_type: The intent that generated this plan
        tasks: List of AgentTask objects in execution order
        parallelizable: List of sets, each set containing agent indices that can run in parallel
    """
    intent_type: str
    tasks: List[AgentTask]
    parallelizable: List[Set[int]] = None
    
    def __post_init__(self):
        """Set default empty parallelizable list."""
        if self.parallelizable is None:
            self.parallelizable = []


# Decision rules: intent type -> ExecutionPlan template
DECISION_RULES = {
    "register_event": ExecutionPlan(
        intent_type="register_event",
        tasks=[
            AgentTask(
                agent="event_agent",
                task="Validate event data and register with demo-domain API",
                params={"action": "register"},
            ),
        ],
        parallelizable=[],
    ),
    
    "create_campaign": ExecutionPlan(
        intent_type="create_campaign",
        tasks=[
            AgentTask(
                agent="campaign_agent",
                task="Create campaign in demo-domain",
                params={"action": "create"},
            ),
            AgentTask(
                agent="campaign_agent",
                task="Add rules to the campaign",
                params={"action": "add_rules"},
            ),
        ],
        parallelizable=[],  # Sequential: create campaign before adding rules
    ),
    
    "analyze_earnings": ExecutionPlan(
        intent_type="analyze_earnings",
        tasks=[
            AgentTask(
                agent="analysis_agent",
                task="Query earnings data from demo-domain",
                params={"action": "query"},
            ),
            AgentTask(
                agent="analysis_agent",
                task="Generate analysis and summary",
                params={"action": "analyze"},
            ),
        ],
        parallelizable=[],  # Sequential: query before analyzing
    ),
    
    "review_code": ExecutionPlan(
        intent_type="review_code",
        tasks=[
            AgentTask(
                agent="code_review_agent",
                task="Review code and generate feedback",
                params={"action": "review"},
            ),
        ],
        parallelizable=[],
    ),
    
    "run_tests": ExecutionPlan(
        intent_type="run_tests",
        tasks=[
            AgentTask(
                agent="testing_agent",
                task="Run tests and collect results",
                params={"action": "run"},
            ),
        ],
        parallelizable=[],
    ),
}

# Context requirements per intent
CONTEXT_REQUIREMENTS = {
    "register_event": [
        "event_code",
        "customer_id",
        "transaction_id",
        "merchant_id",
        "amount",
    ],
    "create_campaign": [
        "name",
        "description",
        "rules",
    ],
    "analyze_earnings": [],  # All fields optional
    "review_code": [
        "repository",
    ],
    "run_tests": [
        "environment",
    ],
}


def apply_rules(intent_type: str, context: Dict[str, Any]) -> ExecutionPlan:
    """Apply decision rules to an intent and return an execution plan.
    
    Args:
        intent_type: The type of intent (e.g., "register_event")
        context: Domain-specific context for the intent
        
    Returns:
        ExecutionPlan specifying which agents to run and in what order
        
    Raises:
        UnknownIntentError: If intent type is not registered
        MissingContextError: If required context fields are missing
    """
    
    # Check if intent type is known
    if intent_type not in DECISION_RULES:
        available = ", ".join(DECISION_RULES.keys())
        raise UnknownIntentError(
            f"Unknown intent type: '{intent_type}'. "
            f"Available: {available}"
        )
    
    # Check for required context fields
    required = CONTEXT_REQUIREMENTS.get(intent_type, [])
    missing = [field for field in required if field not in context]
    
    if missing:
        raise MissingContextError(
            f"Intent '{intent_type}' missing required context: {', '.join(missing)}"
        )
    
    # Get the rule and return the plan
    plan = DECISION_RULES[intent_type]
    return plan


def list_available_intents() -> List[str]:
    """Return all registered intent types."""
    return sorted(DECISION_RULES.keys())


def get_intent_requirements(intent_type: str) -> List[str]:
    """Get the required context fields for an intent type."""
    if intent_type not in DECISION_RULES:
        raise UnknownIntentError(f"Unknown intent type: '{intent_type}'")
    
    return CONTEXT_REQUIREMENTS.get(intent_type, [])
