import os
from typing import Dict, Any, List, Optional
from base_client import BaseLLMClient
from openai_client import OpenAIClient
from anthropic_client import AnthropicClient


class LLMClientManager:
    """Manages multiple LLM providers and routes requests."""
    
    def __init__(self):
        self.clients: Dict[str, BaseLLMClient] = {}
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize available LLM clients from environment variables."""
        
        # OpenAI
        openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        if openai_key:
            self.clients["openai"] = OpenAIClient(
                api_key=openai_key,
                model=os.getenv("OPENAI_MODEL", "gpt-4")
            )
        
        # Anthropic Claude
        anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        if anthropic_key:
            self.clients["anthropic"] = AnthropicClient(
                api_key=anthropic_key,
                model=os.getenv("ANTHROPIC_MODEL", "claude-3-opus-20240229")
            )
    
    def get_client(self, provider: str = "openai") -> Optional[BaseLLMClient]:
        """Get a client for the specified provider."""
        return self.clients.get(provider.lower())
    
    def list_providers(self) -> List[Dict[str, str]]:
        """List available providers."""
        return [
            {
                "name": name,
                "model": client.model
            }
            for name, client in self.clients.items()
        ]
    
    async def validate_all(self) -> Dict[str, bool]:
        """Validate connections for all providers."""
        results = {}
        for name, client in self.clients.items():
            try:
                results[name] = await client.validate_connection()
            except:
                results[name] = False
        return results
    
    async def generate(
        self,
        prompt: str,
        provider: str = "openai",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate text using specified provider."""
        
        client = self.get_client(provider)
        if not client:
            raise ValueError(f"Provider '{provider}' not available. Available: {list(self.clients.keys())}")
        
        return await client.generate(prompt, max_tokens, temperature, **kwargs)
