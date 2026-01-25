# Demo Domain - Campaign Management System

A complete campaign management system for testing and learning about event-driven architecture, rule matching, and earnings calculation.

## Project Structure

```
demo-domain/
├── docs/                          # Documentation
│   ├── DOCUMENTATION_RULES.md     # Language and publication guidelines
│   └── demo-setup/                # Demo environment setup guides
├── src/
│   └── demo-environment/          # Demo system implementation
│       ├── docker-compose.yml     # PostgreSQL container
│       ├── init.sql               # Database schema
│       ├── api_server.py          # FastAPI server
│       ├── job_processor.py       # Event processing worker
│       ├── requirements.txt       # Python dependencies
│       └── .env.example           # Environment template
├── .gitignore                     # Git ignore file (includes .env)
└── README.md                      # This file
```

## Related Modules

This is a standalone module. Related modules are managed separately:

- **[agents](https://github.com/yourusername/agents)** - Agent implementations that interact with demo-domain API
- **[ai-management](https://github.com/yourusername/ai-management)** - AI/LLM integration and management utilities

## Quick Start

### 1. Setup Environment

```bash
cd src/demo-environment
cp .env.example .env
# Edit .env with your credentials
```

### 2. Start Infrastructure

```bash
docker compose up -d      # Start PostgreSQL
pip install -r requirements.txt  # Install dependencies
python api_server.py      # Start API (Terminal 1)
python job_processor.py   # Start worker (Terminal 2)
```

### 3. Test the System

```bash
# Health check
curl -u your_api_user:your_api_password http://localhost:8000/health

# Create campaign
curl -u your_api_user:your_api_password -X POST http://localhost:8000/campaigns \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Campaign","description":"Test"}'

# Create campaign rule
curl -u your_api_user:your_api_password -X POST http://localhost:8000/campaigns/1/rules \
  -H "Content-Type: application/json" \
  -d '{
    "campaign_id":1,
    "rule_name":"Test Rule",
    "rule_condition":{"amount":100},
    "reward_amount":10
  }'

# Register event
curl -u your_api_user:your_api_password -X POST http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_code":"purchase",
    "customer_id":"cust_123",
    "transaction_id":"txn_001",
    "merchant_id":"merch_001",
    "amount":100,
    "transaction_date":"2024-01-25T10:00:00"
  }'
```

## Key Features

- **PostgreSQL Database** - Stores campaigns, rules, events, and earnings
- **FastAPI Server** - REST API with basic authentication
- **Job Processor** - Background worker for event processing
- **Rule Engine** - Dot-notation pattern matching
- **Event Streaming** - Queue-based event processing
- **Earnings Calculation** - Automatic reward distribution

## Architecture

```
Event Registration (API)
        ↓
    Pending Event
        ↓
  Job Processor (polls every 5 seconds)
        ↓
  Rule Matching Engine
        ↓
  Create Earnings / Update Event Status
```

## Security

- All credentials stored in environment variables (`.env`)
- Never commit sensitive data to git
- Basic authentication on all API endpoints
- Database credentials isolated in `.env`
- See [Security Configuration](docs/demo-setup/README.md#security-configuration) for details

## Documentation

- [Demo Setup Guide](docs/demo-setup/README.md) - Full setup and usage instructions
- [API Endpoints](docs/demo-setup/README.md#api-endpoints) - Available endpoints and examples
- [Database Schema](docs/demo-setup/README.md#database-schema) - Table structures
- [Documentation Rules](docs/DOCUMENTATION_RULES.md) - Writing and publication guidelines

## Using with Agents

To build agents that interact with this demo system:

1. Clone this repository to test the API
2. See [agents](https://github.com/yourusername/agents) module for agent implementations
3. Agents communicate with demo-domain API using basic authentication
4. Each agent can register events, query campaigns, and manage rules

## Database Connection

```bash
# Via environment variable
PGPASSWORD=your_password psql -h localhost -U admin -d campaign_demo

# Connection string
postgresql://admin:your_password@localhost:5432/campaign_demo
```

## Stopping the System

```bash
# Stop API and Job Processor (Ctrl+C in their terminals)

# Stop database
docker compose down

# Stop and remove all data
docker compose down -v
```

## Next Steps

- Read [Demo Setup Guide](docs/demo-setup/README.md) for detailed instructions
- Explore the database with your preferred SQL client
- Clone the [agents](https://github.com/yourusername/agents) module to build custom agents
- Publish your implementation details to Medium using [Documentation Rules](docs/DOCUMENTATION_RULES.md)

---

**Created:** January 25, 2026  
**Language:** English (documentation) - See [Documentation Rules](docs/DOCUMENTATION_RULES.md)
