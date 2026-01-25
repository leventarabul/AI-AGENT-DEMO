# AI Management Module

Centralized management of AI/LLM integrations, model configurations, and AI-powered features across the application ecosystem.

## Overview

The AI Management module provides:
- LLM provider abstractions (OpenAI, Claude, local models)
- Prompt management and templating
- Token counting and cost tracking
- Model configuration and switching
- Caching and optimization layers
- Integration with agents and other modules

## Repository Structure

```
ai-management/
├── src/
│   ├── models/
│   │   ├── openai_client.py        # OpenAI integration
│   │   ├── anthropic_client.py     # Claude integration
│   │   └── base_client.py          # Base LLM interface
│   ├── prompts/
│   │   ├── templates/
│   │   └── prompt_manager.py       # Prompt management
│   ├── cache/
│   │   └── cache_manager.py        # LLM response caching
│   └── config/
│       └── models_config.py        # Model configurations
├── docs/
│   ├── README.md
│   ├── supported-models.md         # Supported LLM models
│   └── integration-guide.md
├── tests/
├── requirements.txt
└── README.md
```

## Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/ai-management.git
cd ai-management

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env with your LLM API keys
```

## Quick Start

```python
from ai_management.models import OpenAIClient, AnthropicClient

# Initialize a client
client = OpenAIClient(api_key="your_api_key", model="gpt-4")

# Generate a response
response = client.generate(
    prompt="Analyze this campaign data...",
    temperature=0.7,
    max_tokens=500
)

print(response.text)
print(f"Tokens used: {response.token_count}")
```

## Supported Models

- OpenAI: GPT-4, GPT-3.5-turbo
- Anthropic: Claude 3 (Opus, Sonnet, Haiku)
- Local: Ollama, LLaMA models
- Open Source: Hugging Face models

## Features

- **Multi-Provider Support** - Switch between different LLM providers seamlessly
- **Prompt Management** - Organize and version prompts
- **Token Tracking** - Monitor token usage and costs
- **Response Caching** - Cache responses for identical prompts
- **Rate Limiting** - Built-in rate limiting
- **Error Handling** - Retry logic and fallback mechanisms

## Configuration

```env
# OpenAI
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4

# Anthropic
ANTHROPIC_API_KEY=your_key
ANTHROPIC_MODEL=claude-3-opus

# Local Models
LOCAL_MODEL_PATH=/path/to/model
```

## Documentation

- [Supported Models](docs/supported-models.md)
- [Integration Guide](docs/integration-guide.md)
- [API Reference](docs/api-reference.md)

## License

MIT
