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
    event_data: Optional[dict]
    channel: str

@app.post("/events/")
async def create_event(event: Event):
    # Save event to database with channel information
    try:
        # Database operation to save event with channel info
        return {"message": "Event created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create event")