# Add a new field 'channel' to the Event model in the demo-domain service

# models/events.py
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
    status: str
    matched_rule_id: Optional[int]
    error_message: Optional[str]
    channel: Optional[str]

# Update the database schema to include the new 'channel' field in the events table

# init.sql
ALTER TABLE events ADD COLUMN channel TEXT;

# Update the event registration API endpoint to accept and store the 'channel' field

# api_server.py
from fastapi import FastAPI
from pydantic import BaseModel
from demo_domain_client import register_event

app = FastAPI()

class EventRequest(BaseModel):
    event_code: str
    customer_id: str
    transaction_id: str
    merchant_id: str
    amount: float
    event_data: dict
    transaction_date: str
    channel: str

@app.post("/events")
async def create_event(event_request: EventRequest):
    event_data = event_request.dict()
    channel = event_data.pop("channel")  # Remove 'channel' from event data
    event_id = await register_event(event_data)
    # Store the 'channel' in the database
    # For example: db.insert_event_channel(event_id, channel)

# Update the Event model in the agents service to include the 'channel' field

# models/events.py
class Event(BaseModel):
    event_code: str
    customer_id: str
    transaction_id: str
    merchant_id: str
    amount: float
    event_data: dict
    transaction_date: str
    channel: Optional[str]

# Update the EventAgent to include the 'channel' in the event data passed to the demo-domain service

# agents/event_agent.py
async def process_event(event_data: dict):
    channel = ...  # Get channel information
    event_data["channel"] = channel
    await send_event_to_demo_domain(event_data)