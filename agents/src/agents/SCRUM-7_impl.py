from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx

app = FastAPI()

class Event(BaseModel):
    event_code: str
    customer_id: str
    transaction_id: str
    merchant_id: str
    amount: float
    transaction_date: str
    event_data: dict
    channel: str

@app.post("/events")
async def create_event(event: Event):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post("http://demo-domain-api:8000/events", json=event.dict())
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.json()["detail"])
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail="Error communicating with demo-domain service")

@app.post("/admin/jobs/process-events")
async def trigger_event_processing():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post("http://demo-domain-api:8000/admin/jobs/process-events")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.json()["detail"])
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail="Error communicating with demo-domain service")