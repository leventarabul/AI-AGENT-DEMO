# demo-domain/src/demo-environment/api_server.py

from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

app = FastAPI()

class Event(BaseModel):
    event_code: str
    customer_id: str
    transaction_id: str
    merchant_id: str
    amount: float
    event_data: Optional[dict] = None
    transaction_date: datetime

@app.post("/events")
async def create_event(event: Event):
    # Save event to database with channel info
    # This channel field is for logging purposes only
    channel = "web"  # Default value
    if "channel" in event.event_data:
        channel = event.event_data["channel"]
        del event.event_data["channel"]  # Remove from event data
    # Save event with channel info
    return {"status": "pending", "channel": channel}