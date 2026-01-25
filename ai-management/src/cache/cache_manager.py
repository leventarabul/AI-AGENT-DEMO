"""Cache layer for LLM responses using Redis"""

import os
import json
import hashlib
import logging
from typing import Optional
import redis
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class CacheManager:
    """Redis-based cache for LLM responses"""
    
    def __init__(self, redis_url: Optional[str] = None, ttl: int = 3600):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.ttl = ttl
        self.redis_client = None
    
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = await aioredis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("Connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
    
    def _generate_key(self, prompt: str, provider: str, model: str) -> str:
        """Generate cache key"""
        content = f"{prompt}:{provider}:{model}"
        hash_value = hashlib.md5(content.encode()).hexdigest()
        return f"llm:response:{hash_value}"
    
    async def get(self, prompt: str, provider: str, model: str) -> Optional[dict]:
        """Get cached response"""
        if not self.redis_client:
            return None
        
        try:
            key = self._generate_key(prompt, provider, model)
            cached = await self.redis_client.get(key)
            
            if cached:
                logger.debug(f"Cache hit for key: {key}")
                return json.loads(cached)
            
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    async def set(
        self,
        prompt: str,
        provider: str,
        model: str,
        response: dict,
        ttl: Optional[int] = None
    ) -> bool:
        """Cache response"""
        if not self.redis_client:
            return False
        
        try:
            key = self._generate_key(prompt, provider, model)
            ttl = ttl or self.ttl
            
            await self.redis_client.setex(
                key,
                ttl,
                json.dumps(response)
            )
            
            logger.debug(f"Cached response for key: {key}")
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def clear(self) -> bool:
        """Clear all LLM cache"""
        if not self.redis_client:
            return False
        
        try:
            cursor = 0
            pattern = "llm:response:*"
            deleted = 0
            
            while True:
                cursor, keys = await self.redis_client.scan(cursor, match=pattern)
                if keys:
                    deleted += await self.redis_client.delete(*keys)
                
                if cursor == 0:
                    break
            
            logger.info(f"Cleared {deleted} cache entries")
            return True
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False
    
    async def health(self) -> bool:
        """Check Redis health"""
        if not self.redis_client:
            return False
        
        try:
            await self.redis_client.ping()
            return True
        except Exception:
            return False
