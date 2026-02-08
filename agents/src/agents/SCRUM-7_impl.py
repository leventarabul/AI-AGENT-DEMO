# agents/src/clients/demo_domain_client.py

import httpx

async def register_event(channel: str, event_data: dict):
    url = "http://demo-domain-api:8000/events"
    payload = {
        "channel": channel,
        "event_data": event_data
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, auth=("admin", "admin123"))
        response.raise_for_status()

# demo-domain/src/demo-environment/api_server.py

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

class EventRequest(BaseModel):
    channel: str
    event_data: dict

@app.post("/events")
async def create_event(event_request: EventRequest):
    # Save event to database with channel information
    return {"message": "Event registered successfully"}