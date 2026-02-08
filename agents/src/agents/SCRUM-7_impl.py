from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx

app = FastAPI()

class EventRequest(BaseModel):
    event_code: str
    customer_id: str
    transaction_id: str
    merchant_id: str
    amount: float
    transaction_date: str
    event_data: dict
    channel: str

@app.post("/events")
async def create_event(event: EventRequest):
    url = "http://localhost:8000/events"
    payload = event.dict()
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload, auth=("admin", "admin123"))
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail="Event registration failed")
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail="Error connecting to demo-domain service")