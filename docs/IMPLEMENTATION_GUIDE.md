# Microservices Architecture - Complete Implementation

## Overview

A distributed microservices architecture for campaign management and event processing with autonomous agents. Three independent services communicate via REST APIs with proper authentication, caching, and background processing.

## Services

### 1. Demo Domain Service (Port 8000)
**Purpose:** Core campaign management and event processing engine

**Technology Stack:**
- FastAPI + Uvicorn
- PostgreSQL (campaign data, events, earnings, rules)
- Background event processing with job polling

**Database Schema:**
- `campaigns` - Campaign metadata with status management
- `campaign_rules` - Event matching rules with priority-based evaluation
- `events` - Transaction events with rule matching status
- `earnings` - Generated rewards when rules are matched
- `configuration` - API credential storage

**Key Endpoints:**
```
GET  /health                              - Service health check
POST /campaigns                           - Create new campaign
POST /campaigns/{id}/rules               - Add rule to campaign
POST /events                             - Register transaction event
GET  /events/{id}                        - Get event details
```

**Authentication:** HTTP Basic Auth (configurable via environment)

**Key Features:**
- Automatic event processing via background job (5-second poll interval)
- Rule matching against transaction data with dot-notation field support
- Automatic earnings record creation when rules match
- Event status tracking: pending → processed/skipped

**Database Credentials:**
- Username: `admin`
- Password: `your_password` (via `DB_PASSWORD` env var)

### 2. AI Management Service (Port 8001)
**Purpose:** Centralized LLM provider abstraction with response caching

**Technology Stack:**
- FastAPI + Uvicorn
- Multi-provider LLM clients (OpenAI, Anthropic)
- Redis caching layer (response-level with MD5 key hashing)

**Supported Providers:**
- OpenAI GPT-4 / GPT-3.5-turbo
- Anthropic Claude (claude-3-opus-20240229)

**Key Endpoints:**
```
GET  /health                     - Service health with cache status
GET  /providers                  - List available LLM providers
POST /generate                   - Generate text via specified provider
POST /cache/clear               - Clear all cached responses
GET  /cache/health              - Check Redis connection status
```

**Cache Configuration:**
- TTL: 3600 seconds (configurable via `CACHE_TTL`)
- Key format: MD5(prompt:provider:model)
- Storage: Redis backend with graceful degradation

**Request Example:**
```json
{
  "prompt": "Explain loyalty programs benefits",
  "provider": "openai",
  "model": "gpt-4",
  "max_tokens": 1000,
  "temperature": 0.7,
  "use_cache": true
}
```

**Response Example:**
```json
{
  "text": "Loyalty programs...",
  "model": "gpt-4",
  "provider": "OpenAI",
  "token_count": 145,
  "input_tokens": 15,
  "output_tokens": 130,
  "cached": false
}
```

### 3. Agents Service (Port 8002)
**Purpose:** Autonomous agents for event registration and campaign management (planned)

**Technology Stack:**
- Python + AsyncIO
- HTTPx for async inter-service communication
- Service clients with configurable endpoints

**Service Clients:**
- `DemoDomainClient` - Event and campaign operations
- `AIManagementClient` - LLM generation requests

**Planned Agents:**
- `EventAgent` - Batch event registration and processing
- `CampaignAgent` - Campaign creation with AI-enhanced descriptions

## Inter-Service Communication

**Service Discovery & Networking:**
- Docker Compose named network (`app-network`)
- Service-to-service communication via container names:
  - `demo-domain-api:8000`
  - `ai-management:8001`
  - Internal DNS resolution within network

**Environment Variables for Service URLs:**
```
DEMO_DOMAIN_URL=http://demo-domain-api:8000
AI_MANAGEMENT_URL=http://ai-management:8001
```

## Running the System

### Prerequisites
- Docker and Docker Compose (v2.0+)
- Python 3.9+ (for testing scripts)

### Start Services
```bash
cd /Users/levent/Documents/AI-Agent-demo
docker compose up -d
```

### Check Service Health
```bash
# Demo Domain
curl -u admin:{PASSWORD} http://localhost:8000/health

# AI Management
curl http://localhost:8001/health

# AI Management providers
curl http://localhost:8001/providers
```

### Run Integration Test
```bash
python3 test_integration.py
```

### Stop Services
```bash
docker compose down
```

## Configuration

### Environment Variables (`.env`)
```
# Database
DB_PASSWORD=your_password
API_USERNAME=admin
API_PASSWORD=your_password

# OpenAI (optional)
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4

# Anthropic (optional)
ANTHROPIC_API_KEY=your_key_here
ANTHROPIC_MODEL=claude-3-opus-20240229

# Redis
REDIS_URL=redis://redis:6379/0
CACHE_TTL=3600
```

### Service-Specific Configuration
Each service has `.env.example` in its root directory showing required variables.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Network                        │
│                    (app-network)                         │
│                                                           │
│  ┌──────────────────────────────────────────────────┐   │
│  │          Demo Domain Service (8000)              │   │
│  │  ┌─────────────────────────────────────────────┐ │   │
│  │  │  FastAPI Server + Background Processor      │ │   │
│  │  │  • Event Registration                       │ │   │
│  │  │  • Rule Matching (5s polling)              │ │   │
│  │  │  • Earnings Generation                     │ │   │
│  │  └─────────────────────────────────────────────┘ │   │
│  │         ↓                                          │   │
│  │  ┌─────────────────────────────────────────────┐ │   │
│  │  │       PostgreSQL Database                   │ │   │
│  │  │  • campaigns, rules, events, earnings      │ │   │
│  │  └─────────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────┘   │
│                                                           │
│  ┌──────────────────────────────────────────────────┐   │
│  │      AI Management Service (8001)               │   │
│  │  ┌─────────────────────────────────────────────┐ │   │
│  │  │  FastAPI Server + LLM Provider Router       │ │   │
│  │  │  • OpenAI Client (GPT-4/3.5)               │ │   │
│  │  │  • Anthropic Client (Claude)               │ │   │
│  │  │  • Cache Management                        │ │   │
│  │  └─────────────────────────────────────────────┘ │   │
│  │         ↓                                          │   │
│  │  ┌─────────────────────────────────────────────┐ │   │
│  │  │       Redis Cache                           │ │   │
│  │  │  • Response Caching (MD5 keys)             │ │   │
│  │  │  • TTL: 3600s                              │ │   │
│  │  └─────────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────┘   │
│                                                           │
│  ┌──────────────────────────────────────────────────┐   │
│  │      Agents Service (8002) [PLANNED]            │   │
│  │  ┌─────────────────────────────────────────────┐ │   │
│  │  │  Event Agent + Campaign Agent               │ │   │
│  │  │  • Service Clients (AsyncIO)                │ │   │
│  │  │  • Autonomous Workers                       │ │   │
│  │  │  • Fallback Handling                        │ │   │
│  │  └─────────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────┘   │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

## Event Processing Flow

```
1. Client registers event via POST /events
   └─> EventData validation (FastAPI/Pydantic)
   └─> Insert into PostgreSQL (status: 'pending')
   └─> Schedule background task

2. Background job processor (5s interval)
   └─> Query pending events
   └─> Fetch active campaign rules
   └─> Match event against each rule
   └─> On match: Create earnings record, set status to 'processed'
   └─> On no match: Set status to 'skipped'

3. Client polls GET /events/{id}
   └─> Returns processed event with matched_rule_id
```

## Testing

### Integration Test
Full end-to-end test covering all 3 services:

```python
# Register campaign with rule
campaign = create_campaign("Spring Sale 2024")
rule = create_campaign_rule(campaign_id, merchant_id="MERCHANT_001")

# Register event matching the rule
event = register_event(merchant_id="MERCHANT_001", amount=150.00)

# Wait for processing
await asyncio.sleep(7)

# Verify event was processed and earnings created
event_result = get_event(event_id)
assert event_result['status'] == 'processed'
assert event_result['matched_rule_id'] is not None
```

Run with:
```bash
python3 test_integration.py
```

## Deployment

### Development Environment
- Running locally with `docker compose up -d`
- Services exposed on localhost:8000, :8001, :8002
- PostgreSQL on localhost:5432
- Redis on localhost:6379

### Production Considerations (Future)
- [ ] Kubernetes manifests with proper resource limits
- [ ] CI/CD pipeline with testing stages
- [ ] Monitoring and observability (Prometheus, Grafana, ELK)
- [ ] Distributed tracing (Jaeger/Zipkin)
- [ ] Secrets management (Vault, sealed secrets)
- [ ] API rate limiting and circuit breakers
- [ ] Database replication and backup strategy
- [ ] Load balancing and auto-scaling

## File Structure

```
/Users/levent/Documents/AI-Agent-demo/
├── docker-compose.yml              # Master orchestration
├── .env                            # Shared environment variables
├── .gitignore                      # Standard Python + env patterns
├── test_integration.py             # Full system test
├── PROJECT_ECOSYSTEM.md            # Architecture overview
│
├── demo-domain/
│   ├── Dockerfile
│   ├── README.md
│   └── src/demo-environment/
│       ├── api_server.py           # FastAPI endpoints
│       ├── job_processor.py        # Background event processor
│       ├── requirements.txt
│       ├── init.sql                # Database schema
│       └── .env.example
│
├── ai-management/
│   ├── Dockerfile
│   ├── README.md
│   └── src/ai_management/
│       ├── ai_server.py            # FastAPI endpoints
│       ├── base_client.py          # Abstract LLM interface
│       ├── openai_client.py        # OpenAI implementation
│       ├── anthropic_client.py     # Anthropic implementation
│       ├── manager.py              # Provider routing
│       ├── cache_manager.py        # Redis caching
│       ├── requirements.txt
│       └── .env.example
│
└── agents/
    ├── Dockerfile
    ├── README.md
    ├── src/
    │   ├── clients/
    │   │   ├── demo_domain_client.py   # HTTP client wrapper
    │   │   └── ai_management_client.py # HTTP client wrapper
    │   ├── agents/
    │   │   ├── event_agent.py          # Event operations [PLANNED]
    │   │   └── campaign_agent.py       # Campaign operations [PLANNED]
    │   └── requirements.txt
    └── .env.example
```

## Status

### ✅ Completed
- [x] Demo Domain service with PostgreSQL integration
- [x] Background event processing with rule matching
- [x] AI Management service with multi-provider support
- [x] Redis caching layer
- [x] Docker Compose orchestration
- [x] Integration testing framework
- [x] Documentation

### 🔄 In Progress
- [ ] Agents service full implementation
- [ ] Retry logic with exponential backoff
- [ ] Circuit breaker patterns

### ❌ Not Started
- [ ] Example worker scripts
- [ ] Kubernetes deployment
- [ ] Monitoring/observability setup
- [ ] API documentation generation (Swagger/OpenAPI)
- [ ] Advanced rule matching with operators ($gte, $in, etc.)

## Next Steps

1. **Implement Agents Service**
   - Complete EventAgent and CampaignAgent classes
   - Add batch processing capabilities
   - Implement graceful fallback for unavailable services

2. **Add Resilience**
   - Implement exponential backoff retry logic
   - Add circuit breaker patterns
   - Improve error handling and logging

3. **Enhance Rule Matching**
   - Support MongoDB-style operators ($gte, $lte, $in, etc.)
   - Add regex pattern matching
   - Support nested field queries

4. **Production Readiness**
   - Kubernetes manifests
   - Prometheus metrics collection
   - Distributed tracing
   - Comprehensive logging aggregation
   - Database backup and replication

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [PostgreSQL JSON Types](https://www.postgresql.org/docs/current/datatype-json.html)
- [Redis Python Client](https://redis-py.readthedocs.io/)
- [Docker Compose](https://docs.docker.com/compose/)
- [HTTPx Documentation](https://www.python-httpx.org/)
