import logging
from fastapi import FastAPI, HTTPException
import httpx

logger = logging.getLogger(__name__)

app = FastAPI()

DEMO_DOMAIN_URL = "http://demo-domain-api:8000"
AI_MANAGEMENT_URL = "http://ai-management-service:8001"
OPENAI_API_KEY = "your_openai_api_key"

@app.post("/events")
async def create_event(event: dict):
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{DEMO_DOMAIN_URL}/events", json=event)
            resp.raise_for_status()
            event_id = resp.json()["id"]
            return {"event_id": event_id, "status": "pending"}
    except Exception as e:
        logger.error(f"Error creating event: {e}")
        raise HTTPException(status_code=500, detail="Error creating event")

@app.post("/admin/jobs/process-events")
async def trigger_event_processing():
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{DEMO_DOMAIN_URL}/admin/jobs/process-events")
            resp.raise_for_status()
            return {"status": "triggered", "message": "Event processing job started"}
    except Exception as e:
        logger.error(f"Error triggering event processing job: {e}")
        raise HTTPException(status_code=500, detail="Error triggering event processing job")

@app.get("/events/{event_id}")
async def get_event_details(event_id: int):
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{DEMO_DOMAIN_URL}/events/{event_id}")
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error(f"Error getting event details: {e}")
        raise HTTPException(status_code=500, detail="Error getting event details")