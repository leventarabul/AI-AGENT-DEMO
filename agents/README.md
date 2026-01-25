# Agents Service

Autonomous agents that interact with demo-domain and ai-management services. Deploy as workers to automate event registration, campaign management, and AI-powered decision making.

## Features

- **Event Agent** - Register and manage events
- **Campaign Agent** - Create campaigns with AI-enhanced descriptions
- **Service Integration** - Seamlessly communicate with demo-domain and AI Management services
- **Error Handling** - Retry logic and graceful failure handling

## Architecture

```
┌──────────────────────────────────┐
│  Agents Service                  │
│  Port: 8002 (Optional workers)   │
├──────────────────────────────────┤
│  ┌───────────┐   ┌───────────┐  │
│  │   Event   │   │ Campaign  │  │
│  │   Agent   │   │   Agent   │  │
│  └───────────┘   └───────────┘  │
├──────────────────────────────────┤
│         Service Clients          │
├──────────────────────────────────┤
│  ↓                           ↓   │
│  demo-domain :8000     ai-mgmt :8001
│  (API)                  (LLM)
└──────────────────────────────────┘
```

## Setup

### Prerequisites

- Python 3.9+
- demo-domain service running on port 8000
- ai-management service running on port 8001 (optional)

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/agents.git
cd agents

# Create environment file
cp .env.example .env

# Edit .env with service URLs and credentials
vim .env

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Event Agent

```python
import asyncio
from src.agents.event_agent import EventAgent

async def main():
    agent = EventAgent()
    
    # Register single event
    response = await agent.register_event(
        event_code="purchase",
        customer_id="cust_123",
        transaction_id="txn_001",
        merchant_id="merch_001",
        amount=99.99
    )
    
    print(f"Event registered: {response['id']}")
    
    # Register multiple events
    events = [
        {
            "event_code": "purchase",
            "customer_id": f"cust_{i}",
            "transaction_id": f"txn_{i:04d}",
            "merchant_id": "merch_001",
            "amount": 50.0 + i,
        }
        for i in range(10)
    ]
    
    results = await agent.register_batch_events(events)
    print(f"Registered {len(results)} events")

asyncio.run(main())
```

### Campaign Agent

```python
import asyncio
from src.agents.campaign_agent import CampaignAgent

async def main():
    agent = CampaignAgent()
    
    # Create campaign
    campaign = await agent.create_campaign(
        name="January Promotion",
        description="Special promotion for January"
    )
    
    print(f"Campaign created: {campaign['id']}")
    
    # Create rule
    rule = await agent.create_rule(
        campaign_id=campaign['id'],
        rule_name="High Value Purchase",
        rule_condition={"amount": 100},
        reward_amount=25
    )
    
    print(f"Rule created: {rule['id']}")
    
    # Create campaign with AI enhancement
    ai_campaign = await agent.create_campaign_with_ai_suggestion(
        name="Summer Sale",
        description="Promote summer products"
    )
    
    print(f"AI-enhanced campaign created: {ai_campaign['id']}")

asyncio.run(main())
```

## Configuration

```env
# Service URLs
DEMO_DOMAIN_URL=http://localhost:8000
AI_MANAGEMENT_URL=http://localhost:8001

# Demo Domain Credentials
DEMO_DOMAIN_USER=admin
DEMO_DOMAIN_PASSWORD=your_password

# Logging
LOG_LEVEL=INFO
```

## Knowledge Management

Static knowledge lives in `agents/docs/`:
- `SYSTEM_CONTEXT.md`: overall system context
- `API_CONTRACTS.md`: endpoints and payloads
- `CODE_PATTERNS.md`: common coding patterns
- `ARCHITECTURE.md`: env vars, networking, caching
- `DECISIONS.md`: key architecture decisions (ADRs)

Use `agents/src/knowledge/context_loader.py` to build rich prompts for tasks (e.g., Jira):

```python
from knowledge.context_loader import build_ai_prompt

prompt = build_ai_prompt(
    task_title="Implement reward calculation", 
    task_description="Separate transaction and reward amounts",
    labels=["backend", "fastapi"],
)
# pass `prompt` to ai-management /generate
```

## Jira Agent (Automated Development)

JiraAgent automates task development from Jira:
1. Receives webhook when task status → "Development Waiting"
2. Generates code using AI
3. Generates unit tests
4. Commits and pushes to feature branch
5. Creates pull request
6. Updates Jira task status

### Setup

```env
JIRA_URL=https://your-jira.atlassian.net
JIRA_USERNAME=your-email@example.com
JIRA_API_TOKEN=your-jira-api-token
GIT_REPO_PATH=/path/to/repo
AI_MANAGEMENT_URL=http://ai-management-service:8001
OPENAI_API_KEY=sk-proj-...
```

### Endpoints

- **POST /webhooks/jira** - Receive Jira webhook events
  - Filters: `status = "Development Waiting"`
  - Processes: code gen → tests → commit → PR → Jira update

### Example

```bash
# 1. Set up environment
export JIRA_URL="https://your-jira.atlassian.net"
export JIRA_USERNAME="you@example.com"
export JIRA_API_TOKEN="your-token"
export GIT_REPO_PATH="$(pwd)"

# 2. Send mock webhook
python examples/test_jira_webhook.py

# 3. Monitor background task (logs in agents container)
docker logs agents-service -f
```

After webhook is received:
- Task status updates to "In Progress"
- Code is generated and committed
- Tests are written
- PR is created
- Task status updates to "In Review"

## Code Review Agent (Automated Quality Control)

CodeReviewAgent automatically reviews code and decides: approve → Testing, or reject → Development Waiting.

### Workflow

1. Receives webhook when PR status → "In Review"
2. Analyzes code for:
   - **Code Quality**: Type hints, docstrings, patterns
   - **Security**: No hardcoded secrets, dangerous functions
   - **Testing**: Comprehensive tests, mocks, fixtures
   - **Patterns**: Async/await, error handling, no duplication
3. **If Approved** → Posts success comment, task transitions to "Testing"
4. **If Rejected** → Posts detailed issue list, task goes back to "Development Waiting"

### Endpoints

- **POST /webhooks/code-review** - Receive code review events
  - Filters: `status = "In Review"` or `"Code Ready"`
  - Returns: AI review decision with issues/approved items

### Example

```bash
# Send mock code review webhook
python examples/test_code_review_webhook.py

# Monitor review in logs
docker logs agents-service -f
```

**Review Results:**

✅ **Approved** → Comment with checklist items:
```
✅ CODE REVIEW PASSED

Code review approved by AI agent. Ready for testing.

Checked items:
- Code follows project patterns
- Error handling is proper
- No hardcoded secrets
- Functions are documented
- Tests are comprehensive

Next step: Automated testing will run...
```

❌ **Rejected** → Comment with issues to fix:
```
❌ CODE REVIEW NEEDS FIXES

The following issues were found:
1. Missing error handling in async function
2. Hardcoded database URL detected
3. Test coverage insufficient

Action required:
- Fix the issues listed above
- Commit and push fixes
- Re-submit for code review
```

## Running as Workers

### Event Registration Worker

```bash
python workers/event_worker.py
```

Polls a queue and registers events with demo-domain.

### Campaign Builder Worker

```bash
python workers/campaign_worker.py
```

Creates campaigns based on rules or AI suggestions.

## API Examples

### Register Event

```bash
# Using agent directly
python -c "
import asyncio
from src.agents.event_agent import EventAgent

asyncio.run(EventAgent().register_event(
    event_code='purchase',
    customer_id='cust_123',
    transaction_id='txn_001',
    merchant_id='merch_001',
    amount=99.99
))
"
```

### Create Campaign

```bash
python -c "
import asyncio
from src.agents.campaign_agent import CampaignAgent

campaign = asyncio.run(CampaignAgent().create_campaign(
    name='Test Campaign',
    description='Test Description'
))
print(campaign)
"
```

## Error Handling

- Automatic retry on transient failures
- Graceful fallback when AI service unavailable
- Comprehensive logging for debugging
- Circuit breaker patterns for service protection

## Documentation

- [Agent Architecture](docs/architecture.md)
- [Service Integration](docs/service-integration.md)
- [Worker Examples](docs/workers.md)

---

**Depends On:**
- demo-domain :8000
- ai-management :8001 (optional)

**Status:** Ready for deployment
