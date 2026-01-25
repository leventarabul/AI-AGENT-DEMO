# Campaign Management System - Distributed Microservices

Complete campaign and event processing system with autonomous agents, built as independent microservices.

## 📋 Quick Start

```bash
# Start all services
docker compose up -d

# Check services
docker compose ps

# Test with example curl
curl -u admin:admin123 http://localhost:8000/health
```

## 🏗️ Architecture

3 independent services communicating via REST APIs:

### 1. **Demo Domain Service** (Port 8000)
Event registration and campaign rule matching engine.

- **Location:** `/demo-domain/`
- **Documentation:** `/demo-domain/docs/API_EXAMPLES.md`
- **Database:** PostgreSQL (campaigns, events, earnings, rules, job logs)
- **Key Features:**
  - Event registration with pending status
  - Rule-based event matching
  - Batch event processing with job execution logging
  - Job trigger via API endpoint

**Quick Curl:**
```bash
# Register event
curl -X POST -u admin:admin123 http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -d '{"event_code":"PURCHASE","customer_id":"CUST_001","transaction_id":"TXN_001",...}'

# Trigger job
curl -X POST -u admin:admin123 http://localhost:8000/admin/jobs/process-events
```

**See:** [API_EXAMPLES.md](demo-domain/docs/API_EXAMPLES.md)

---

### 2. **AI Management Service** (Port 8001)
Multi-provider LLM routing with response caching.

- **Location:** `/ai-management/`
- **Documentation:** `/ai-management/docs/README.md`
- **Providers:** OpenAI (GPT-4/3.5), Anthropic (Claude)
- **Cache:** Redis with MD5-based key hashing
- **Key Features:**
  - Provider abstraction and routing
  - Automatic response caching
  - Token counting per provider

**Quick Curl:**
```bash
# List providers
curl http://localhost:8001/providers

# Generate text
curl -X POST http://localhost:8001/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"...","provider":"openai","use_cache":true}'
```

**See:** [AI_MANAGEMENT_MODULE.md](ai-management/docs/AI_MANAGEMENT_MODULE.md)

---

### 3. **Agents Service** (Port 8002)
Autonomous agents for event registration and campaign management.

- **Location:** `/agents/`
- **Documentation:** `/agents/docs/README.md`
- **Clients:** DemoDomainClient, AIManagementClient
- **Key Features:**
  - Batch event registration
  - Campaign creation with AI enhancement
  - Graceful service fallback

**See:** [AGENTS_MODULE.md](agents/docs/AGENTS_MODULE.md)

---

## 📚 Documentation Structure

```
/projects
├── README.md                          ← You are here (overview)
├── docs/
│   ├── IMPLEMENTATION_GUIDE.md        ← System architecture & design
│   ├── PROJECT_ECOSYSTEM.md           ← Services overview
│   ├── SETUP.md                       ← Setup instructions
│   ├── SECURITY.md                    ← Authentication & security
│   └── CURL_COMMANDS.md               ← API curl examples
│
├── demo-domain/
│   ├── README.md                      ← Service setup
│   └── docs/
│       └── API_EXAMPLES.md            ← Curl commands & examples
│
├── ai-management/
│   ├── README.md                      ← Service setup
│   └── docs/
│       ├── README.md                  ← AI service documentation
│       └── AI_MANAGEMENT_MODULE.md    ← Detailed AI module docs
│
└── agents/
    ├── README.md                      ← Service setup
    └── docs/
        ├── README.md                  ← Agents documentation
        └── AGENTS_MODULE.md           ← Detailed agents module docs
```

## 🚀 Common Tasks

### Register and Process Event
```bash
# 1. Create campaign with rule
curl -X POST -u admin:admin123 http://localhost:8000/campaigns \
  -H "Content-Type: application/json" \
  -d '{"name":"Campaign","description":"...","start_date":"...","end_date":"..."}'

# 2. Add rule to campaign
curl -X POST -u admin:admin123 http://localhost:8000/campaigns/1/rules \
  -H "Content-Type: application/json" \
  -d '{"rule_name":"Rule","rule_condition":{"merchant_id":"MERCHANT_001"},"reward_amount":15.50}'

# 3. Register event
curl -X POST -u admin:admin123 http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -d '{"event_code":"PURCHASE","customer_id":"CUST_001",...}'

# 4. Trigger job processing
curl -X POST -u admin:admin123 http://localhost:8000/admin/jobs/process-events

# 5. Check event status
curl -u admin:admin123 http://localhost:8000/events/1
```

### View Job Execution Logs
```bash
# Get latest job logs
curl -u admin:admin123 'http://localhost:8000/admin/jobs/execution-logs?limit=5'

# Filter by status
curl -u admin:admin123 'http://localhost:8000/admin/jobs/execution-logs?status=completed&limit=10'
```

### Generate Text with AI
```bash
# Using OpenAI
curl -X POST http://localhost:8001/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explain loyalty programs",
    "provider": "openai",
    "model": "gpt-4",
    "max_tokens": 500,
    "use_cache": true
  }'

# Using Anthropic
curl -X POST http://localhost:8001/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explain loyalty programs",
    "provider": "anthropic",
    "use_cache": true
  }'
```

## 🔧 Configuration

### Environment Variables (`.env`)
```env
# Database
DB_PASSWORD=admin123
API_USERNAME=admin
API_PASSWORD=admin123

# AI Services (optional)
OPENAI_API_KEY=your_key
ANTHROPIC_API_KEY=your_key

# Redis
REDIS_URL=redis://redis:6379/0

# Service URLs (for inter-service communication)
DEMO_DOMAIN_URL=http://demo-domain-api:8000
AI_MANAGEMENT_URL=http://ai-management:8001
```

## 📊 Database Schema

**Demo Domain Service:**
- `campaigns` - Campaign metadata
- `campaign_rules` - Event matching rules
- `events` - Transaction events
- `earnings` - Generated rewards
- `job_execution_logs` - Job run history

## 🔑 Authentication

Most endpoints require HTTP Basic Auth:
```
Username: admin
Password: admin123
```

Exceptions:
- `GET /health` - No auth required
- `GET /providers` (AI Management) - No auth required

## 🚢 Deployment

### Development (Local)
```bash
cd /Users/levent/Documents/AI-Agent-demo
docker compose up -d
```

### Production Considerations
- [ ] Kubernetes deployment
- [ ] Secrets management (Vault)
- [ ] Monitoring & logging (Prometheus, ELK)
- [ ] Distributed tracing (Jaeger)
- [ ] Database backup strategy
- [ ] API rate limiting

## 📖 Full Documentation

For detailed information, see:
- **System Architecture:** [docs/IMPLEMENTATION_GUIDE.md](docs/IMPLEMENTATION_GUIDE.md)
- **Services Overview:** [docs/PROJECT_ECOSYSTEM.md](docs/PROJECT_ECOSYSTEM.md)
- **Setup Guide:** [docs/SETUP.md](docs/SETUP.md)
- **Security:** [docs/SECURITY.md](docs/SECURITY.md)
- **Curl Commands:** [docs/CURL_COMMANDS.md](docs/CURL_COMMANDS.md)
- **Demo Domain API:** [demo-domain/docs/API_EXAMPLES.md](demo-domain/docs/API_EXAMPLES.md)
- **AI Management:** [ai-management/docs/AI_MANAGEMENT_MODULE.md](ai-management/docs/AI_MANAGEMENT_MODULE.md)
- **Agents:** [agents/docs/AGENTS_MODULE.md](agents/docs/AGENTS_MODULE.md)

## ✅ Status

- ✅ Demo Domain Service - Production Ready
- ✅ AI Management Service - Production Ready
- ✅ Agents Service - Core Implementation Ready
- ✅ Docker Orchestration - Complete
- ✅ Integration Testing - Implemented
- 🔄 Kubernetes Deployment - Planned
- 🔄 Production Monitoring - Planned

## 📞 Support

Each service has its own README and documentation directory. Check the relevant folder for service-specific information.
