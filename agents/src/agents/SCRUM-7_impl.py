# demo-domain/src/demo-environment/api_server.py

from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
import httpx

app = FastAPI()

class Event(BaseModel):
    event_code: str
    customer_id: str
    transaction_id: str
    merchant_id: str
    amount: float
    event_data: dict
    transaction_date: datetime

@app.post("/events")
async def create_event(event: Event):
    async with httpx.AsyncClient() as client:
        # Call the event registration service to save the event with channel info
        response = await client.post("http://demo-domain-api:8000/events", json=event.dict())
        response.raise_for_status()
        return response.json()