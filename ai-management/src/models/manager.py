"""LLM Client Manager - Routes requests to appropriate provider"""

import os
import logging
from typing import Optional

try:
    from .base_client import BaseLLMClient, LLMResponse
    from .openai_client import OpenAIClient
    from .anthropic_client import AnthropicClient
except ImportError:
    from base_client import BaseLLMClient, LLMResponse
    from openai_client import OpenAIClient
    from anthropic_client import AnthropicClient

logger = logging.getLogger(__name__)


class LLMClientManager:
    """Manager for multiple LLM providers"""
    
    def __init__(self):
        self.clients = {}
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize available LLM clients"""
        
        # OpenAI
        if os.getenv("OPENAI_API_KEY"):
            try:
                self.clients["openai"] = OpenAIClient()
                logger.info("OpenAI client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}")
        
        # Anthropic
        if os.getenv("ANTHROPIC_API_KEY"):
            try:
                self.clients["anthropic"] = AnthropicClient()
                logger.info("Anthropic client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Anthropic client: {e}")
    
    def get_client(self, provider: Optional[str] = None) -> BaseLLMClient:
        """Get LLM client by provider"""
        
        if provider:
            if provider not in self.clients:
                raise ValueError(f"Provider '{provider}' not available or not configured")
            return self.clients[provider]
        
        # Return first available client
        if not self.clients:
            raise ValueError("No LLM providers configured")
        
        return list(self.clients.values())[0]
    
    async def generate(
        self,
        prompt: str,
        provider: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """Generate using specified or default provider"""
        
        client = self.get_client(provider)
        return await client.generate(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            system_prompt=system_prompt
        )
    
    async def validate_all(self) -> dict:
        """Validate all configured providers"""
        
        results = {}
        for provider, client in self.clients.items():
            try:
                is_valid = await client.validate_connection()
                results[provider] = {
                    "status": "healthy" if is_valid else "unhealthy",
                    "model": client.model
                }
            except Exception as e:
                results[provider] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return results
    
    def list_providers(self) -> list:
        """List available providers"""
        return list(self.clients.keys())
