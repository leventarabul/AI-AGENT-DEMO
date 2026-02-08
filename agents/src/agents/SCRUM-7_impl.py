# demo-domain/src/demo-environment/api_server.py

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
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post("http://ai-management-service:8001/events", json={"channel": event.channel})
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=500, detail="Error calling ai-management service")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")
    return {"status": "pending", "message": "Event created successfully"}

# Update the database schema to include the `channel` field in the events table
# Update the data model and request payload accordingly