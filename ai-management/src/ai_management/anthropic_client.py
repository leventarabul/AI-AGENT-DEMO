import aiohttp
import json
from typing import Dict, Any
from base_client import BaseLLMClient


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude client implementation."""
    
    BASE_URL = "https://api.anthropic.com/v1"
    
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate text using Anthropic Claude API."""
        
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.BASE_URL}/messages",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Anthropic API error: {error_text}")
                    
                    data = await response.json()
                    
                    return {
                        "text": data["content"][0]["text"],
                        "model": self.model,
                        "provider": "Anthropic",
                        "input_tokens": data["usage"]["input_tokens"],
                        "output_tokens": data["usage"]["output_tokens"],
                        "total_tokens": data["usage"]["input_tokens"] + data["usage"]["output_tokens"]
                    }
            except Exception as e:
                raise Exception(f"Anthropic generation failed: {str(e)}")
    
    async def count_tokens(self, text: str) -> int:
        """Estimate token count (Claude: ~1 token per 3.5 chars)."""
        return len(text) // 3
    
    async def validate_connection(self) -> bool:
        """Validate Anthropic API connection."""
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{self.BASE_URL}/models",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    return response.status == 200
            except:
                return False
