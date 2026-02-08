# agents/src/clients/demo_domain_client.py

import httpx
from typing import Optional

DEMO_DOMAIN_URL = "http://demo-domain-api:8000"

async def register_event(event_data: dict) -> Optional[dict]:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(f"{DEMO_DOMAIN_URL}/events", json=event_data)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            print(f"Error registering event: {e}")
            return None

# demo-domain/src/demo-environment/api_server.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

class Event(BaseModel):
    event_code: str
    customer_id: str
    transaction_id: str
    merchant_id: str
    amount: float
    transaction_date: str
    event_data: dict
    channel: Optional[str] = None

@app.post("/events")
async def create_event(event: Event):
    # Save event to database with channel information
    # For demonstration purposes, return the saved event
    return event