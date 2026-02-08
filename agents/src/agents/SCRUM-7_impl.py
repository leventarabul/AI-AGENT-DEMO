from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

class EventRequest(BaseModel):
    event_code: str
    customer_id: str
    transaction_id: str
    merchant_id: str
    amount: float
    transaction_date: str
    event_data: Optional[dict]
    channel: str

@app.post("/events")
async def create_event(event: EventRequest):
    # Save event with channel information
    try:
        # Save event to database with channel info
        return {"message": "Event created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")