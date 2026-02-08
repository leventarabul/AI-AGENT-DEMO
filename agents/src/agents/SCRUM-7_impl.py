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
    channel: str

@app.post("/events")
async def create_event(event: Event):
    # Save event to database with the new channel field
    try:
        # Database insert logic here
        return {"message": "Event created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error creating event")

# Ensure to update the database schema to include the new channel field in the events table