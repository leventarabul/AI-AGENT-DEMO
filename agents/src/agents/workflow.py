from enum import Enum
from typing import Dict, Callable, Any


class TaskState(str, Enum):
    """Jira task workflow states."""
    DEVELOPMENT_WAITING = "Development Waiting"
    IN_PROGRESS = "In Progress"
    CODE_READY = "Code Ready"
    TEST_READY = "Test Ready"
    IN_REVIEW = "In Review"
    DONE = "Done"


class WorkflowTransition:
    """Represents a workflow transition with handler."""
    
    def __init__(
        self,
        from_state: TaskState,
        to_state: TaskState,
        transition_id: str,
        handler: Callable[..., Any],
    ):
        self.from_state = from_state
        self.to_state = to_state
        self.transition_id = transition_id
        self.handler = handler
    
    async def execute(self, issue_key: str, jira_client, **kwargs) -> None:
        """Execute handler and transition in Jira."""
        await self.handler(issue_key, jira_client, **kwargs)
        # Note: transition_id will be mapped from Jira instance configs
        # (different Jira instances have different transition IDs)


class TaskWorkflow:
    """Task workflow state machine."""
    
    def __init__(self):
        self.transitions: Dict[str, WorkflowTransition] = {}
    
    def register_transition(
        self,
        from_state: TaskState,
        to_state: TaskState,
        transition_id: str,
        handler: Callable[..., Any],
    ) -> None:
        """Register a state transition with handler."""
        key = f"{from_state.value}_{to_state.value}"
        self.transitions[key] = WorkflowTransition(
            from_state, to_state, transition_id, handler
        )
    
    async def execute_transition(
        self,
        issue_key: str,
        from_state: TaskState,
        to_state: TaskState,
        jira_client,
        **kwargs
    ) -> None:
        """Execute transition and handler."""
        key = f"{from_state.value}_{to_state.value}"
        if key not in self.transitions:
            raise ValueError(f"No transition registered: {key}")
        
        transition = self.transitions[key]
        await transition.execute(issue_key, jira_client, **kwargs)


# Default workflow sequence
DEFAULT_WORKFLOW_STATES = [
    TaskState.DEVELOPMENT_WAITING,
    TaskState.IN_PROGRESS,
    TaskState.CODE_READY,
    TaskState.TEST_READY,
    TaskState.IN_REVIEW,
    TaskState.DONE,
]
