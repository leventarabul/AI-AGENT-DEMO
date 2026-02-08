# models/event.py

from pydantic import BaseModel
from typing import Optional

class Event(BaseModel):
    event_code: str
    customer_id: str
    transaction_id: str
    merchant_id: str
    amount: float
    event_data: dict
    transaction_date: str
    channel: Optional[str]

# routes/events.py

from fastapi import APIRouter
from models.event import Event

router = APIRouter()

@router.post("/events")
async def create_event(event: Event):
    # Save event to database with channel info
    # event.channel is now available for logging purposes
    return {"message": "Event created successfully with channel info"}

# Update database schema (events table) to include the channel field
# Add channel field to the Event model in the database

# Update the data flow to include passing the channel info through the system
# Ensure proper validation and handling of the channel field throughout the process