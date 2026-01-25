# Setup Guide - Campaign Management System

Complete step-by-step guide to deploy the entire distributed microservices system locally.

## 📋 Prerequisites

### System Requirements
- **OS:** macOS, Linux, or Windows with WSL2
- **Docker & Docker Compose:** v20.10+
  ```bash
  docker --version       # Docker version 20.10 or higher
  docker compose version # Docker Compose v2.0 or higher
  ```
- **Python:** 3.9+
  ```bash
  python3 --version
  ```
- **Git**
  ```bash
  git --version
  ```

### Check Prerequisites
```bash
# Verify all requirements are met
docker --version && docker compose version && python3 --version && git --version
```

---

## 🚀 Quick Start (5 minutes)

### 1. Clone Repository
```bash
cd /path/to/projects
git clone <your-repo-url> .
cd /Users/levent/Documents/AI-Agent-demo
```

### 2. Start All Services
```bash
# Start all containers (PostgreSQL, Redis, API services)
docker compose up -d

# Verify all services are running
docker compose ps
```

**Expected Output:**
```
NAME                  STATUS      PORTS
demo-domain-api       Up 2 sec    0.0.0.0:8000->8000/tcp
ai-management         Up 2 sec    0.0.0.0:8001->8001/tcp
postgres              Up 2 sec    0.0.0.0:5432->5432/tcp
redis                 Up 2 sec    0.0.0.0:6379->6379/tcp
```

### 3. Test the System
```bash
# Set credentials (from .env file)
export USERNAME=admin
export PASSWORD=admin123

# Test Demo Domain health
curl -u $USERNAME:$PASSWORD http://localhost:8000/health

# Test AI Management health
curl http://localhost:8001/health
```

✅ **If both services return `{"status":"ok"}`, you're ready!**

---

## 📖 Detailed Setup

### Step 1: Environment Configuration

#### A. Copy Environment Template
```bash
cp .env.example .env
```

#### B. Edit `.env` with Your Values

**Default values for local development:**
```env
# ==========================================
# DATABASE
# ==========================================
DB_PASSWORD=admin123
DB_USER=admin
DB_NAME=campaign_demo
DB_HOST=postgres          # Docker service name
DB_PORT=5432

# ==========================================
# API AUTHENTICATION
# ==========================================
API_USERNAME=admin
API_PASSWORD=admin123

# ==========================================
# AI SERVICE KEYS (Optional)
# ==========================================
OPENAI_API_KEY=          # Leave empty if no key
ANTHROPIC_API_KEY=       # Leave empty if no key

# ==========================================
# SERVICE URLS (Docker networking)
# ==========================================
DEMO_DOMAIN_URL=http://demo-domain-api:8000
DEMO_DOMAIN_USER=admin
DEMO_DOMAIN_PASSWORD=admin123
AI_MANAGEMENT_URL=http://ai-management:8001

# ==========================================
# REDIS (Caching)
# ==========================================
REDIS_URL=redis://redis:6379/0
CACHE_TTL=3600
```

**For Production:** Change `API_PASSWORD` and `DB_PASSWORD` to strong values.

### Step 2: Start Infrastructure

#### A. Start All Services
```bash
docker compose up -d
```

This starts:
- **PostgreSQL** (port 5432) - Event, campaign, rule, earnings, job log storage
- **Redis** (port 6379) - LLM response caching
- **Demo Domain API** (port 8000) - Event registration and processing
- **AI Management** (port 8001) - LLM routing and caching
- **Agents** (port 8002) - Optional autonomous agents

#### B. Monitor Startup
```bash
# Watch real-time logs
docker compose logs -f

# Or check specific service
docker compose logs demo-domain-api
```

#### C. Wait for Database Initialization
First run creates database schema. Wait ~10 seconds:
```bash
# Check if database is ready
docker exec demo-domain-postgres psql -U admin -d campaign_demo -c "SELECT COUNT(*) FROM campaigns;"
```

If this works, database is ready ✅

### Step 3: Verify Services Are Ready

```bash
# Check all containers running
docker compose ps

# Check API health endpoints
curl -u admin:admin123 http://localhost:8000/health
curl http://localhost:8001/health
```

**Expected Response:**
```json
{"status":"ok"}
```

---

## 🧪 Testing

### Test 1: Create Campaign
```bash
curl -X POST -u {USERNAME}:{PASSWORD} http://localhost:8000/campaigns \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Campaign",
    "description": "Test",
    "start_date": "2026-01-25T00:00:00",
    "end_date": "2026-12-31T23:59:59"
  }' | jq .
```

Note the campaign `id` (e.g., `1`)

### Test 2: Create Campaign Rule
```bash
# Replace {CAMPAIGN_ID} with ID from test 1
curl -X POST -u {USERNAME}:{PASSWORD} http://localhost:8000/campaigns/{CAMPAIGN_ID}/rules \
  -H "Content-Type: application/json" \
  -d '{
    "rule_name": "Test Rule",
    "rule_condition": {"merchant_id": "MERCHANT_001"},
    "reward_amount": 10.00,
    "rule_priority": 1
  }' | jq .
```

### Test 3: Register Event
```bash
curl -X POST -u {USERNAME}:{PASSWORD} http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_code": "PURCHASE",
    "customer_id": "CUST_001",
    "transaction_id": "TXN_'$(date +%s)'",
    "merchant_id": "MERCHANT_001",
    "amount": 100.00,
    "event_data": {"qty": 1},
    "transaction_date": "'$(date -u +'%Y-%m-%dT%H:%M:%SZ')'"
  }' | jq .
```

Note the event `id` (e.g., `1`)

### Test 4: Process Events
```bash
# Trigger job manually
curl -X POST -u {USERNAME}:{PASSWORD} http://localhost:8000/admin/jobs/process-events | jq .

# Wait 2 seconds
sleep 2

# Check event status (replace {EVENT_ID})
curl -u {USERNAME}:{PASSWORD} http://localhost:8000/events/{EVENT_ID} | jq '.status, .matched_rule_id'
```

**Expected:** Event status should be `processed` and `matched_rule_id` should be set ✅

### Test 5: View Job Logs
```bash
curl -u {USERNAME}:{PASSWORD} 'http://localhost:8000/admin/jobs/execution-logs?limit=5' | jq .
```

---

## 🔧 Common Operations

### View Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f demo-domain-api
docker compose logs -f ai-management

# Last 100 lines
docker compose logs --tail=100 demo-domain-api
```

### Stop Services
```bash
# Stop all containers (keeps data)
docker compose stop

# Stop and remove containers
docker compose down

# Stop and remove everything (WARNING: deletes data)
docker compose down -v
```

### Restart Services
```bash
# Restart all
docker compose restart

# Restart specific service
docker compose restart demo-domain-api
```

### Check Database
```bash
# Connect to PostgreSQL
docker exec -it demo-domain-postgres psql -U admin -d campaign_demo

# Inside psql:
\dt                    # List tables
SELECT * FROM events;  # Query events
SELECT * FROM job_execution_logs;  # View job logs
\q                     # Exit
```

### Run Integration Test
```bash
# From project root
cd tests
python integration_test.py
```

---

## 🐛 Troubleshooting

### "Connection refused" when accessing localhost:8000

**Problem:** Service hasn't started yet
```bash
# Solution: Check service status
docker compose ps

# Wait a few seconds and retry
docker compose logs demo-domain-api | tail -20
```

### "Database connection failed"

**Problem:** PostgreSQL not initialized
```bash
# Solution: Check postgres logs
docker compose logs postgres

# Reinitialize database
docker compose down -v
docker compose up -d
sleep 15  # Wait for initialization
```

### "Could not connect to Redis"

**Problem:** Redis service not running
```bash
# Solution: Restart redis
docker compose restart redis

# Verify
docker compose ps redis
```

### "401 Unauthorized" on API calls

**Problem:** Wrong credentials or missing authentication
```bash
# Verify you're using correct username and password
# Check .env file
cat .env | grep API_

# Retry with correct credentials
curl -u admin:admin123 http://localhost:8000/health
```

### Port Already in Use

**Problem:** Another service using port 8000, 8001, etc.
```bash
# Find process using port
lsof -i :8000

# Kill process (macOS/Linux)
kill -9 <PID>

# Or change port in docker-compose.yml
# Change "8000:8000" to "8100:8000" for example
```

### Event stays "pending" after job triggers

**Problem:** Rule condition doesn't match event data
```bash
# Check events
docker exec demo-domain-postgres psql -U admin -d campaign_demo \
  -c "SELECT id, status, event_data FROM events;"

# Check rules
docker exec demo-domain-postgres psql -U admin -d campaign_demo \
  -c "SELECT id, rule_name, rule_condition FROM campaign_rules;"

# Verify rule_condition matches event_data exactly
# Field names are case-sensitive!
```

### "No such file or directory: .env"

**Problem:** .env file doesn't exist
```bash
# Solution: Create from template
cp .env.example .env

# Or create manually with required variables
# See "Edit .env" section above
```

---

## 📊 Service Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Your Machine (localhost)                  │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────┐    ┌──────────────────┐               │
│  │ Demo Domain API  │    │ AI Management    │               │
│  │ :8000            │    │ :8001            │               │
│  └──────────────────┘    └──────────────────┘               │
│  - Campaigns               - OpenAI GPT                     │
│  - Events                  - Anthropic Claude              │
│  - Rules                   - Response Caching              │
│  - Job Processing                                          │
│                                                               │
│  ┌──────────────────┐    ┌──────────────────┐               │
│  │  PostgreSQL      │    │ Redis            │               │
│  │  :5432           │    │ :6379            │               │
│  └──────────────────┘    └──────────────────┘               │
│  - Persistent Storage      - LLM Cache                      │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 📚 Next Steps

1. **Read Documentation:**
   - [Architecture Guide](PROJECT_ECOSYSTEM.md)
   - [API Examples](demo-domain/docs/API_EXAMPLES.md)
   - [Security Guide](SECURITY.md)

2. **Run Integration Tests:**
   ```bash
   cd tests
   python integration_test.py
   ```

3. **Deploy Agents (Optional):**
   - See [agents/README.md](agents/README.md)

4. **Configure AI Keys (Optional):**
   - Get API key from [OpenAI](https://platform.openai.com)
   - Get API key from [Anthropic](https://console.anthropic.com)
   - Update `.env` with keys

---

## 🆘 Support

### Check Logs
```bash
# Full logs with timestamps
docker compose logs --timestamps -f

# Last 50 lines
docker compose logs --tail=50
```

### Health Check Script
```bash
#!/bin/bash
echo "=== Service Health Check ==="
echo "Demo Domain:"
curl -s -u admin:admin123 http://localhost:8000/health | jq .
echo "AI Management:"
curl -s http://localhost:8001/health | jq .
echo "PostgreSQL:"
docker compose exec -T postgres pg_isready -U admin
echo "Redis:"
docker compose exec -T redis redis-cli ping
```

---

## ✅ Verification Checklist

- [ ] Docker and Docker Compose installed
- [ ] Python 3.9+ installed
- [ ] `.env` file created and configured
- [ ] `docker compose up -d` completed successfully
- [ ] All 4 containers running (`docker compose ps`)
- [ ] `curl -u admin:admin123 http://localhost:8000/health` returns `{"status":"ok"}`
- [ ] `curl http://localhost:8001/health` returns `{"status":"ok"}`
- [ ] Campaign created successfully
- [ ] Event registered successfully
- [ ] Job triggered and event processed

✅ All checked? System is ready for use!
