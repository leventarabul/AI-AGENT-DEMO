import logging
logger = logging.getLogger(__name__)
"""Orchestrator: Single entry point for agent orchestration.

Accepts an intent, applies decision rules, executes agents sequentially.
Controls the entire development pipeline.

Includes execution tracing for observability and debugging.
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import uuid
import os
from orchestrator.decision_router import (
    apply_rules,
    ExecutionPlan,
    UnknownIntentError,
    MissingContextError,
    list_available_intents,
    get_intent_requirements,
)
from orchestrator.execution_trace import (
    ExecutionTrace,
    TriggerInfo,
    StepStatus,
    PipelineStatus,
    get_trace_store,
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
        trace_id: ID of the execution trace for this run
    """
    intent_type: str
    status: str  # "success", "partial", "failure"
    agent_results: List[AgentExecutionResult]
    final_commit: Optional[str] = None
    error: Optional[str] = None
    trace_id: Optional[str] = None
    
    def __repr__(self):
        """Human-readable representation."""
        agents_executed = len([r for r in self.agent_results if r.success])
        total_agents = len(self.agent_results)
        
        return (
            f"PipelineResult(\n"
            f"  intent={self.intent_type},\n"
            f"  status={self.status},\n"
            f"  agents_executed={agents_executed}/{total_agents},\n"
            f"  final_commit={self.final_commit or 'N/A'},\n"
            f"  trace_id={self.trace_id or 'N/A'}\n"
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
    
    def _execute_git_operations(
        self,
        dev_output: Any,
        intent_context: Dict[str, Any],
        trace: Any,
        step: Any,
    ) -> Optional[str]:
        """Execute git operations after DevelopmentAgent completes.
        
        This is called by the orchestrator (NOT by the agent itself).
        
        Args:
            dev_output: DevelopmentResult from development_agent
            intent_context: The intent context (for branch name, etc.)
            trace: ExecutionTrace for recording steps
            step: Current execution step
            
        Returns:
            Commit hash if successful, None if failed
        """
        try:
            from orchestrator.git_service import create_git_service
            
            # Convert FileChange objects to dicts for GitService
            files_list = []
            for file_change in dev_output.files:
                files_list.append({
                    "path": file_change.path,
                    "content": file_change.content,
                })
            
            # Get repository root (from context or use current directory)
            repo_root = intent_context.get("repo_root") or os.getcwd()
            
            # Get branch name
            jira_key = intent_context.get("jira_issue_key", "AUTO")
            branch_name = intent_context.get("branch_name") or f"develop/{jira_key.lower()}"
            
            # Create GitService
            git_service = create_git_service(repo_root)
            
            # Execute git operations
            logger.info(f"  🔧 Running git operations in {repo_root}")
            git_result = git_service.execute_operation(
                files=files_list,
                commit_message=dev_output.commit_message,
                branch_name=branch_name,
            )
            
            # Check result
            if not git_result.success:
                error_msg = f"Git operations failed: {git_result.error}"
                logger.info(f"  ✗ {error_msg}")
                
                # Update trace with error
                trace.update_step(
                    step_number=step.step_number,
                    status=StepStatus.FAIL,
                    success=False,
                    error_message=error_msg,
                )
                trace.complete(PipelineStatus.PARTIAL, error_msg)
                
                return None
            
            # Success - update trace
            summary = f"Committed {len(git_result.files_written)} files to {branch_name}"
            trace.update_step(
                step_number=step.step_number,
                status=StepStatus.SUCCESS,
                success=True,
                output_summary=summary,
            )
            
            return git_result.commit_hash
            
        except Exception as e:
            error_msg = f"Git operations exception: {str(e)}"
            logger.info(f"  ✗ {error_msg}")
            
            # Update trace
            trace.update_step(
                step_number=step.step_number,
                status=StepStatus.FAIL,
                success=False,
                error_message=error_msg,
            )
            trace.complete(PipelineStatus.PARTIAL, error_msg)
            
            return None
    
    def _check_agent_result(self, agent_name: str, output: Any) -> tuple[bool, Optional[str]]:
        """Centralized agent result checking.
        
        This is the SINGLE place where agent results are evaluated for continuation.
        
        Checks for:
        1. Agent-specific status fields (CodeReviewAgent.decision, TestingAgent.status)
        2. Generic success=False attribute
        3. Any other agent-specific failure patterns
        
        Args:
            agent_name: Name of the agent that produced this output
            output: The agent's output object
            
        Returns:
            Tuple of (should_continue, error_message)
            - (True, None) means continue pipeline
            - (False, "reason") means stop pipeline
        """
        # Check 1: CodeReviewAgent decision field (checked BEFORE generic success)
        if agent_name == "code_review_agent" and hasattr(output, 'decision'):
            from agents.code_review_agent import ReviewDecision
            
            if output.decision == ReviewDecision.BLOCK:
                return False, f"Code review BLOCKED: {output.reasoning}"
            elif output.decision == ReviewDecision.REQUEST_CHANGES:
                return False, f"Code review REQUEST_CHANGES: {output.reasoning}"
            # APPROVE means continue
        
        # Check 2: TestingAgent status field (checked BEFORE generic success)
        if agent_name == "testing_agent" and hasattr(output, 'status'):
            from agents.testing_agent import TestStatus
            
            if output.status == TestStatus.FAIL:
                return False, f"Tests FAILED: {output.summary} ({output.failed_count} failures)"
            # PASS means continue
        
        # Check 3: Generic success field (fallback for agents without specific status)
        if hasattr(output, 'success') and not output.success:
            error = getattr(output, 'error', 'Unknown error')
            return False, f"Agent failed: {error}"
        
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
        1. Create execution trace
        2. Route the intent (planning)
        3. Execute agents in order
        4. Record each step in trace
        5. Stop on first failure
        6. Return complete results with trace ID
        
        Args:
            intent: The user intent to fulfill
            
        Returns:
            PipelineResult with execution status, agent outputs, and trace ID
        """
        
        # Create execution trace
        trace_id = str(uuid.uuid4())
        trigger = TriggerInfo(
            source=intent.metadata.get("source", "unknown") if intent.metadata else "unknown",
            issue_key=intent.context.get("issue_key"),
            intent_type=intent.type,
        )
        
        trace = ExecutionTrace(
            trace_id=trace_id,
            trigger=trigger,
            intent_type=intent.type,
            pipeline_status=PipelineStatus.RUNNING,
            started_at=None,  # Will be set by __post_init__
        )
        
        # Store trace immediately
        get_trace_store().store(trace)
        
        try:
            # Validate intent
            if not isinstance(intent, Intent):
                trace.complete(PipelineStatus.FAILED, "Input must be an Intent object")
                raise ValueError("Input must be an Intent object")
            
            # Plan the pipeline
            decision = self.route(intent)
            if decision.status == "error":
                trace.complete(PipelineStatus.FAILED, decision.error)
                return PipelineResult(
                    intent_type=intent.type,
                    status="failure",
                    agent_results=[],
                    error=decision.error,
                    trace_id=trace_id,
                )
            
            # Record execution plan in trace
            agents_summary = " → ".join([t.agent for t in decision.execution_plan.tasks])
            trace.execution_plan_summary = agents_summary
            
            # Execute agents sequentially
            agent_results = []
            final_commit = None
            
            for i, task in enumerate(decision.execution_plan.tasks):
                try:
                    # Record step start
                    step = trace.add_step(
                        agent_name=task.agent,
                        agent_task=task.task,
                        status=StepStatus.STARTED,
                    )
                    
                    # Get agent instance
                    agent = self._get_agent(task.agent)
                    
                    # Execute agent
                    logger.info(f"\n▶ Executing {task.agent}: {task.task}")
                    output = agent.execute(intent.context)
                    
                    # POST-EXECUTION HOOK: If development_agent, run git operations
                    if task.agent == "development_agent" and output.success:
                        logger.info(f"  📝 Development agent completed. Processing git operations...")
                        git_result = self._execute_git_operations(output, intent.context, trace, step)
                        
                        if not git_result:
                            # Git operations failed - stop pipeline
                            return PipelineResult(
                                intent_type=intent.type,
                                status="partial",
                                agent_results=agent_results,
                                error="Git operations failed after development_agent",
                                trace_id=trace_id,
                            )
                        
                        # Git succeeded - extract commit hash
                        final_commit = git_result
                        logger.info(f"  ✓ Git operations completed. Commit: {final_commit}")
                        # Update context with the actual code changes written by DevelopmentAgent
                        intent.context["code_changes"] = {
                            file_change.path: file_change.content
                            for file_change in output.files
                        }
                    
                    # Auto-fix loop for code review failures (single attempt)
                    if task.agent == "code_review_agent" and hasattr(output, "decision"):
                        from agents.code_review_agent import ReviewDecision
                        if output.decision in (ReviewDecision.BLOCK, ReviewDecision.REQUEST_CHANGES):
                            if not intent.context.get("auto_fix_attempted"):
                                intent.context["auto_fix_attempted"] = True
                                logger.info("  🛠️  Code review failed. Attempting auto-fix via DevelopmentAgent...")
                                dev_agent = self._get_agent("development_agent")
                                fix_context = {
                                    **intent.context,
                                    "auto_fix": True,
                                    "review_issues": output.issues,
                                }
                                fix_output = dev_agent.execute(fix_context)
                                if fix_output.success:
                                    logger.info("  🧩 Auto-fix completed. Applying git operations...")
                                    git_result = self._execute_git_operations(
                                        fix_output,
                                        intent.context,
                                        trace,
                                        step,
                                    )
                                    if git_result:
                                        final_commit = git_result
                                        intent.context["code_changes"] = {
                                            file_change.path: file_change.content
                                            for file_change in fix_output.files
                                        }
                                        output = agent.execute(intent.context)
                                        logger.info("  🔁 Re-running code review after auto-fix...")
                                    else:
                                        logger.info("  ⚠️ Auto-fix git operations failed.")
                                else:
                                    logger.info(f"  ⚠️ Auto-fix failed: {fix_output.error}")

                    # Centralized failure detection for ALL agents
                    should_continue, error_message = self._check_agent_result(task.agent, output)
                    
                    if not should_continue:
                        # Agent failed or blocked - stop pipeline
                        
                        # Determine step status based on error type
                        if "BLOCKED" in error_message or "BLOCK" in error_message:
                            step_status = StepStatus.BLOCKED
                        else:
                            step_status = StepStatus.FAIL
                        
                        trace.update_step(
                            step_number=step.step_number,
                            status=step_status,
                            success=False,
                            error_message=error_message,
                        )
                        
                        agent_results.append(AgentExecutionResult(
                            agent=task.agent,
                            success=False,
                            output=output,
                            error=error_message,
                        ))
                        
                        trace.complete(PipelineStatus.PARTIAL, error_message)
                        
                        return PipelineResult(
                            intent_type=intent.type,
                            status="partial",
                            agent_results=agent_results,
                            error=error_message,
                            trace_id=trace_id,
                        )
                    
                    # Agent succeeded
                    trace.update_step(
                        step_number=step.step_number,
                        status=StepStatus.SUCCESS,
                        success=True,
                        output_summary=self._get_output_summary(task.agent, output),
                    )
                    
                    agent_results.append(AgentExecutionResult(
                        agent=task.agent,
                        success=True,
                        output=output,
                    ))
                    
                    # Extract commit hash if available
                    if hasattr(output, 'commit_hash') and output.commit_hash:
                        final_commit = output.commit_hash
                    
                    logger.info(f"✓ {task.agent} completed successfully")
                    
                except Exception as e:
                    # Execution error - update trace
                    trace.update_step(
                        step_number=len(trace.steps),
                        status=StepStatus.FAIL,
                        success=False,
                        error_message=str(e),
                    )
                    
                    agent_results.append(AgentExecutionResult(
                        agent=task.agent,
                        success=False,
                        error=str(e),
                    ))
                    
                    trace.complete(PipelineStatus.PARTIAL, f"Error executing {task.agent}: {str(e)}")
                    
                    # Stop pipeline on error
                    return PipelineResult(
                        intent_type=intent.type,
                        status="partial",
                        agent_results=agent_results,
                        final_commit=final_commit,
                        error=f"Error executing {task.agent}: {str(e)}",
                        trace_id=trace_id,
                    )
            
            # All agents succeeded
            trace.complete(PipelineStatus.SUCCESS)
            
            return PipelineResult(
                intent_type=intent.type,
                status="success",
                agent_results=agent_results,
                final_commit=final_commit,
                trace_id=trace_id,
            )
            
        except Exception as e:
            trace.complete(PipelineStatus.FAILED, f"Orchestration error: {str(e)}")
            
            return PipelineResult(
                intent_type=intent.type if isinstance(intent, Intent) else "unknown",
                status="failure",
                agent_results=[],
                error=f"Orchestration error: {str(e)}",
                trace_id=trace_id,
            )
    
    def _get_output_summary(self, agent_name: str, output: Any) -> str:
        """Generate a brief summary of agent output for tracing.
        
        Args:
            agent_name: Name of the agent
            output: Agent output object
            
        Returns:
            Brief summary string
        """
        if agent_name == "code_review_agent" and hasattr(output, 'decision'):
            return f"Decision: {output.decision.value}"
        elif agent_name == "testing_agent" and hasattr(output, 'status'):
            return f"Status: {output.status.value}, Tests: {output.passed_count}/{output.test_count}"
        elif hasattr(output, 'success'):
            return f"Success: {output.success}"
        else:
            return "Completed"
    
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
