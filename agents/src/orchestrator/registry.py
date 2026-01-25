"""Registry of agents and their routing rules.

Maps intents to agent execution sequences without executing agents.
"""

from typing import List, Dict, Any
from dataclasses import dataclass
from enum import Enum


class AgentType(str, Enum):
    """Available agent types in the system."""
    
    EVENT_AGENT = "event_agent"
    CAMPAIGN_AGENT = "campaign_agent"
    ANALYSIS_AGENT = "analysis_agent"
    CODE_REVIEW_AGENT = "code_review_agent"
    TESTING_AGENT = "testing_agent"


@dataclass
class AgentTask:
    """Definition of an agent and what it should do.
    
    Attributes:
        agent: The agent type to execute
        task: Human-readable description of the task
        params: Parameters specific to this agent from the intent
    """
    
    agent: AgentType
    task: str
    params: Dict[str, Any]


@dataclass
class ExecutionPlan:
    """Ordered sequence of agents to execute.
    
    Attributes:
        intent_type: The intent that generated this plan
        sequence: List of agent tasks in execution order
        parallelizable: Set of agent indices that can run in parallel
    """
    
    intent_type: str
    sequence: List[AgentTask]
    parallelizable: List[set] = None
    
    def __post_init__(self):
        """Set default parallelizable groups."""
        if self.parallelizable is None:
            self.parallelizable = []


class AgentRegistry:
    """Deterministic registry of agent routing rules.
    
    This is the control plane: it decides what should happen,
    not how it happens or whether it succeeds.
    """
    
    # Routing rules: IntentType -> ExecutionPlan
    ROUTES = {
        "register_event": ExecutionPlan(
            intent_type="register_event",
            sequence=[
                AgentTask(
                    agent=AgentType.EVENT_AGENT,
                    task="Validate event data and register with demo-domain",
                    params={"action": "register"}
                ),
            ],
            parallelizable=[],
        ),
        
        "create_campaign": ExecutionPlan(
            intent_type="create_campaign",
            sequence=[
                AgentTask(
                    agent=AgentType.CAMPAIGN_AGENT,
                    task="Create campaign in demo-domain",
                    params={"action": "create"}
                ),
                AgentTask(
                    agent=AgentType.CAMPAIGN_AGENT,
                    task="Add rules to campaign",
                    params={"action": "add_rules"}
                ),
            ],
            parallelizable=[],  # Sequential: must create campaign before adding rules
        ),
        
        "analyze_earnings": ExecutionPlan(
            intent_type="analyze_earnings",
            sequence=[
                AgentTask(
                    agent=AgentType.ANALYSIS_AGENT,
                    task="Query earnings data",
                    params={"action": "query"}
                ),
                AgentTask(
                    agent=AgentType.ANALYSIS_AGENT,
                    task="Generate analysis and summary",
                    params={"action": "analyze"}
                ),
            ],
            parallelizable=[],
        ),
        
        "review_code": ExecutionPlan(
            intent_type="review_code",
            sequence=[
                AgentTask(
                    agent=AgentType.CODE_REVIEW_AGENT,
                    task="Review code and generate feedback",
                    params={"action": "review"}
                ),
            ],
            parallelizable=[],
        ),
        
        "run_tests": ExecutionPlan(
            intent_type="run_tests",
            sequence=[
                AgentTask(
                    agent=AgentType.TESTING_AGENT,
                    task="Run test suite and collect results",
                    params={"action": "run"}
                ),
            ],
            parallelizable=[],
        ),
    }
    
    @classmethod
    def get_route(cls, intent_type: str) -> ExecutionPlan:
        """Look up the execution plan for an intent.
        
        Args:
            intent_type: The type of intent
            
        Returns:
            ExecutionPlan specifying which agents to run and in what order
            
        Raises:
            ValueError: If intent type is not registered
        """
        if intent_type not in cls.ROUTES:
            available = ", ".join(cls.ROUTES.keys())
            raise ValueError(
                f"Unknown intent type: {intent_type}. "
                f"Available: {available}"
            )
        return cls.ROUTES[intent_type]
    
    @classmethod
    def list_routes(cls) -> List[str]:
        """Return all registered intent types."""
        return list(cls.ROUTES.keys())
