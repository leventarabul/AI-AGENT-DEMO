# Decision Rules

Intent-to-agent mappings. Deterministic, explicit, and version-controlled.

## Core Principle

Each intent type maps to a **sequence of agents** that will execute in order.
No conditional logic, no LLMs—pure routing rules.

## Rule Format

```
Intent Type: <intent_code>
Description: <what this intent does>
Agents: [agent_1 → agent_2 → agent_3]
Parallelizable: [Set of agent indices that can run concurrently]
Context Requirements: [What fields must be in the intent context]
```

---

## Rules

### register_event

**Description:** Register a transaction event for rule matching

**Agents:**
1. `event_agent` — Validate event data and register with demo-domain API

**Context Requirements:**
- `event_code` (str) — Type of event (e.g., "purchase")
- `customer_id` (str) — Customer identifier
- `transaction_id` (str) — Unique transaction identifier
- `merchant_id` (str) — Merchant identifier
- `amount` (float) — Transaction amount

**Parallelizable:** None (single agent)

---

### create_campaign

**Description:** Create a new campaign and add rules to it

**Agents:**
1. `campaign_agent` — Create campaign in demo-domain
2. `campaign_agent` — Add rules to the campaign

**Context Requirements:**
- `name` (str) — Campaign name
- `description` (str) — Campaign description
- `rules` (list) — List of rule definitions with `rule_name`, `rule_condition`, `reward_amount`

**Parallelizable:** None (must create campaign before adding rules)

**Execution Order:** Sequential (step 2 depends on step 1)

---

### analyze_earnings

**Description:** Query and analyze earnings data for a campaign

**Agents:**
1. `analysis_agent` — Query earnings data from demo-domain
2. `analysis_agent` — Generate analysis and summary

**Context Requirements:**
- `campaign_id` (int, optional) — Campaign to analyze (if omitted, analyze all campaigns)
- `start_date` (str, optional) — Start date for analysis
- `end_date` (str, optional) — End date for analysis

**Parallelizable:** None (must query before analyzing)

---

### review_code

**Description:** Review code changes and generate feedback

**Agents:**
1. `code_review_agent` — Review code and generate feedback

**Context Requirements:**
- `repository` (str) — Repository name or path
- `pull_request_id` (int, optional) — PR to review (if omitted, review current branch)
- `focus_areas` (list, optional) — Specific areas to focus on (e.g., "performance", "security")

**Parallelizable:** None (single agent)

---

### run_tests

**Description:** Run the test suite and collect results

**Agents:**
1. `testing_agent` — Run tests and collect results

**Context Requirements:**
- `test_suite` (str, optional) — Specific test suite to run (if omitted, run all)
- `environment` (str) — Test environment (e.g., "unit", "integration")

**Parallelizable:** None (single agent)

---

## Adding a New Rule

1. Define the intent type name (lowercase, snake_case)
2. List the agents in execution order
3. Specify which agents can run in parallel (if any)
4. Document required context fields
5. Add the rule to the DECISION_RULES dict in [decision_router.py](./decision_router.py)
6. Update this file
7. Merge via pull request (control plane changes require review)

## Change History

| Date | Rule | Change |
|------|------|--------|
| 2026-01-25 | register_event | Initial rule |
| 2026-01-25 | create_campaign | Initial rule |
| 2026-01-25 | analyze_earnings | Initial rule |
| 2026-01-25 | review_code | Initial rule |
| 2026-01-25 | run_tests | Initial rule |

## Validation

When a new intent arrives:
1. Check that the intent type exists in this rule set
2. Verify all required context fields are present
3. Return the agent sequence and parallelization groups
4. Do not execute agents; return the plan to the execution layer

If any required field is missing, raise `MissingContextError` with clear message.
