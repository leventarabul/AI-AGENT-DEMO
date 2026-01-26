"""Orchestrator: Single entry point for agent orchestration.

Accepts an intent, applies decision rules, executes agents sequentially.
Controls the entire development pipeline.
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from orchestrator.decision_router import (
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


@dataclass
class AgentExecutionResult:
    """Result of executing a single agent.
    
    Attributes:
        agent: Agent name
        success: Whether agent executed successfully
        output: Agent output (varies by agent type)
        error: Error message if success is False
    """
    agent: str
    success: bool
    output: Any = None
    error: str = None


@dataclass
class PipelineResult:
    """Result of executing the entire pipeline.
    
    Attributes:
        intent_type: The intent type
        status: "success", "partial", or "failure"
        agent_results: List of AgentExecutionResult in execution order
        final_commit: Git commit hash if development was successful
        error: Error message if status is "failure"
    """
    intent_type: str
    status: str  # "success", "partial", "failure"
    agent_results: List[AgentExecutionResult]
    final_commit: Optional[str] = None
    error: Optional[str] = None
    
    def __repr__(self):
        """Human-readable representation."""
        agents_executed = len([r for r in self.agent_results if r.success])
        total_agents = len(self.agent_results)
        
        return (
            f"PipelineResult(\n"
            f"  intent={self.intent_type},\n"
            f"  status={self.status},\n"
            f"  agents_executed={agents_executed}/{total_agents},\n"
            f"  final_commit={self.final_commit or 'N/A'}\n"
            f")"
        )


class Orchestrator:
    """Single entry point for agent orchestration.
    
    Responsibilities:
    - Accept an intent
    - Validate the intent
    - Apply decision rules (via decision_router)
    - Execute agents sequentially
    - Detect and handle ALL agent failures centrally
    - Return complete pipeline result
    
    CRITICAL: This is the ONLY orchestrator in the system.
    Agents must NOT:
    - Decide which agent runs next
    - Call other agents directly
    - Contain multi-step workflow logic
    
    The orchestrator:
    - Plans the execution (via decision_router)
    - Executes the plan
    - Stops on first failure
    """
    
    def __init__(self):
        """Initialize orchestrator with agent registry."""
        self._agent_instances = {}
    
    def _get_agent(self, agent_name: str) -> Any:
        """Get or create an agent instance.
        
        Args:
            agent_name: Name of the agent (e.g., "development_agent")
        
        Returns:
            Agent instance
            
        Raises:
            ValueError: If agent type is not supported
        """
        if agent_name in self._agent_instances:
            return self._agent_instances[agent_name]
        
        # Lazy-load agents by type
        if agent_name == "development_agent":
            from agents.development_agent import DevelopmentAgent
            agent = DevelopmentAgent()
        elif agent_name == "code_review_agent":
            from agents.code_review_agent import CodeReviewAgent
            agent = CodeReviewAgent()
        elif agent_name == "testing_agent":
            from agents.testing_agent import TestingAgent
            agent = TestingAgent()
        else:
            raise ValueError(f"Unknown agent type: {agent_name}")
        
        self._agent_instances[agent_name] = agent
        return agent
    
    def _check_agent_result(self, agent_name: str, output: Any) -> tuple[bool, Optional[str]]:
        """Centralized agent result checking.
        
        This is the SINGLE place where agent results are evaluated for continuation.
        
        Checks for:
        1. success=False attribute
        2. CodeReviewAgent-specific decisions (BLOCK, REQUEST_CHANGES)
        3. Any other agent-specific failure patterns
        
        Args:
            agent_name: Name of the agent that produced this output
            output: The agent's output object
            
        Returns:
            Tuple of (should_continue, error_message)
            - (True, None) means continue pipeline
            - (False, "reason") means stop pipeline
        """
        # Check 1: Generic success field
        if hasattr(output, 'success') and not output.success:
            error = getattr(output, 'error', 'Unknown error')
            return False, f"Agent failed: {error}"
        
        # Check 2: CodeReviewAgent decision field
        if agent_name == "code_review_agent" and hasattr(output, 'decision'):
            from agents.code_review_agent import ReviewDecision
            
            if output.decision == ReviewDecision.BLOCK:
                return False, f"Code review BLOCKED: {output.reasoning}"
            elif output.decision == ReviewDecision.REQUEST_CHANGES:
                return False, f"Code review REQUEST_CHANGES: {output.reasoning}"
            # APPROVE means continue
        
        # Check 3: TestingAgent test failures (if applicable in future)
        # if agent_name == "testing_agent" and hasattr(output, 'tests_failed'):
        #     if output.tests_failed > 0:
        #         return False, f"Tests failed: {output.tests_failed} failures"
        
        # All checks passed - continue pipeline
        return True, None
    
    def route(self, intent: Intent) -> OrchestrationDecision:
        """Route an intent to an execution plan (planning phase).
        
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
    
    def execute(self, intent: Intent) -> PipelineResult:
        """Execute the full pipeline for an intent (execution phase).
        
        Sequence:
        1. Route the intent (planning)
        2. Execute agents in order
        3. Stop on first failure
        4. Return complete results
        
        Args:
            intent: The user intent to fulfill
            
        Returns:
            PipelineResult with execution status and agent outputs
        """
        
        try:
            # Validate intent
            if not isinstance(intent, Intent):
                raise ValueError("Input must be an Intent object")
            
            # Plan the pipeline
            decision = self.route(intent)
            if decision.status == "error":
                return PipelineResult(
                    intent_type=intent.type,
                    status="failure",
                    agent_results=[],
                    error=decision.error,
                )
            
            # Execute agents sequentially
            agent_results = []
            final_commit = None
            
            for i, task in enumerate(decision.execution_plan.tasks):
                try:
                    # Get agent instance
                    agent = self._get_agent(task.agent)
                    
                    # Execute agent
                    print(f"\n▶ Executing {task.agent}: {task.task}")
                    output = agent.execute(intent.context)
                    
                    # Centralized failure detection for ALL agents
                    should_continue, error_message = self._check_agent_result(task.agent, output)
                    
                    if not should_continue:
                        # Agent failed or blocked - stop pipeline
                        agent_results.append(AgentExecutionResult(
                            agent=task.agent,
                            success=False,
                            output=output,
                            error=error_message,
                        ))
                        
                        return PipelineResult(
                            intent_type=intent.type,
                            status="partial",
                            agent_results=agent_results,
                            error=error_message,
                        )
                    
                    # Agent succeeded
                    agent_results.append(AgentExecutionResult(
                        agent=task.agent,
                        success=True,
                        output=output,
                    ))
                    
                    # Extract commit hash if available
                    if hasattr(output, 'commit_hash') and output.commit_hash:
                        final_commit = output.commit_hash
                    
                    print(f"✓ {task.agent} completed successfully")
                    
                except Exception as e:
                    # Execution error
                    agent_results.append(AgentExecutionResult(
                        agent=task.agent,
                        success=False,
                        error=str(e),
                    ))
                    
                    # Stop pipeline on error
                    return PipelineResult(
                        intent_type=intent.type,
                        status="partial",
                        agent_results=agent_results,
                        final_commit=final_commit,
                        error=f"Error executing {task.agent}: {str(e)}",
                    )
            
            # All agents succeeded
            return PipelineResult(
                intent_type=intent.type,
                status="success",
                agent_results=agent_results,
                final_commit=final_commit,
            )
            
        except Exception as e:
            return PipelineResult(
                intent_type=intent.type if isinstance(intent, Intent) else "unknown",
                status="failure",
                agent_results=[],
                error=f"Orchestration error: {str(e)}",
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


def execute(intent: Intent) -> PipelineResult:
    """Convenience function: execute a full pipeline using the default orchestrator.
    
    Args:
        intent: The intent to execute
        
    Returns:
        PipelineResult with execution status and results
    """
    return get_orchestrator().execute(intent)
