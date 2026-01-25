# System Context

## Services
- demo-domain (8000): Event management and campaign rules
- ai-management (8001): LLM integration and caching layer
- agents (8002): Business logic orchestration (AI-powered)

## Data Flow
1. Agents receives an event request
2. Builds AI prompt with customer context
3. Calls ai-management `/generate` for suggestion
4. Registers event in demo-domain (transaction amount)
5. Returns suggested reward separately

## Key Business Rules
- `event.amount` stores the transaction total (paid by customer)
- `earnings.amount` stores the AI-suggested reward (benefit to customer)
- Do not mix transaction and reward amounts

## Tech Stack
- FastAPI (async)
- Python 3.11
- Redis (cache), PostgreSQL (demo data)
- OpenAI Chat Completions (gpt-4)
