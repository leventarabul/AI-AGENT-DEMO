"""Execution tracing for orchestrator runs.

Provides structured, deterministic tracing of pipeline execution
for observability and debugging.

Key principles:
- Read-only: Traces don't affect execution
- Deterministic: Same execution = same trace
- Serializable: Easy to convert to JSON
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import json


class StepStatus(str, Enum):
    """Status of an execution step."""
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"


class PipelineStatus(str, Enum):
    """Overall pipeline status."""
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"  # Some agents succeeded before failure
    FAILED = "FAILED"    # Failed before any agent execution


@dataclass
class TriggerInfo:
    """Information about what triggered the pipeline."""
    source: str  # e.g., "jira_webhook", "manual", "scheduled"
    issue_key: Optional[str] = None
    issue_status: Optional[str] = None
    intent_type: Optional[str] = None
    timestamp: Optional[str] = None
    
    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()


@dataclass
class ExecutionStep:
    """A single step in the pipeline execution."""
    step_number: int
    agent_name: str
    agent_task: str
    status: StepStatus
    started_at: str
    completed_at: Optional[str] = None
    success: Optional[bool] = None
    error_message: Optional[str] = None
    output_summary: Optional[str] = None
    
    def __post_init__(self):
        """Set started_at if not provided."""
        if self.started_at is None:
            self.started_at = datetime.utcnow().isoformat()


@dataclass
class ExecutionTrace:
    """Complete trace of a pipeline execution.
    
    This is the top-level trace object that captures everything
    about a single orchestrator run.
    """
    trace_id: str
    trigger: TriggerInfo
    intent_type: str
    pipeline_status: PipelineStatus
    started_at: str
    completed_at: Optional[str] = None
    steps: List[ExecutionStep] = field(default_factory=list)
    final_error: Optional[str] = None
    execution_plan_summary: Optional[str] = None
    
    def __post_init__(self):
        """Set started_at if not provided."""
        if self.started_at is None:
            self.started_at = datetime.utcnow().isoformat()
    
    def add_step(
        self,
        agent_name: str,
        agent_task: str,
        status: StepStatus = StepStatus.STARTED,
    ) -> ExecutionStep:
        """Add a new step to the trace.
        
        Args:
            agent_name: Name of the agent being executed
            agent_task: Description of what the agent is doing
            status: Initial status (usually STARTED)
        
        Returns:
            The created ExecutionStep
        """
        step = ExecutionStep(
            step_number=len(self.steps) + 1,
            agent_name=agent_name,
            agent_task=agent_task,
            status=status,
            started_at=datetime.utcnow().isoformat(),
        )
        self.steps.append(step)
        return step
    
    def update_step(
        self,
        step_number: int,
        status: StepStatus,
        success: Optional[bool] = None,
        error_message: Optional[str] = None,
        output_summary: Optional[str] = None,
    ) -> None:
        """Update an existing step's status.
        
        Args:
            step_number: The step number to update (1-indexed)
            status: New status
            success: Whether the step succeeded
            error_message: Error message if failed
            output_summary: Brief summary of output
        """
        if step_number < 1 or step_number > len(self.steps):
            return
        
        step = self.steps[step_number - 1]
        step.status = status
        step.completed_at = datetime.utcnow().isoformat()
        
        if success is not None:
            step.success = success
        if error_message is not None:
            step.error_message = error_message
        if output_summary is not None:
            step.output_summary = output_summary
    
    def complete(
        self,
        pipeline_status: PipelineStatus,
        final_error: Optional[str] = None,
    ) -> None:
        """Mark the trace as complete.
        
        Args:
            pipeline_status: Final status of the pipeline
            final_error: Error message if pipeline failed
        """
        self.pipeline_status = pipeline_status
        self.completed_at = datetime.utcnow().isoformat()
        if final_error is not None:
            self.final_error = final_error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert trace to dictionary for JSON serialization.
        
        Returns:
            Dictionary representation of the trace
        """
        return asdict(self)
    
    def to_json(self, indent: int = 2) -> str:
        """Convert trace to JSON string.
        
        Args:
            indent: JSON indentation level
        
        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict(), indent=indent)
    
    def get_summary(self) -> str:
        """Get a human-readable summary of the trace.
        
        Returns:
            Multi-line summary string
        """
        lines = [
            f"Trace ID: {self.trace_id}",
            f"Intent: {self.intent_type}",
            f"Status: {self.pipeline_status.value}",
            f"Started: {self.started_at}",
        ]
        
        if self.completed_at:
            lines.append(f"Completed: {self.completed_at}")
        
        lines.append(f"\nExecution Steps ({len(self.steps)}):")
        for step in self.steps:
            status_icon = {
                StepStatus.STARTED: "⏳",
                StepStatus.SUCCESS: "✅",
                StepStatus.FAIL: "❌",
                StepStatus.BLOCKED: "🚫",
            }.get(step.status, "❓")
            
            lines.append(
                f"  {step.step_number}. {status_icon} {step.agent_name}: {step.status.value}"
            )
            
            if step.error_message:
                lines.append(f"     Error: {step.error_message}")
        
        if self.final_error:
            lines.append(f"\nFinal Error: {self.final_error}")
        
        return "\n".join(lines)


class TraceStore:
    """Simple in-memory store for execution traces.
    
    In production, this could be replaced with:
    - Database storage
    - File-based storage
    - Structured logging
    - Metrics/observability platform
    """
    
    def __init__(self):
        """Initialize the trace store."""
        self._traces: Dict[str, ExecutionTrace] = {}
    
    def store(self, trace: ExecutionTrace) -> None:
        """Store a trace.
        
        Args:
            trace: The trace to store
        """
        self._traces[trace.trace_id] = trace
    
    def get(self, trace_id: str) -> Optional[ExecutionTrace]:
        """Retrieve a trace by ID.
        
        Args:
            trace_id: The trace ID to retrieve
        
        Returns:
            The trace if found, None otherwise
        """
        return self._traces.get(trace_id)
    
    def get_all(self) -> List[ExecutionTrace]:
        """Get all stored traces.
        
        Returns:
            List of all traces
        """
        return list(self._traces.values())
    
    def get_recent(self, limit: int = 10) -> List[ExecutionTrace]:
        """Get the most recent traces.
        
        Args:
            limit: Maximum number of traces to return
        
        Returns:
            List of recent traces, most recent first
        """
        traces = sorted(
            self._traces.values(),
            key=lambda t: t.started_at,
            reverse=True,
        )
        return traces[:limit]
    
    def clear(self) -> None:
        """Clear all stored traces."""
        self._traces.clear()


# Global trace store instance
_trace_store = TraceStore()


def get_trace_store() -> TraceStore:
    """Get the global trace store instance.
    
    Returns:
        The global TraceStore
    """
    return _trace_store
