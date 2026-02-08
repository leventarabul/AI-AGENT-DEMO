# agents/src/agents/SCRUM-7_impl.py

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

class Event(BaseModel):
    event_code: str
    customer_id: str
    transaction_id: str
    merchant_id: str
    amount: float
    event_data: dict
    channel: Optional[str] = None

class EventIn(BaseModel):
    event_code: str
    customer_id: str
    transaction_id: str
    merchant_id: str
    amount: float
    event_data: dict
    channel: Optional[str] = None

def create_event(event: EventIn):
    # Business logic to create event in database with channel information
    # Dummy implementation for demo purposes
    if event.channel:
        return {"status": "Event created with channel information"}
    else:
        return {"status": "Event created without channel information"}

# API Endpoints
router = APIRouter()

@router.post("/events/", response_model=Event)
async def create_event_endpoint(event: EventIn):
    result = create_event(event)
    if result:
        return event
    else:
        raise HTTPException(status_code=400, detail="Event creation failed")