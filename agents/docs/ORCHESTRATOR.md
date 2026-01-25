# Agent Orchestrator

## Purpose

The orchestrator is the **control plane** for agent execution. It decides which agents should run and in what order—but does not execute them.

- **Deterministic:** Rules-based routing, no LLMs or randomness
- **Decoupled:** Decision logic separated from agent execution
- **Auditable:** Clear decision path for every intent
- **Maintainable:** Easy to add new intents and routes

## Architecture

```
Intent (user request)
    ↓
DecisionRouter
    ↓
AgentRegistry (lookup routing rules)
    ↓
ExecutionPlan (agents + parameters)
    ↓
Return decision (no execution)
```

## Components

### Intent
- Represents a high-level user request
- Contains type (e.g., `register_event`, `create_campaign`)
- Carries context (domain-specific parameters)
- Defined in [intent.py](../src/orchestrator/intent.py)

### DecisionRouter
- Accepts an Intent
- Looks up the routing rule
- Returns a DecisionResult
- No side effects, no LLM calls
- Defined in [router.py](../src/orchestrator/router.py)

### AgentRegistry
- Centralized repository of routing rules
- Maps intent types to execution sequences
- Defines which agents run and in what order
- Specifies parallel execution opportunities
- Defined in [registry.py](../src/orchestrator/registry.py)

### ExecutionPlan
- Ordered list of agent tasks
- Parameters for each agent
- Parallelization constraints
- Returned by the router, consumed by execution layer

## Usage Example

```python
from agents.src.orchestrator.intent import Intent, IntentType
from agents.src.orchestrator.router import DecisionRouter

# Create an intent
intent = Intent(
    type=IntentType.REGISTER_EVENT,
    context={
        "event_code": "purchase",
        "customer_id": "cust_123",
        "amount": 99.99,
    }
)

# Route it
router = DecisionRouter()
decision = router.route(intent)

# Inspect the decision
print(f"Agents to run: {decision.agents_to_run}")
print(f"Execution plan: {decision.execution_plan}")
print(decision.reasoning)

# Output:
# Agents to run: ['event_agent']
# Reasoning: Intent 'register_event' routed to:
#   1. event_agent: Validate event data and register with demo-domain
```

## Adding a New Intent

1. Add the intent type to `IntentType` enum in [intent.py](../src/orchestrator/intent.py)
2. Define the routing rule in `AgentRegistry.ROUTES` in [registry.py](../src/orchestrator/registry.py)
3. Specify agents in execution order
4. Mark which agent groups can run in parallel (if any)

Example:

```python
"new_intent": ExecutionPlan(
    intent_type="new_intent",
    sequence=[
        AgentTask(
            agent=AgentType.AGENT_A,
            task="Do something first",
            params={"action": "step1"}
        ),
        AgentTask(
            agent=AgentType.AGENT_B,
            task="Do something next",
            params={"action": "step2"}
        ),
    ],
    parallelizable=[],  # Sequential execution
),
```

## Key Principles

### No Agent Invocation
The router returns a plan. It does **not** call agents.
- Separation of concerns
- Testable in isolation
- Enables mock execution for testing

### No LLMs
Routing is deterministic and rule-based.
- Predictable behavior
- No hallucinations
- Fast and cheap to run

### No Side Effects
A routing decision has no impact on the system.
- Safe to call repeatedly
- Can be logged and audited
- No dependencies on external services

### Explicit Over Implicit
All rules are visible and editable.
- No hidden decision logic
- Changes require code review
- Failure modes are clear

## Execution vs. Decision

```
┌─────────────────────────────────────────┐
│         ORCHESTRATOR (This Module)      │
│                                         │
│  Intent → Router → ExecutionPlan        │
│          (Decision Only)                │
└────────────┬────────────────────────────┘
             │
             ↓
┌─────────────────────────────────────────┐
│       EXECUTION LAYER (Not Here)        │
│                                         │
│  ExecutionPlan → Agent Executor         │
│              → Call Agents              │
│              → Collect Results          │
└─────────────────────────────────────────┘
```

The orchestrator stops at the decision. Execution is the responsibility of a separate layer.

## Testing

Test the router without agents:

```python
from agents.src.orchestrator.intent import Intent, IntentType
from agents.src.orchestrator.router import DecisionRouter

router = DecisionRouter()

# Test routing decision
intent = Intent(
    type=IntentType.REGISTER_EVENT,
    context={"event_code": "purchase"}
)
decision = router.route(intent)

assert decision.agents_to_run == ["event_agent"]
assert len(decision.execution_plan.sequence) == 1
```

## Parallelization

Some intents can have agents run in parallel. The `ExecutionPlan.parallelizable` field specifies which agent indices (by position in `sequence`) can run concurrently.

Example: If agents 0 and 1 can run in parallel, and then agent 2 must wait:

```python
ExecutionPlan(
    ...
    sequence=[AgentA, AgentB, AgentC],
    parallelizable=[{0, 1}],  # Agents 0 and 1 run together
                               # Agent 2 waits for both to complete
)
```

## Future Extensions

- **Conditional routing:** Route based on intent context (e.g., campaign size)
- **Agent fallback:** Specify backup agents if primary fails
- **Timeout policies:** Define SLA per intent
- **Audit logging:** Log all routing decisions
- **Metrics:** Track which intents are routed most frequently

(Implement these as simple enhancements to the registry—no ML required.)
