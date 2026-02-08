# agents/src/clients/demo_domain_client.py

import httpx

DEMO_DOMAIN_URL = "http://demo-domain-api:8000"

async def register_event(event_data: dict):
    async with httpx.AsyncClient(timeout=30) as client:
        url = f"{DEMO_DOMAIN_URL}/events"
        headers = {"Content-Type": "application/json"}
        response = await client.post(url, headers=headers, json=event_data)
        response.raise_for_status()
        return response.json()


# demo-domain/src/demo-environment/api_server.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime

app = FastAPI()

class Event(BaseModel):
    event_code: str
    customer_id: str
    transaction_id: str
    merchant_id: str
    amount: float
    transaction_date: datetime
    event_data: dict

@app.post("/events")
async def create_event(event: Event):
    # Save event to database with additional channel field for logging
    event_data = event.dict()
    event_data["channel"] = "web"  # Example channel value
    # Insert into database logic here
    return {"status": "pending", "message": "Event registered successfully"}


# demo-domain/src/demo-environment/init.sql

ALTER TABLE events ADD COLUMN IF NOT EXISTS channel TEXT;