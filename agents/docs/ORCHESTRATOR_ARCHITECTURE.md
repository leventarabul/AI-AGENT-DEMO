# Orchestrator Architecture

## Overview

The orchestrator is the **single deterministic authority** for agent execution in this system. It provides a centralized, predictable, and failure-resilient control plane for all multi-agent workflows.

## Core Principles

### 1. Single Entry Point
- **ONE orchestrator**: `orchestrator.Orchestrator` class
- All multi-agent workflows MUST go through `orchestrator.execute()`
- Agents MUST NOT call other agents directly
- Agents MUST NOT contain workflow logic

### 2. Decision vs Execution Separation
```
Intent → DecisionRouter → ExecutionPlan → Orchestrator → Agents
         (planning)                        (execution)
                                                ↓
                                          ExecutionTrace
                                          (observability)
                                                ↓
                                          JiraFeedback
                                          (SDLC loop)
                                ↓
                            LearningGate
                            (pattern detection)
```

**Learning Phase** (after execution):
- Analyzes ExecutionTrace for patterns
- Detects repeated failures
- Generates knowledge proposals
- NO autonomous learning (human approval required)

**Decision Phase** (`orchestrator.route()`):
- Takes an Intent
- Applies deterministic decision rules via `DecisionRouter`
- Returns `OrchestrationDecision` with `ExecutionPlan`
- No agent execution during this phase

**Execution Phase** (`orchestrator.execute()`):
- Takes the same Intent
- Re-routes to get ExecutionPlan
- Creates ExecutionTrace for observability
- Executes agents sequentially
- Records each step in trace
- Stops on first failure
- Completes trace with final status
- Returns `PipelineResult` with `trace_id`

**Tracing Phase** (parallel to execution):
- Creates trace at pipeline start
- Records each agent execution as a step
- Captures STARTED → SUCCESS/FAIL/BLOCKED transitions
- Stores trigger information
- Provides complete execution history

**Feedback Phase** (after execution):
- Retrieves trace from TraceStore
- Posts human-readable report to Jira
- Updates issue status based on result
- Closes the SDLC feedback loop

### 3. Deterministic Behavior
- **NO LLMs** in orchestration logic
- **NO randomness** in routing
- Decision rules are defined in `decision_router.DECISION_RULES` dict
- Same intent + same context = same execution plan (always)

### 4. Centralized Failure Handling
All agent failures are detected in ONE place: `Orchestrator._check_agent_result()`

Failure detection:
1. Check `output.success == False`
2. Check agent-specific failure conditions (e.g., CodeReviewAgent.decision == BLOCK)
3. Return `(should_continue, error_message)` tuple

Pipeline stops IMMEDIATELY on first failure.

### 5. Explicit Execution Plan
```python
@dataclass
class ExecutionPlan:
    intent_type: str
    tasks: List[AgentTask]  # Ordered list of agents to execute
    parallelizable: List[str]  # Which tasks can run in parallel (future)
    
@dataclass
class AgentTask:
    agent: str  # Agent type (e.g., "code_review_agent")
    task: str  # Human-readable task description
    required_context: List[str]  # What context this agent needs
```

## Current State

### Compliant Components

**orchestrator.py**:
- ✅ Single entry point via `execute()`
- ✅ Centralized failure handling in `_check_agent_result()`
- ✅ Sequential execution with stop-on-failure
- ✅ Clear separation: route() + execute()
- ✅ Execution tracing for every pipeline run

**execution_trace.py**:
- ✅ Structured trace model (ExecutionTrace, ExecutionStep, TriggerInfo)
- ✅ Step statuses: STARTED, SUCCESS, FAIL, BLOCKED
- ✅ Pipeline statuses: RUNNING, SUCCESS, PARTIAL, FAILED
- ✅ JSON-serializable, deterministic
- ✅ TraceStore for in-memory storage

**jira_feedback.py**:
- ✅ JiraFeedbackService for posting traces to Jira
- ✅ Human-readable comment generation
- ✅ Automatic status transitions (SUCCESS → Done, FAIL → Blocked)
- ✅ Single source of truth (uses ExecutionTrace)
- ✅ One-way communication (orchestrator-controlled)

**learning_gate.py**:
- ✅ PatternDetector for failure pattern detection
- ✅ LearningGate with threshold-based evaluation
- ✅ Deterministic confidence scoring
- ✅ Structured LearningProposal generation
- ✅ NO autonomous learning (human-in-the-loop)
- ✅ ProposalStore for tracking insights

**decision_router.py**:
- ✅ Deterministic DECISION_RULES dict
- ✅ No LLMs, no randomness
- ✅ Explicit ExecutionPlan objects
- ✅ Intent type → agent sequence mapping

**Agents** (development_agent, code_review_agent, testing_agent):
- ✅ Stateless execute() methods
- ✅ Return structured outputs
- ✅ No orchestration logic
- ✅ No cross-agent calls

### Legacy Components (Non-Compliant)

**jira_agent.py**:
- ❌ Contains orchestration logic in `process_task()`
- ❌ Hardcoded 6-step workflow: gen code → gen tests → commit → PR → comment → transition
- ❌ Calls other agents directly (DevelopmentAgent, CodeReviewAgent, TestingAgent)
- ❌ NOT using orchestrator.execute()

**ai_server.py**:
- ❌ TWO entry points: `/ai-events` (uses orchestrator) and `/webhooks/jira` (uses JiraAgent.process_task)
- ❌ Direct JiraAgent instantiation at line 77
- ❌ Bypasses orchestrator for Jira webhooks

**scheduler.py**:
- ❌ Lines 156-159 directly use JiraAgent
- ❌ Bypasses orchestrator

## Migration Plan

### Phase 1: Document Legacy (COMPLETE)
- ✅ Identify non-compliant components
- ✅ Document violations
- ✅ Create this architecture guide

### Phase 2: Add Orchestrator Path (Future)
1. Create `development_flow` intent type in decision_router
2. Map to ExecutionPlan with [development_agent, code_review_agent, testing_agent]
3. Add Jira context extraction helper
4. Test via new endpoint: `POST /orchestrator/development`

### Phase 3: Dual-Path Operation (Future)
- Keep JiraAgent for backward compatibility
- Add orchestrator path as alternative
- Test both paths in parallel
- Monitor for differences

### Phase 4: Deprecate JiraAgent (Future)
- Switch all traffic to orchestrator path
- Mark JiraAgent as deprecated
- Remove after 1 release cycle

## How to Add a New Agent

1. **Create the agent** in `agents/src/agents/`:
```python
class MyAgent:
    def execute(self, context: Dict[str, Any]) -> MyAgentOutput:
        # Your logic here
        return MyAgentOutput(success=True, ...)
```

2. **Register in orchestrator** (`orchestrator.py`):
```python
def _get_agent(self, agent_name: str):
    # ... existing agents ...
    elif agent_name == "my_agent":
        from agents.my_agent import MyAgent
        agent = MyAgent()
```

3. **Add decision rules** (`decision_router.py`):
```python
DECISION_RULES = {
    "my_intent": ExecutionPlan(
        intent_type="my_intent",
        tasks=[
            AgentTask(agent="my_agent", task="Do my task", required_context=["field1", "field2"])
        ],
        parallelizable=[]
    ),
    # ... existing rules ...
}
```

4. **Add failure checking** (if needed):
If your agent has specific failure conditions beyond `success=False`, add to `_check_agent_result()`:
```python
def _check_agent_result(self, agent_name: str, output: Any) -> tuple[bool, Optional[str]]:
    # ... existing checks ...
    
    # Check: MyAgent specific failure
    if agent_name == "my_agent" and hasattr(output, 'custom_status'):
        if output.custom_status == "FAILED":
            return False, f"MyAgent failed: {output.reason}"
    
    return True, None
```

## Testing

All orchestrator tests are in `tests/`:
- `test_orchestrator_sanity.py`: Basic routing and execution
- `test_code_review_agent.py`: CodeReviewAgent integration with orchestrator
- `test_integration.py`: End-to-end pipeline tests

Run tests:
```bash
cd agents
python -m pytest tests/ -v
```

## Decision Rules

Current intent types and their execution plans:

| Intent Type | Agents | Parallelizable | Context Required |
|------------|--------|----------------|------------------|
| `register_event` | event_agent | [] | event_type, event_data |
| `create_campaign` | campaign_agent | [] | campaign_name, target_users |
| `analyze_earnings` | campaign_agent | [] | period, filters |
| `review_code` | code_review_agent | [] | pull_request_url |
| `run_tests` | testing_agent | [] | test_suite_path |
| `development_flow` | development_agent → code_review_agent → testing_agent | [] | issue_key |

See `decision_router.py` for full definitions.

## Error Handling

### Agent Failures
When an agent fails:
1. `_check_agent_result()` detects failure
2. Pipeline stops immediately
3. `PipelineResult` returned with:
   - `status="partial"`
   - `error="[reason]"`
   - `agent_results=[all results so far]`

### Orchestration Errors
When orchestration itself fails:
1. Exception caught in `execute()`
2. `PipelineResult` returned with:
   - `status="failure"`
   - `error="Orchestration error: [details]"`
   - `agent_results=[]`

### Unknown Intent
When intent type is not recognized:
1. `route()` raises `UnknownIntentError`
2. Returns `OrchestrationDecision` with `status="error"`
3. `execute()` returns early with failure

## Key Files

- `agents/src/orchestrator/orchestrator.py`: Main orchestrator (494 lines)
- `agents/src/orchestrator/decision_router.py`: Decision rules (225 lines)
- `agents/src/orchestrator/execution_trace.py`: Execution tracing (315 lines)
- `agents/src/orchestrator/jira_feedback.py`: Jira feedback loop (225 lines)
- `agents/src/orchestrator/learning_gate.py`: Pattern detection & proposals (671 lines)
- `agents/src/orchestrator/types.py`: Data types (ExecutionPlan, AgentTask, etc.)
- `agents/docs/ORCHESTRATOR_ARCHITECTURE.md`: This document
- `agents/docs/EXECUTION_TRACING_REPORT.md`: Tracing implementation details
- `agents/docs/JIRA_FEEDBACK_LOOP.md`: Jira integration documentation
- `agents/docs/LEARNING_GATE.md`: Learning Gate implementation guide

## Contact

For questions about orchestrator architecture, see:
- Architecture decisions: `docs/DECISIONS.md`
- System context: `docs/SYSTEM_CONTEXT.md`
- API contracts: `docs/API_CONTRACTS.md`
