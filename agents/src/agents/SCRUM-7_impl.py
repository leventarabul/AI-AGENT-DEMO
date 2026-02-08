# agents/src/clients/demo_domain_client.py

import httpx

DEMO_DOMAIN_URL = "http://demo-domain-api:8000"

async def register_event(event_data: dict):
    async with httpx.AsyncClient() as client:
        url = f"{DEMO_DOMAIN_URL}/events"
        try:
            response = await client.post(url, json=event_data, auth=("admin", "admin123"))
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Error registering event: {e}")
            return None

# demo-domain/src/demo-environment/api_server.py

from fastapi import FastAPI
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
    channel: str

@app.post("/events")
async def create_event(event: Event):
    # Save event to database with channel info
    return {"message": "Event created successfully"}