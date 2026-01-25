# AI Management Service

Centralized LLM integration and management service. Routes requests to multiple LLM providers (OpenAI, Claude), manages caching with Redis, and provides a unified API.

## Features

- **Multi-Provider Support** - OpenAI GPT, Anthropic Claude
- **Response Caching** - Redis-based caching for identical prompts
- **Token Tracking** - Monitor token usage across providers
- **Health Checks** - Validate provider connectivity
- **Async Support** - Built with FastAPI for high concurrency

## Architecture

```
┌─────────────────────────────────────┐
│  AI Management Service (FastAPI)    │
│  Port: 8001                         │
├─────────────────────────────────────┤
│  ┌──────────────┐   ┌──────────────┐│
│  │  OpenAI GPT  │   │Claude Claude ││
│  │   Client     │   │   Client     ││
│  └──────────────┘   └──────────────┘│
├─────────────────────────────────────┤
│  ┌────────────────────────────────┐ │
│  │  Redis Cache Layer             │ │
│  │  (Response Caching)            │ │
│  └────────────────────────────────┘ │
└─────────────────────────────────────┘
```

## Setup

### Prerequisites

- Python 3.9+
- Redis (via Docker Compose)
- LLM API keys (OpenAI or Anthropic or both)

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/ai-management.git
cd ai-management

# Create environment file
cp .env.example .env

# Edit .env with your API keys
vim .env

# Install dependencies
pip install -r requirements.txt

# Start Redis
docker compose up -d

# Start AI Service
python ai_server.py
```

Service will be available at `http://localhost:8001`

## API Endpoints

### Health Check
```bash
GET /health
```

Check service and provider health status.

### Generate Text
```bash
POST /generate
Content-Type: application/json

{
  "prompt": "Explain machine learning",
  "provider": "openai",
  "max_tokens": 500,
  "temperature": 0.7,
  "use_cache": true
}
```

### List Providers
```bash
GET /providers
```

Get available LLM providers.

### Clear Cache
```bash
POST /cache/clear
```

Clear all cached responses.

### Cache Health
```bash
GET /cache/health
```

Check Redis connection status.

## Configuration

```env
# LLM Provider Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Redis
REDIS_URL=redis://localhost:6379/0

# Service
AI_SERVICE_PORT=8001
CACHE_TTL=3600  # 1 hour
```

## Usage Examples

### Python

```python
import httpx
import asyncio

async def generate():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8001/generate",
            json={
                "prompt": "Write a Python function for fibonacci",
                "provider": "openai",
                "max_tokens": 500
            }
        )
        print(response.json()["text"])

asyncio.run(generate())
```

### cURL

```bash
curl -X POST http://localhost:8001/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explain AI",
    "provider": "openai",
    "max_tokens": 500
  }'
```

## Supported Models

### OpenAI
- gpt-4
- gpt-4-turbo
- gpt-3.5-turbo

### Anthropic
- claude-3-opus-20240229
- claude-3-sonnet-20240229
- claude-3-haiku-20240307

## Performance

- **Response Caching** - Identical prompts return instantly from Redis
- **Async/Await** - High concurrency with FastAPI
- **Token Counting** - Track usage and costs
- **Connection Pooling** - Efficient API client management

## Stopping the Service

```bash
# Stop FastAPI server (Ctrl+C)

# Stop Redis
docker compose down

# Remove all data
docker compose down -v
```

## Documentation

- [API Reference](docs/api-reference.md)
- [Supported Models](docs/supported-models.md)
- [Integration Guide](docs/integration-guide.md)

---

**Port:** 8001  
**Status:** Ready to integrate with demo-domain and agents services
