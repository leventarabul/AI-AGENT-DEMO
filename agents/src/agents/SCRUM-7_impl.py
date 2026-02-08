# demo-domain/api_server.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
import httpx

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
    # Call ai-management service to generate suggestion
    async with httpx.AsyncClient() as client:
        response = await client.post("http://ai-management:8001/generate", json={"prompt": f"Channel: {event.channel}"})
        response.raise_for_status()
        suggestion = response.json()["suggestion"]

    # Save event with channel information
    # Replace this with actual DB saving logic
    event_info = f"Event saved with channel: {event.channel}"
    return {"message": event_info, "suggestion": suggestion}