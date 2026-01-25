"""Orchestrator: Single entry point for agent orchestration.

Accepts an intent, applies decision rules, returns an execution plan.
Does NOT execute agents.
"""

from dataclasses import dataclass
from typing import Dict, Any, List
from agents.src.orchestrator.decision_router import (
    apply_rules,
    ExecutionPlan,
    UnknownIntentError,
    MissingContextError,
    list_available_intents,
    get_intent_requirements,
)


@dataclass
class Intent:
    """User-facing request that agents need to fulfill.
    
    Attributes:
        type: Intent type (e.g., "register_event", "create_campaign")
        context: Domain-specific parameters (dict)
        metadata: Optional metadata (user_id, timestamp, priority, etc.)
    """
    type: str
    context: Dict[str, Any]
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        """Validate intent structure."""
        if not isinstance(self.type, str) or not self.type:
            raise ValueError("Intent type must be a non-empty string")
        if not isinstance(self.context, dict):
            raise ValueError("Intent context must be a dictionary")


@dataclass
class OrchestrationDecision:
    """Result of routing an intent through the orchestrator.
    
    Attributes:
        intent_type: The intent type
        agents: Ordered list of agent names to execute
        execution_plan: Full ExecutionPlan with tasks and parameters
        parallelizable_groups: Sets of agent indices that can run in parallel
        status: "success" or "error"
        error: Error message if status is "error"
    """
    intent_type: str
    agents: List[str]
    execution_plan: ExecutionPlan
    parallelizable_groups: List[set]
    status: str = "success"
    error: str = None
    
    def __repr__(self):
        """Human-readable representation."""
        if self.status == "error":
            return f"OrchestrationDecision(status=error, error={self.error})"
        
        agents_str = " → ".join(self.agents)
        return (
            f"OrchestrationDecision(\n"
            f"  intent={self.intent_type},\n"
            f"  agents={agents_str},\n"
            f"  parallelizable_groups={self.parallelizable_groups}\n"
            f")"
        )


class Orchestrator:
    """Control plane for agent orchestration.
    
    Responsibilities:
    - Accept an intent
    - Validate the intent
    - Apply decision rules
    - Return an execution plan
    - No agent invocation
    - No LLMs
    
    This is the orchestrator, not the executor.
    """
    
    def route(self, intent: Intent) -> OrchestrationDecision:
        """Route an intent to an execution plan.
        
        Args:
            intent: The user intent to fulfill
            
        Returns:
            OrchestrationDecision with the execution plan or error
        """
        
        try:
            # Validate intent
            if not isinstance(intent, Intent):
                raise ValueError("Input must be an Intent object")
            
            # Apply routing rules
            plan = apply_rules(intent.type, intent.context)
            
            # Extract agent names
            agents = [task.agent for task in plan.tasks]
            
            # Build decision
            decision = OrchestrationDecision(
                intent_type=intent.type,
                agents=agents,
                execution_plan=plan,
                parallelizable_groups=plan.parallelizable,
                status="success",
            )
            
            return decision
            
        except (UnknownIntentError, MissingContextError, ValueError) as e:
            # Return error decision
            return OrchestrationDecision(
                intent_type=intent.type if isinstance(intent, Intent) else "unknown",
                agents=[],
                execution_plan=None,
                parallelizable_groups=[],
                status="error",
                error=str(e),
            )
    
    def get_available_intents(self) -> Dict[str, List[str]]:
        """Return all available intent types and their requirements.
        
        Returns:
            Dict mapping intent types to required context fields
        """
        intents = {}
        for intent_type in list_available_intents():
            intents[intent_type] = get_intent_requirements(intent_type)
        return intents


# Singleton instance for convenience
_default_orchestrator = None


def get_orchestrator() -> Orchestrator:
    """Get or create the default orchestrator instance."""
    global _default_orchestrator
    if _default_orchestrator is None:
        _default_orchestrator = Orchestrator()
    return _default_orchestrator


def route(intent: Intent) -> OrchestrationDecision:
    """Convenience function: route an intent using the default orchestrator.
    
    Args:
        intent: The intent to route
        
    Returns:
        OrchestrationDecision with the execution plan
    """
    return get_orchestrator().route(intent)
