import aiohttp
import json
from typing import Dict, Any
from base_client import BaseLLMClient


class OpenAIClient(BaseLLMClient):
    """OpenAI GPT client implementation."""
    
    BASE_URL = "https://api.openai.com/v1"
    
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate text using OpenAI API."""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.BASE_URL}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"OpenAI API error: {error_text}")
                    
                    data = await response.json()
                    
                    return {
                        "text": data["choices"][0]["message"]["content"],
                        "model": self.model,
                        "provider": "OpenAI",
                        "input_tokens": data["usage"]["prompt_tokens"],
                        "output_tokens": data["usage"]["completion_tokens"],
                        "total_tokens": data["usage"]["total_tokens"]
                    }
            except Exception as e:
                raise Exception(f"OpenAI generation failed: {str(e)}")
    
    async def count_tokens(self, text: str) -> int:
        """Estimate token count (OpenAI: ~1 token per 4 chars)."""
        return len(text) // 4
    
    async def validate_connection(self) -> bool:
        """Validate OpenAI API connection."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
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
