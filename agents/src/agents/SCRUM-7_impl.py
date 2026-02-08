from fastapi import FastAPI, HTTPException
import httpx

app = FastAPI()

DEMO_DOMAIN_URL = "http://demo-domain-api:8000"
AI_MANAGEMENT_URL = "http://ai-management-service:8001"

@app.post("/events")
async def create_event(event_data: dict):
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.post(f"{DEMO_DOMAIN_URL}/events", json=event_data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.json())

@app.post("/events/{event_id}/process")
async def process_event(event_id: int):
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.post(f"{DEMO_DOMAIN_URL}/events/{event_id}/process")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.json())

@app.post("/ai/generate")
async def generate_suggestion(prompt: str):
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.post(f"{AI_MANAGEMENT_URL}/generate", json={"prompt": prompt})
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.json())