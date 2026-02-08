"""Anthropic Claude LLM Client Implementation"""

import os
import logging
import aiohttp
from typing import Optional

try:
    from .base_client import BaseLLMClient, LLMResponse
except ImportError:
    from base_client import BaseLLMClient, LLMResponse

logger = logging.getLogger(__name__)


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude Client"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-opus-20240229",
        temperature: float = 0.7
    ):
        api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not provided")
        
        super().__init__(api_key, model, temperature)
        self.base_url = "https://api.anthropic.com/v1"
        self.headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
    
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """Generate text using Anthropic API"""
        
        temp = temperature if temperature is not None else self.temperature
        
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temp,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/messages",
                    json=payload,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status != 200:
                        error_data = await response.json()
                        raise Exception(f"Anthropic API error: {error_data}")
                    
                    data = await response.json()
                    
                    return LLMResponse(
                        text=data["content"][0]["text"],
                        model=self.model,
                        provider="anthropic",
                        token_count=data["usage"]["input_tokens"] + data["usage"]["output_tokens"],
                        input_tokens=data["usage"]["input_tokens"],
                        output_tokens=data["usage"]["output_tokens"],
                        stop_reason=data.get("stop_reason")
                    )
        
        except Exception as e:
            logger.error(f"Error calling Anthropic API: {e}")
            raise
    
    def count_tokens(self, text: str) -> int:
        """Approximate token count (rough estimate)"""
        # Rough estimate: 1 token ≈ 3.5 characters for Claude
        return len(text) // 3
    
    async def validate_connection(self) -> bool:
        """Validate Anthropic API connection"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model,
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": "ping"}]
                }
                
                async with session.post(
                    f"{self.base_url}/messages",
                    json=payload,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Failed to validate Anthropic connection: {e}")
            return False
