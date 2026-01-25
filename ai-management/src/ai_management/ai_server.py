import os
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from manager import LLMClientManager
from cache_manager import CacheManager


app = FastAPI(title="AI Management Service", version="1.0.0")
llm_manager = LLMClientManager()
cache_manager = CacheManager(
    redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    ttl=int(os.getenv("CACHE_TTL", "3600"))
)


class GenerateRequest(BaseModel):
    prompt: str
    provider: str = "openai"
    model: Optional[str] = None
    max_tokens: int = 1000
    temperature: float = 0.7
    use_cache: bool = True


class GenerateResponse(BaseModel):
    text: str
    model: str
    provider: str
    token_count: int
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cached: bool


@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup."""
    await cache_manager.connect()


@app.on_event("shutdown")
async def shutdown_event():
    """Close connections on shutdown."""
    await cache_manager.disconnect()


@app.get("/health")
async def health():
    """Service health check."""
    cache_ok = await cache_manager.health()
    return {
        "status": "healthy",
        "service": "ai-management",
        "cache": "connected" if cache_ok else "disconnected"
    }


@app.get("/providers")
async def list_providers():
    """List available LLM providers."""
    return {
        "providers": llm_manager.list_providers()
    }


@app.post("/generate")
async def generate(request: GenerateRequest) -> GenerateResponse:
    """Generate text using specified LLM provider."""
    
    try:
        # Check cache first
        cached_response = None
        if request.use_cache:
            cached_response = await cache_manager.get(
                request.prompt,
                request.provider,
                request.model or llm_manager.get_client(request.provider).model
            )
            if cached_response:
                return GenerateResponse(**cached_response, cached=True)
        
        # Generate response
        response = await llm_manager.generate(
            prompt=request.prompt,
            provider=request.provider,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )
        
        # Cache the response
        if request.use_cache:
            await cache_manager.set(
                request.prompt,
                request.provider,
                response["model"],
                response
            )
        
        response["cached"] = False
        return GenerateResponse(**response)
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cache/clear")
async def clear_cache():
    """Clear the response cache."""
    cleared = await cache_manager.clear()
    return {
        "cleared_entries": cleared
    }


@app.get("/cache/health")
async def cache_health():
    """Check cache health."""
    is_healthy = await cache_manager.health()
    return {
        "cache_status": "healthy" if is_healthy else "unhealthy"
    }


if __name__ == "__main__":
    port = int(os.getenv("AI_SERVICE_PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
