# agents/src/clients/demo_domain_client.py

import httpx

DEMO_DOMAIN_URL = "http://demo-domain-api:8000"

async def create_event(event_data: dict):
    async with httpx.AsyncClient(timeout=30) as client:
        url = f"{DEMO_DOMAIN_URL}/events"
        headers = {"Content-Type": "application/json"}
        response = await client.post(url, json=event_data, headers=headers, auth=("admin", "admin123"))
        response.raise_for_status()
        return response.json()

# demo-domain/src/demo-environment/api_server.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class Event(BaseModel):
    event_code: str
    customer_id: str
    transaction_id: str
    merchant_id: str
    amount: float
    transaction_date: str
    event_data: dict

@app.post("/events")
async def create_event(event: Event):
    # Add channel information to event data
    event.event_data["channel"] = "web"
    
    # Save event to demo-domain
    event_data = event.dict()
    event_response = await create_event(event_data)
    
    return event_response