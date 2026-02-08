# agents/src/agents/SCRUM-7_impl.py

from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from httpx import AsyncClient

router = APIRouter()

class NewEvent(BaseModel):
    event_code: str
    customer_id: str
    transaction_id: str
    merchant_id: str
    amount: float
    channel: str
    transaction_date: str
    event_data: dict

@router.post("/events", response_model=dict)
async def create_event(event: NewEvent):
    async with AsyncClient(timeout=30) as client:
        try:
            response = await client.post("http://demo-domain-api:8000/events", json=event.dict())
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail="Error creating event in demo-domain")

# demo-domain/src/demo-environment/init.sql

ALTER TABLE events ADD COLUMN channel VARCHAR(255);