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
    channel: Optional[str]

@app.post("/events")
async def create_event(event: Event):
    # Save event to database with the new 'channel' field
    try:
        # Database logic to save the event
        return {"message": "Event created successfully with channel information"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create event")

# You can add more endpoints and business logic as needed