# Authentication & Credentials Management

## 🔐 Overview

System uses HTTP Basic Authentication for API access. Credentials are managed via environment variables with database fallback.

## 📍 Credential Sources

### Priority Order:
1. **Environment Variables (.env file)** ← First preference
2. **Database Configuration Table** ← Fallback only

### Why This Approach?
- **Dev/Local:** Use `.env` for simplicity
- **Production:** Use environment variables or secrets management (Vault, sealed-secrets)
- **Fallback:** Database for dynamic credential updates without restart

---

## 🔑 Where Credentials Are Stored

### 1. Demo Domain Service (Port 8000)

**Credentials Location:**
- **Primary:** `.env` file
  ```env
  API_USERNAME=admin
  API_PASSWORD=admin123
  DB_PASSWORD=admin123
  ```

**Code Location:**
- `demo-domain/src/demo-environment/api_server.py` → `get_api_credentials()` function (line 93)
- Loads from environment → Falls back to database `configuration` table

**How It Works:**
```python
# 1. Try environment variables first
username = os.getenv('API_USERNAME')  # From .env
password = os.getenv('API_PASSWORD')  # From .env

# 2. If not found, query database
SELECT config_value FROM configuration 
WHERE config_key = 'api_username'
```

**Used For:**
- HTTP Basic Auth on all protected endpoints
- `/campaigns`, `/events`, `/admin/jobs/*` endpoints require auth
- Exception: `GET /health` - no auth required

---

### 2. Demo Domain Service - Database Credentials

**Location:**
- `docker-compose.yml` environment variables
- `demo-domain/src/demo-environment/api_server.py` (lines 25-29)

```python
db_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'campaign_demo'),
    'user': os.getenv('DB_USER', 'admin'),
    'password': os.getenv('DB_PASSWORD', 'admin123'),  # ← From .env
}
```

**Environment Variables:**
```env
DB_PASSWORD=admin123
DB_USER=admin
DB_NAME=campaign_demo
DB_HOST=postgres  # In Docker
```

---

### 3. AI Management Service (Port 8001)

**No Built-in Auth**, but manages LLM API keys:

```env
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
```

**Location:**
- `ai-management/src/ai_management/manager.py` (lines 14-24)
- Loads from environment variables during initialization

```python
openai_key = os.getenv("OPENAI_API_KEY", "").strip()
if openai_key:
    self.clients["openai"] = OpenAIClient(api_key=openai_key, ...)

anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
if anthropic_key:
    self.clients["anthropic"] = AnthropicClient(api_key=anthropic_key, ...)
```

**Public Endpoints:**
- `GET /health` - No auth
- `GET /providers` - No auth
- `POST /generate` - No auth

---

### 4. Agents Service

**Credentials Used:**
- Demo Domain credentials for inter-service communication
- AI Management URL (no credentials needed)

**Location:**
- `agents/src/clients/demo_domain_client.py` (lines 16-22)
- Constructor takes username/password or loads from env

```python
class DemoDomainClient:
    def __init__(
        self,
        base_url: str,
        username: str = "admin",  # Default from .env usually
        password: str = "admin123"  # Default from .env usually
    ):
        self.username = username
        self.password = password
```

**Usage:**
```python
client = DemoDomainClient(
    base_url=os.getenv('DEMO_DOMAIN_URL'),
    username=os.getenv('DEMO_DOMAIN_USER', 'admin'),
    password=os.getenv('DEMO_DOMAIN_PASSWORD', 'admin123')
)
```

---

## 📋 Complete .env Reference

```env
# ==========================================
# DATABASE CREDENTIALS
# ==========================================
DB_PASSWORD=admin123          # PostgreSQL password
DB_USER=admin                 # PostgreSQL username
DB_NAME=campaign_demo         # Database name
DB_HOST=postgres              # Host (localhost in dev, postgres in docker)
DB_PORT=5432                  # PostgreSQL port

# ==========================================
# API AUTHENTICATION
# ==========================================
API_USERNAME=admin            # Demo Domain API username
API_PASSWORD=admin123         # Demo Domain API password

# ==========================================
# AI SERVICE KEYS (Optional)
# ==========================================
OPENAI_API_KEY=               # Get from https://platform.openai.com
OPENAI_MODEL=gpt-4            # Default model
ANTHROPIC_API_KEY=            # Get from https://console.anthropic.com
ANTHROPIC_MODEL=claude-3-opus-20240229

# ==========================================
# REDIS CONFIGURATION
# ==========================================
REDIS_URL=redis://redis:6379/0
CACHE_TTL=3600                # Cache expiration in seconds

# ==========================================
# SERVICE URLS (Inter-service Communication)
# ==========================================
DEMO_DOMAIN_URL=http://demo-domain-api:8000
DEMO_DOMAIN_USER=admin
DEMO_DOMAIN_PASSWORD=admin123
AI_MANAGEMENT_URL=http://ai-management:8001
```

---

## 🔒 Security Checklist

| Item | Status | Notes |
|------|--------|-------|
| `.env` in `.gitignore` | ✅ YES | Never committed to git |
| `.env.example` committed | ✅ YES (template) | Shows structure without secrets |
| API credentials in code | ❌ NO | Always from environment |
| Database password in code | ❌ NO | Always from environment |
| API keys in code | ❌ NO | Always from environment |
| Default credentials in dev | ✅ OK | Only for local development |

---

## 🚀 Production Deployment

### Recommended Approach:
```bash
# Don't use .env files in production
# Use container orchestration secrets:

# Kubernetes
kubectl create secret generic api-credentials \
  --from-literal=API_USERNAME=produser \
  --from-literal=API_PASSWORD=securepass

# Docker Swarm
echo "securepass" | docker secret create api_password -
```

### Environment Variable Injection:
```yaml
# docker-compose.prod.yml
services:
  demo-domain-api:
    environment:
      API_USERNAME: ${API_USERNAME}  # Injected at runtime
      API_PASSWORD: ${API_PASSWORD}
      DB_PASSWORD: ${DB_PASSWORD}
```

---

## ⚠️ Important Notes

1. **Never commit `.env` to git** - Already in `.gitignore`
2. **Change default credentials in production** - Use strong passwords
3. **Use environment-specific configs** - `.env` for dev, secrets manager for prod
4. **Rotate API keys regularly** - Especially OpenAI/Anthropic keys
5. **Database fallback is optional** - Can be removed if using dedicated secrets manager

---

## 🔄 Changing Credentials

### Option 1: Update .env (Local Development)
```bash
# Edit .env file
API_PASSWORD=new_secure_password

# Restart containers
docker compose restart
```

### Option 2: Update Database (Runtime)
```bash
# Connect to database
docker exec demo-domain-postgres psql -U admin -d campaign_demo

# Update configuration table
UPDATE configuration 
SET config_value = 'new_password'
WHERE config_key = 'api_password';
```

### Option 3: Environment Variables (Production)
```bash
export API_USERNAME=newuser
export API_PASSWORD=newpass
docker compose up -d
```

---

## 🧪 Testing Authentication

```bash
# Correct credentials - Should work
curl -u admin:admin123 http://localhost:8000/health

# Wrong credentials - Should fail (401)
curl -u admin:wrongpass http://localhost:8000/health

# No credentials - Should fail (401)
curl http://localhost:8000/health
```
