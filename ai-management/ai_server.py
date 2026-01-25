"""AI Management Service - FastAPI Application"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from dotenv import load_dotenv

from src.models.manager import LLMClientManager
from src.cache.cache_manager import CacheManager

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize managers
llm_manager = LLMClientManager()
cache_manager = CacheManager()


# Lifespan context
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    try:
        await cache_manager.connect()
        logger.info("AI Management Service started")
    except Exception as e:
        logger.warning(f"Redis not available, caching disabled: {e}")
    
    yield
    
    # Shutdown
    await cache_manager.disconnect()
    logger.info("AI Management Service stopped")


# FastAPI app
app = FastAPI(
    title="AI Management Service",
    description="LLM routing, caching, and management service",
    version="1.0.0",
    lifespan=lifespan
)


# Pydantic models
class GenerateRequest(BaseModel):
    """Generate request model"""
    prompt: str
    provider: str = None
    max_tokens: int = 1000
    temperature: float = None
    system_prompt: str = None
    use_cache: bool = True


class GenerateResponse(BaseModel):
    """Generate response model"""
    text: str
    model: str
    provider: str
    token_count: int
    input_tokens: int
    output_tokens: int
    cached: bool = False


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    cache_health = await cache_manager.health()
    
    provider_health = {}
    try:
        provider_health = await llm_manager.validate_all()
    except Exception as e:
        logger.error(f"Error validating providers: {e}")
    
    return {
        "status": "healthy",
        "cache": "healthy" if cache_health else "unavailable",
        "providers": provider_health
    }


# Generate endpoint
@app.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest, authorization: str = Header(None)):
    """
    Generate text using specified LLM provider
    
    Supports caching to avoid duplicate requests.
    """
    
    try:
        # Check cache first
        cached_response = None
        if request.use_cache:
            cached_response = await cache_manager.get(
                request.prompt,
                request.provider or "default",
                llm_manager.get_client(request.provider).model
            )
        
        if cached_response:
            logger.info(f"Cache hit for prompt (first 50 chars): {request.prompt[:50]}...")
            return GenerateResponse(**cached_response, cached=True)
        
        # Generate new response
        llm_response = await llm_manager.generate(
            prompt=request.prompt,
            provider=request.provider,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            system_prompt=request.system_prompt
        )
        
        # Cache response
        response_dict = {
            "text": llm_response.text,
            "model": llm_response.model,
            "provider": llm_response.provider,
            "token_count": llm_response.token_count,
            "input_tokens": llm_response.input_tokens,
            "output_tokens": llm_response.output_tokens,
        }
        
        if request.use_cache:
            await cache_manager.set(
                request.prompt,
                request.provider or "default",
                llm_response.model,
                response_dict
            )
        
        return GenerateResponse(**response_dict, cached=False)
    
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Providers endpoint
@app.get("/providers")
async def list_providers():
    """List available LLM providers"""
    return {
        "providers": llm_manager.list_providers(),
        "count": len(llm_manager.list_providers())
    }


# Cache management
@app.post("/cache/clear")
async def clear_cache():
    """Clear all cached responses"""
    try:
        success = await cache_manager.clear()
        return {
            "status": "cleared" if success else "failed"
        }
    except Exception as e:
        logger.error(f"Cache clear error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cache/health")
async def cache_health():
    """Check cache health"""
    is_healthy = await cache_manager.health()
    return {
        "cache": "healthy" if is_healthy else "unhealthy"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
