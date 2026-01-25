# Architecture Decisions

## ADR-001: Separate Transaction vs Reward Amounts
- Decision: `event.amount` = transaction; `earnings.amount` = reward
- Rationale: semantic clarity and reporting correctness

## ADR-002: Use Chat Completions Initially
- Decision: Prefer Chat Completions over Assistants for simplicity
- Rationale: Stateless, cheaper; adequate for per-task flows

## ADR-003: Full OpenAI Logging
- Decision: Log URL, request JSON, response JSON, usage
- Rationale: observability and debugging
