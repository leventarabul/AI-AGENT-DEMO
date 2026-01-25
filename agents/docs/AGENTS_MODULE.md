# Agents Module

Autonomous agents that interact with the demo-domain API to perform tasks like event registration, rule matching, and earnings analysis.

## Overview

The agents module contains implementations of agents that:
- Register events with the demo-domain API
- Create and manage campaigns and rules
- Query event and earnings data
- Automate testing and validation workflows

## Repository Structure

```
agents/
├── src/
│   ├── agents/
│   │   ├── event_agent.py          # Agent for event management
│   │   ├── campaign_agent.py       # Agent for campaign management
│   │   └── analysis_agent.py       # Agent for data analysis
│   ├── mcp_servers/                # MCP server implementations
│   └── examples/                   # Example scripts
├── docs/
│   ├── README.md                   # Agent documentation
│   ├── architecture.md             # Agent design patterns
│   └── examples/                   # Usage examples
├── tests/
├── requirements.txt
└── README.md
```

## Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/agents.git
cd agents

# Install dependencies
pip install -r requirements.txt

# Configure demo-domain connection
cp .env.example .env
# Edit .env with demo-domain API credentials
```

## Quick Start

```python
from agents.event_agent import EventAgent

agent = EventAgent(
    api_url="http://localhost:8000",
    username="your_api_user",
    password="your_api_password"
)

# Register an event
response = agent.register_event(
    event_code="purchase",
    customer_id="cust_123",
    transaction_id="txn_001",
    merchant_id="merch_001",
    amount=99.99,
    transaction_date="2024-01-25T10:00:00"
)

print(f"Event registered: {response['id']}")
```

## Available Agents

- **EventAgent** - Register and manage events
- **CampaignAgent** - Create and manage campaigns
- **AnalysisAgent** - Query and analyze data

## Documentation

- [Agent Architecture](docs/architecture.md)
- [API Integration Guide](docs/api-integration.md)
- [Examples](docs/examples)

## Dependencies

- demo-domain running API server
- Python 3.9+
- requests library
- python-dotenv

## License

MIT
