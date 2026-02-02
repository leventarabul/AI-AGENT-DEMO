"""OpenAI LLM Client Implementation"""

import os
import logging
import aiohttp
from typing import Optional

from .base_client import BaseLLMClient, LLMResponse

logger = logging.getLogger(__name__)


class OpenAIClient(BaseLLMClient):
    """OpenAI GPT Client"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4",
        temperature: float = 0.7
    ):
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not provided")
        
        super().__init__(api_key, model, temperature)
        self.base_url = "https://api.openai.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """Generate text using OpenAI API"""
        
        import json
        
        temp = temperature if temperature is not None else self.temperature
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temp,
        }
        
        # Log request
        logger.info("\n" + "="*100)
        logger.info("📤 OPENAI REQUEST")
        logger.info("="*100)
        logger.info(f"URL: POST {self.base_url}/chat/completions")
        logger.info(f"\nPayload:\n{json.dumps(payload, indent=2)}")
        logger.info("="*100)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status != 200:
                        error_data = await response.json()
                        logger.error(f"\n❌ OPENAI ERROR (HTTP {response.status}):\n{json.dumps(error_data, indent=2)}")
                        raise Exception(f"OpenAI API error: {error_data}")
                    
                    data = await response.json()
                    
                    # Log response
                    logger.info("\n" + "="*100)
                    logger.info("📥 OPENAI RESPONSE")
                    logger.info("="*100)
                    logger.info(f"Status: {response.status} OK")
                    logger.info(f"\nFull Response:\n{json.dumps(data, indent=2)}")
                    logger.info("="*100)
                    
                    text = data["choices"][0]["message"]["content"]
                    logger.info(f"\n✅ Generated Text (first 500 chars):\n{text[:500]}")
                    logger.info("="*100 + "\n")
                    
                    return LLMResponse(
                        text=text,
                        model=self.model,
                        provider="openai",
                        token_count=data["usage"]["total_tokens"],
                        input_tokens=data["usage"]["prompt_tokens"],
                        output_tokens=data["usage"]["completion_tokens"],
                        stop_reason=data["choices"][0].get("finish_reason")
                    )
        
        except Exception as e:
            logger.error(f"\n❌ ERROR calling OpenAI API: {e}\n")
            raise
    
    def count_tokens(self, text: str) -> int:
        """Approximate token count (rough estimate)"""
        # Rough estimate: 1 token ≈ 4 characters
        return len(text) // 4
    
    async def validate_connection(self) -> bool:
        """Validate OpenAI API connection"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/models",
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Failed to validate OpenAI connection: {e}")
            return False
