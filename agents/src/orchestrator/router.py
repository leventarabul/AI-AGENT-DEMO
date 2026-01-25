"""Decision router for orchestrating agent execution.

Takes an intent, returns an execution plan.
No agent invocation, no LLMs—pure routing logic.
"""

from dataclasses import dataclass
from typing import List, Optional
from agents.src.orchestrator.intent import Intent, IntentType
from agents.src.orchestrator.registry import AgentRegistry, ExecutionPlan, AgentTask


@dataclass
class DecisionResult:
    """Result of routing an intent.
    
    Attributes:
        intent_type: The intent that was routed
        agents_to_run: List of agents in execution order
        execution_plan: Full execution plan with parameters
        parallelizable_groups: Sets of agent indices that can run in parallel
        reasoning: Human-readable explanation of the decision
    """
    
    intent_type: str
    agents_to_run: List[str]
    execution_plan: ExecutionPlan
    parallelizable_groups: List[set]
    reasoning: str


class DecisionRouter:
    """Control plane for agent orchestration.
    
    Deterministically maps intents to agent execution sequences
    without invoking agents or using any ML/LLM.
    """
    
    def __init__(self):
        """Initialize the router with the agent registry."""
        self.registry = AgentRegistry()
    
    def route(self, intent: Intent) -> DecisionResult:
        """Decide which agents should run for the given intent.
        
        Args:
            intent: The user intent to fulfill
            
        Returns:
            DecisionResult with the execution plan
            
        Raises:
            ValueError: If the intent type is not recognized
        """
        # Look up the routing rule
        plan = self.registry.get_route(intent.type.value)
        
        # Extract agent names from the plan
        agents = [task.agent.value for task in plan.sequence]
        
        # Generate a reasoning explanation
        reasoning = self._explain_decision(intent, plan)
        
        return DecisionResult(
            intent_type=intent.type.value,
            agents_to_run=agents,
            execution_plan=plan,
            parallelizable_groups=plan.parallelizable,
            reasoning=reasoning,
        )
    
    def _explain_decision(self, intent: Intent, plan: ExecutionPlan) -> str:
        """Generate a human-readable explanation of the routing decision.
        
        Args:
            intent: The intent being routed
            plan: The execution plan that was selected
            
        Returns:
            A string explaining the decision
        """
        agent_tasks = [
            f"{i+1}. {task.agent.value}: {task.task}"
            for i, task in enumerate(plan.sequence)
        ]
        
        agents_str = "\n  ".join(agent_tasks)
        
        explanation = (
            f"Intent '{intent.type.value}' routed to:\n"
            f"  {agents_str}"
        )
        
        if plan.parallelizable:
            parallel_groups = [
                f"Group {i}: agents {group}"
                for i, group in enumerate(plan.parallelizable)
            ]
            parallel_str = "\n  ".join(parallel_groups)
            explanation += f"\n\nParallelize-able agent groups:\n  {parallel_str}"
        
        return explanation
    
    def get_available_intents(self) -> List[str]:
        """Return all available intent types."""
        return self.registry.list_routes()
