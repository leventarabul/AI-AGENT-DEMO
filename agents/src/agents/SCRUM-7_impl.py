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
    channel: str  # New field for channel information

@app.post("/events")
async def create_event(event: Event):
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # Call demo-domain API to save the event with channel information
            demo_domain_url = "http://demo-domain-api:8000"  # Use internal URL
            url = f"{demo_domain_url}/events/"
            headers = {"Content-Type": "application/json"}
            payload = event.dict()
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail="Demo Domain API Error")
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail="Demo Domain API Connection Error")