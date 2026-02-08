# demo-domain/src/demo-environment/api_server.py

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

app = FastAPI()

class Event(BaseModel):
    event_code: str
    customer_id: str
    transaction_id: str
    merchant_id: str
    amount: float
    transaction_date: datetime
    event_data: Optional[dict] = {}

@app.post("/events")
async def create_event(event: Event):
    # Save event to database with channel info
    # For logging purposes only
    event.channel = "web"  # Assume channel info is passed in
    return {"message": "Event created successfully"}

# Update database schema
# Add a new column 'channel' to the events table
# This is a VARCHAR field for logging purpose, not used in business logic

# Modify the database insert query to include the 'channel' field when creating an event
# Update the schema definition in init.sql

# Add proper validation for the new 'channel' field in the Event model
# Ensure it's included in the request body and has a valid value