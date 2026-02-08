# agents/src/clients/demo_domain_client.py

from typing import Optional
from pydantic import BaseModel
import httpx

class EventRequest(BaseModel):
    event_code: str
    customer_id: str
    transaction_id: str
    merchant_id: str
    amount: float
    transaction_date: str
    event_data: Optional[dict] = None
    channel: Optional[str] = None

async def register_event(event: EventRequest, base_url: str, auth: tuple):
    async with httpx.AsyncClient(timeout=30) as client:
        url = f"{base_url}/events"
        resp = await client.post(url, json=event.dict(), auth=auth)
        resp.raise_for_status()

# demo-domain/src/demo-environment/api_server.py

from fastapi import FastAPI
from agents.src.clients.demo_domain_client import register_event, EventRequest

app = FastAPI()

@app.post("/events")
async def create_event(event: EventRequest):
    # Process event
    await register_event(event, DEMO_DOMAIN_URL, (API_USERNAME, API_PASSWORD))
    return {"message": "Event registered successfully"}

# demo-domain/src/demo-environment/init.sql

ALTER TABLE events
ADD COLUMN channel VARCHAR;

# demo-domain/src/demo-environment/requirements.txt

httpx
pydantic