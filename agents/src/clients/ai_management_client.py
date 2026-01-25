"""Client for AI Management service"""

import logging
import httpx
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class AIManagementClient:
    """HTTP client for AI Management service"""
    
    def __init__(
        self,
        base_url: str = "http://localhost:8001",
        timeout: float = 60.0
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.client = httpx.AsyncClient(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.client:
            await self.client.aclose()
    
    async def health_check(self) -> bool:
        """Check service health"""
        try:
            if not self.client:
                self.client = httpx.AsyncClient(timeout=self.timeout)
            
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def generate(
        self,
        prompt: str,
        provider: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """Generate text using LLM"""
        
        payload = {
            "prompt": prompt,
            "provider": provider,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system_prompt": system_prompt,
            "use_cache": use_cache
        }
        
        try:
            # Ensure HTTP client is initialized
            if not self.client:
                self.client = httpx.AsyncClient(timeout=self.timeout)
            response = await self.client.post(
                f"{self.base_url}/generate",
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to generate text: {e}")
            raise
    
    async def list_providers(self) -> Dict[str, Any]:
        """List available LLM providers"""
        try:
            response = await self.client.get(f"{self.base_url}/providers")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to list providers: {e}")
            raise
