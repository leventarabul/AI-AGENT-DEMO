# Updated Database Schema
# Add a new field 'channel' to the events table

ALTER TABLE events
ADD COLUMN channel VARCHAR(255);

# API Endpoint to Register Event with Channel Information
# Update the POST /events endpoint in the FastAPI server

from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
import uuid

app = FastAPI()

class Event(BaseModel):
    event_code: str
    customer_id: str
    transaction_id: str
    merchant_id: str
    amount: float
    event_data: dict
    transaction_date: datetime
    channel: str

@app.post("/events")
async def create_event(event: Event):
    # Generate unique id for the event
    event_id = str(uuid.uuid4())

    # Add event to the database with channel information
    # Sample database insert query
    # INSERT INTO events (id, event_code, customer_id, transaction_id, merchant_id, amount, event_data, transaction_date, channel)
    # VALUES (event_id, event.event_code, event.customer_id, event.transaction_id, event.merchant_id, event.amount, event.event_data, event.transaction_date, event.channel);

    # Return the created event id
    return {"id": event_id, "status": "pending", "created_at": datetime.now()}

# This code assumes proper error handling and database connection setup.
# Logging and authentication/authorization mechanisms should also be implemented.