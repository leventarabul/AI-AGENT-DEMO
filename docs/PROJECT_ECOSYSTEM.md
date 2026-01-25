# Project Ecosystem

This document describes the overall structure of the project ecosystem with separate, independent modules.

## Module Overview

### 1. Demo Domain (Foundation)
**Repository:** `demo-domain`  
**Purpose:** Standalone campaign management system for testing and learning

**Components:**
- PostgreSQL database with campaigns, rules, events, earnings
- FastAPI REST API with basic authentication
- Job processor for event handling and rule matching

**Use Case:** 
- Learn event-driven architecture
- Test agents and AI integrations
- Foundation for other modules

**Independence:** ✅ Fully standalone, no external dependencies (except Python libraries)

---

### 2. Agents (Integration Layer)
**Repository:** `agents`  
**Purpose:** AI-powered agents that interact with demo-domain API

**Components:**
- Event agents - Register and manage events
- Campaign agents - Create and manage campaigns
- Analysis agents - Query and analyze data
- MCP servers - Model Context Protocol implementations

**Dependencies:**
- ✅ demo-domain (API endpoint)
- ❌ ai-management (optional, for AI features)

**Use Cases:**
- Automate event registration
- Build intelligent campaign managers
- Analyze earnings and metrics
- Test rule matching logic

---

### 3. AI Management (Utility Module)
**Repository:** `ai-management`  
**Purpose:** Centralized LLM integration and management

**Components:**
- Multi-provider LLM clients (OpenAI, Claude, etc.)
- Prompt management and templating
- Token counting and cost tracking
- Response caching and optimization

**Dependencies:**
- ❌ demo-domain
- ❌ agents

**Use Cases:**
- Power AI features in agents
- Manage LLM integrations
- Track costs and usage
- Share prompts across projects

---

## Integration Patterns

### Pattern 1: Standalone Demo
```
User → demo-domain API → PostgreSQL
```
- No agents, no AI
- Pure event processing system

### Pattern 2: Agent-Driven Testing
```
User → agents (EventAgent) → demo-domain API → PostgreSQL
```
- Agents automate interactions
- No AI features yet

### Pattern 3: Full AI Stack
```
User → agents (with AI) → ai-management → LLM Provider
         ↓
      demo-domain API → PostgreSQL
```
- Agents use AI for intelligent decisions
- AI management handles LLM interactions

---

## Data Flow

### Event Processing Flow
```
1. Agent registers event via API
   POST /events
   
2. API stores event as 'pending'
   
3. Job Processor polls every 5 seconds
   
4. Processor matches event against rules
   
5. Matched rule → Create earnings record
   
6. Update event status to 'processed'
```

### Agent Decision Flow
```
1. Agent queries campaign data from API
   GET /campaigns
   
2. Agent sends data to AI model (optional)
   ai-management → OpenAI/Claude
   
3. AI generates rule recommendation
   
4. Agent creates campaign rule via API
   POST /campaigns/{id}/rules
   
5. Rule becomes active immediately
```

---

## Development Workflow

### Local Development Setup

```bash
# 1. Clone all repositories
git clone https://github.com/yourusername/demo-domain.git
git clone https://github.com/yourusername/agents.git
git clone https://github.com/yourusername/ai-management.git

# 2. Setup demo-domain
cd demo-domain/src/demo-environment
docker compose up -d
python api_server.py &
python job_processor.py &

# 3. Setup agents (optional)
cd agents
pip install -r requirements.txt
# Create .env with demo-domain API credentials

# 4. Setup ai-management (optional)
cd ai-management
pip install -r requirements.txt
# Create .env with LLM API keys
```

### Testing Workflow

```bash
# Test 1: Demo Domain standalone
curl -u user:pass http://localhost:8000/health

# Test 2: Agent interactions
python agents/examples/register_events.py

# Test 3: AI-powered agent
python agents/examples/intelligent_campaign_builder.py
```

---

## Module Independence

| Module | Requires | Requires | Requires | Status |
|--------|----------|----------|----------|--------|
|        | demo-domain | agents | ai-management | |
| **demo-domain** | - | ❌ | ❌ | ✅ Fully Standalone |
| **agents** | ✅ | - | ❌ | ✅ Opt-in AI |
| **ai-management** | ❌ | ❌ | - | ✅ Library |

---

## Future Modules

Additional modules that could extend the ecosystem:

- **Data Pipeline** - ETL processes for analytics
- **Dashboard** - Web UI for campaign management
- **Mobile App** - Mobile client for event registration
- **Webhooks** - Event webhooks for external systems
- **CLI Tool** - Command-line interface

---

## Documentation by Module

| Module | Setup | API | Architecture | Examples |
|--------|-------|-----|--------------|----------|
| **demo-domain** | [Setup](demo-domain/docs/demo-setup/README.md) | [API](demo-domain/docs/demo-setup/README.md#api-endpoints) | [Schema](demo-domain/docs/demo-setup/README.md#database-schema) | [Quick Start](demo-domain/README.md#quick-start) |
| **agents** | [Setup](AGENTS_MODULE.md) | [Integration](AGENTS_MODULE.md) | [Architecture](AGENTS_MODULE.md) | [Examples](AGENTS_MODULE.md) |
| **ai-management** | [Setup](AI_MANAGEMENT_MODULE.md) | [API](AI_MANAGEMENT_MODULE.md) | [Models](AI_MANAGEMENT_MODULE.md) | [Usage](AI_MANAGEMENT_MODULE.md) |

---

## Contributing

Each module has its own repository and contribution guidelines:

1. **demo-domain** - Core system, stable API
2. **agents** - Agent implementations, experimental
3. **ai-management** - LLM utilities, library-like

---

**Last Updated:** January 25, 2026  
**Status:** Planning Phase
