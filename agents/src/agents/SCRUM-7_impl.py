# models/event.py
from pydantic import BaseModel
from typing import Optional

class Event(BaseModel):
    event_code: str
    customer_id: str
    transaction_id: str
    merchant_id: str
    amount: float
    transaction_date: str
    event_data: Optional[dict] = None
    channel: Optional[str] = None

# api_server.py
from fastapi import FastAPI
from models.event import Event

app = FastAPI()

@app.post("/events")
async def create_event(event: Event):
    # Save event to database with channel info
    event_dict = event.dict()
    event_dict.pop("channel")
    # Save event_dict and event.channel to database
    return {"status": "Event created successfully"}

# database.py
import asyncpg

async def save_event(event_dict, channel):
    conn = await asyncpg.connect(user='admin', password='admin123', database='crm_demo', host='localhost')
    await conn.execute("INSERT INTO events (event_data, channel) VALUES ($1, $2)", event_dict, channel)
    await conn.close()