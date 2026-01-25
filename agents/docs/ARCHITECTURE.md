# Architecture

## Environment Variables
- DEMO_DOMAIN_URL: internal URL for demo-domain (e.g., `http://demo-domain-api:8000`)
- AI_MANAGEMENT_URL: internal URL for ai-management (e.g., `http://ai-management-service:8001`)
- OPENAI_API_KEY: required by ai-management
- REDIS_URL: cache connection string (ai-management)

## Networking
- All services join `app-network` via docker-compose
- Use container names for inter-service DNS (not localhost)

## Caching
- ai-management caches LLM responses keyed by prompt
- Failures in cache must not break response generation
