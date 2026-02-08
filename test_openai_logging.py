#!/usr/bin/env python3
import asyncio
import httpx

async def test():
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "http://localhost:8001/generate",
            json={
                "prompt": "What is machine learning? Explain briefly.",
                "provider": "openai",
                "max_tokens": 150,
                "temperature": 0.7,
                "use_cache": False
            },
            timeout=60
        )
        print(f"Response status: {resp.status_code}")
        result = resp.json()
        print(f"\nGenerated text:\n{result.get('text', '')[:300]}")

asyncio.run(test())
