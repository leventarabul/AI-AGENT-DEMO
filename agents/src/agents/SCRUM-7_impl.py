# demo-domain/src/demo-environment/api_server.py

from fastapi import FastAPI, HTTPException
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
    transaction_date: datetime
    event_data: dict
    channel: Optional[str] = None

@app.post("/events")
async def create_event(event: Event):
    # Save event to database with channel information
    # Return event ID and status "pending"
    return {"id": 1, "status": "pending"}

# Add endpoint to update event channel if needed

# Add necessary error handling and logging