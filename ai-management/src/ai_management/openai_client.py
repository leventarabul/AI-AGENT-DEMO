import aiohttp
import json
import logging
from typing import Dict, Any
from base_client import BaseLLMClient

logger = logging.getLogger(__name__)


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
            "Authorization": f"Bearer {self.api_key[:20]}...",  # Masked for logging
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        # Print full request details
        api_url = f"{self.BASE_URL}/chat/completions"
        print("\n" + "="*100, flush=True)
        print("🔗 OPENAI API URL:", flush=True)
        print(api_url, flush=True)
        print("\n📤 OPENAI REQUEST (JSON):", flush=True)
        print(json.dumps(payload, indent=2, ensure_ascii=False), flush=True)
        print("="*100 + "\n", flush=True)
        
        async with aiohttp.ClientSession() as session:
            try:
                # Use real API key for actual request
                headers["Authorization"] = f"Bearer {self.api_key}"
                
                async with session.post(
                    api_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    response_data = await response.json() if response.content_type == 'application/json' else await response.text()
                    
                    if response.status != 200:
                        print("\n" + "="*100, flush=True)
                        print(f"❌ OPENAI API ERROR ({response.status}):", flush=True)
                        print(json.dumps(response_data, indent=2, ensure_ascii=False) if isinstance(response_data, dict) else response_data, flush=True)
                        print("="*100 + "\n", flush=True)
                        raise Exception(f"OpenAI API error: {json.dumps(response_data) if isinstance(response_data, dict) else response_data}")
                    
                    # Print full response
                    print("\n" + "="*100, flush=True)
                    print("📥 OPENAI RESPONSE (JSON):", flush=True)
                    print(json.dumps(response_data, indent=2, ensure_ascii=False), flush=True)
                    print("="*100 + "\n", flush=True)
                    
                    result = {
                        "text": response_data["choices"][0]["message"]["content"],
                        "model": self.model,
                        "provider": "OpenAI",
                        "token_count": response_data["usage"]["total_tokens"],
                        "input_tokens": response_data["usage"]["prompt_tokens"],
                        "output_tokens": response_data["usage"]["completion_tokens"]
                    }
                    
                    logger.info(f"✅ Generated: {result['text']}")
                    return result
            except Exception as e:
                print(f"\n❌ Exception: {str(e)}\n", flush=True)
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
