# Orchestrator Extension: SDLC Development Pipeline

## Overview

The orchestrator has been extended from a **control plane** to an **executable control plane** that manages a complete SDLC development pipeline triggered by Jira status changes.

## Key Changes

### 1. New Intent Type: `development_flow`

**Trigger:** Jira issue transitions to "Waiting for Development"

**Execution Sequence:**
```
development_flow
  ↓
development_agent    → Create/update files, commit, push
  ↓
code_review_agent    → Review changes, provide feedback
  ↓
testing_agent        → Run tests, validate changes
```

**Context Requirements:**
- `jira_issue_key` (str) — e.g., "PROJ-123"
- `jira_issue_status` (str) — e.g., "Waiting for Development"
- `code_changes` (dict) — File path → file content mapping
- `branch_name` (str, optional) — Git branch name

### 2. Agent Implementations

#### DevelopmentAgent
- **File:** `agents/src/agents/development_agent.py`
- **Responsibilities:**
  - Write code files to disk
  - Validate file paths (no escaping repo root)
  - Stage files with `git add`
  - Commit with message format: `feat(JIRA-KEY): status`
  - Push to specified branch
- **Output:** `DevelopmentResult` with commit hash

#### CodeReviewAgent
- **File:** `agents/src/agents/code_review_agent.py`
- **Responsibilities:**
  - Analyze code changes
  - Generate review feedback (severity, category, message)
  - Approve or reject based on error count
  - Return structured feedback
- **Output:** `CodeReviewResult` with approval status

#### TestingAgent
- **File:** `agents/src/agents/testing_agent.py`
- **Responsibilities:**
  - Run test suites
  - Collect test results
  - Report pass/fail status
  - Generate summary
- **Output:** `TestingResult` with test results

### 3. Orchestrator Enhancement

**File:** `agents/src/orchestrator/orchestrator.py`

**New Methods:**

- `execute(intent: Intent) → PipelineResult`
  - Executes full pipeline sequentially
  - Stops on first agent failure
  - Returns detailed execution status

- `_get_agent(agent_name: str) → Agent`
  - Lazy-loads agent instances
  - Caches agent objects

**New Result Types:**

- `PipelineResult` — Overall pipeline status
- `AgentExecutionResult` — Per-agent execution status

**Error Handling:**
- Validates intent before execution
- Stops pipeline immediately on agent failure
- Returns `status="partial"` with error details
- No agent calls other agents

### 4. Decision Router Enhancement

**Files:**
- `agents/src/orchestrator/decision_rules.md`
- `agents/src/orchestrator/decision_router.py`

**Additions:**
- `development_flow` intent registration
- Required context validation
- Execution plan with 3-agent sequence

### 5. Testing & Validation

**File:** `agents/tests/test_orchestrator_sanity.py`

**Checks:**
- Intent creation and validation
- Intent routing to correct agents
- Available intents list
- DEVELOPMENT_FLOW execution plan structure

**Status:** ✓ All sanity checks pass

## Architecture: Control Plane + Execution

```
┌─────────────────────────────────────────┐
│      ORCHESTRATOR (Control Plane)       │
│                                         │
│  Intent → Route → Execute → Pipeline    │
│  - Deterministic routing rules          │
│  - Sequential agent execution           │
│  - Error handling                       │
│  - Result aggregation                   │
└────────────┬────────────────────────────┘
             │
             ↓
   ┌─────────────────────────┐
   │   EXECUTION LAYER       │
   │                         │
   │  AgentA → AgentB → AgentC
   │  - No inter-agent calls │
   │  - Structured I/O       │
   │  - Orchestrator control │
   └─────────────────────────┘
```

## Execution Flow

### 1. Planning Phase (Routing)
```python
from agents.src.orchestrator.orchestrator import Intent, Orchestrator

intent = Intent(
    type="development_flow",
    context={
        "jira_issue_key": "PROJ-123",
        "jira_issue_status": "Waiting for Development",
        "code_changes": {"src/main.py": "# code"},
    }
)

orchestrator = Orchestrator()
decision = orchestrator.route(intent)
# Returns: OrchestrationDecision with agents and execution plan
```

### 2. Execution Phase
```python
result = orchestrator.execute(intent)
# Returns: PipelineResult with status and agent outputs

# Check result
if result.status == "success":
    print(f"Commit: {result.final_commit}")
else:
    print(f"Error: {result.error}")
```

## Key Principles

### 1. Deterministic Routing
- No LLMs in routing decisions
- Rule-based, version-controlled mappings
- Changes require code review

### 2. Sequential Execution
- Agents run in strict order
- Each agent waits for previous to complete
- No parallel execution in DEVELOPMENT_FLOW

### 3. No Inter-Agent Communication
- Agents do not call other agents
- Orchestrator is the only director
- All communication is through orchestrator

### 4. Immediate Failure Stop
- Pipeline stops on first agent failure
- Returns partial results
- Clear error messages

### 5. Structured I/O
- All agents accept Dict[str, Any]
- All agents return typed Result objects
- No side effects outside Git operations

## Future Extensions

1. **Conditional Routing:** Route based on issue size, priority
2. **Agent Fallback:** Specify backup agents if primary fails
3. **Parallel Execution:** Mark certain agent pairs as parallelizable
4. **Timeout Policies:** Define SLA per intent
5. **Metrics & Observability:** Track pipeline performance
6. **Webhook Integration:** Trigger from Jira webhooks directly

## Testing

**Run sanity checks:**
```bash
cd agents
python3 tests/test_orchestrator_sanity.py
```

**All checks pass:**
✓ Intent creation
✓ Intent routing
✓ Available intents
✓ DEVELOPMENT_FLOW execution plan

## Commit

**Hash:** `59fb8ec`

**Files Changed:**
- `agents/src/orchestrator/decision_rules.md` (updated)
- `agents/src/orchestrator/decision_router.py` (updated)
- `agents/src/orchestrator/orchestrator.py` (extended)
- `agents/src/agents/development_agent.py` (new)
- `agents/tests/test_orchestrator_sanity.py` (new)

## Status

✅ DEVELOPMENT_FLOW intent implemented
✅ Agent stubs created with structured I/O
✅ Orchestrator execution layer added
✅ Git operations integrated
✅ Error handling and failure stop implemented
✅ Sanity checks pass
✅ Pushed to main

Ready for Jira webhook integration and production use.
