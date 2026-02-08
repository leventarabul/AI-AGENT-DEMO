import os
import redis.asyncio as redis
import hashlib
import json
from dataclasses import asdict, is_dataclass
from typing import Optional, Dict, Any


class CacheManager:
    """Redis-based response caching for LLM API calls."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0", ttl: int = 3600):
        self.redis_url = redis_url
        self.ttl = ttl
        self.redis_client = None
    
    async def connect(self):
        """Establish Redis connection."""
        try:
            self.redis_client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5
            )
            # Test connection
            await self.redis_client.ping()
        except Exception as e:
            print(f"Warning: Could not connect to Redis: {e}")
            self.redis_client = None
    
    async def disconnect(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
    
    def _make_key(self, prompt: str, provider: str, model: str) -> str:
        """Generate cache key using MD5 hash."""
        key_data = f"{prompt}:{provider}:{model}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def get(self, prompt: str, provider: str, model: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached response."""
        if not self.redis_client:
            return None
        
        try:
            key = self._make_key(prompt, provider, model)
            cached = await self.redis_client.get(key)
            if cached:
                return json.loads(cached)
            return None
        except Exception as e:
            print(f"Cache get error: {e}")
            return None
    
    async def set(self, prompt: str, provider: str, model: str, response: Dict[str, Any]):
        """Store response in cache."""
        if not self.redis_client:
            return
        
        try:
            if is_dataclass(response):
                response = asdict(response)
            elif hasattr(response, "dict") and callable(getattr(response, "dict")):
                response = response.dict()
            elif hasattr(response, "__dict__") and not isinstance(response, dict):
                response = dict(response.__dict__)
            key = self._make_key(prompt, provider, model)
            await self.redis_client.setex(
                key,
                self.ttl,
                json.dumps(response)
            )
        except Exception as e:
            print(f"Cache set error: {e}")
    
    async def clear(self) -> int:
        """Clear all cached responses."""
        if not self.redis_client:
            return 0
        
        try:
            keys = await self.redis_client.keys("*")
            if keys:
                return await self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            print(f"Cache clear error: {e}")
            return 0
    
    async def health(self) -> bool:
        """Check Redis health."""
        if not self.redis_client:
            return False
        
        try:
            await self.redis_client.ping()
            return True
        except:
            return False
