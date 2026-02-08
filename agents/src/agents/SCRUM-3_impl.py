from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import httpx

app = FastAPI()

class Event(BaseModel):
    event_code: str
    customer_id: str
    transaction_id: str
    merchant_id: str
    amount: float
    transaction_date: str
    event_data: Optional[dict]

@app.post("/events", response_model=dict)
async def create_event(event: Event):
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.post("http://ai-management-service:8001/generate", json={"prompt": \
            event.event_code})
            resp.raise_for_status()
            reward = resp.json()["reward"]
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail="AI service error")
        except (httpx.RequestError, httpx.TimeoutException) as e:
            raise HTTPException(status_code=500, detail="AI service unavailable")

        # Register event in demo-domain
        # This part is specific to the demo-domain API, please complete accordingly
        demo_domain_url = "http://demo-domain-api:8000"
        try:
            resp = await client.post(f"{demo_domain_url}/events", json=event.dict())
            resp.raise_for_status()
            event_id = resp.json()["id"]
            return {"event_id": event_id, "reward": reward}
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail="Demo-domain API error")
        except (httpx.RequestError, httpx.TimeoutException) as e:
            raise HTTPException(status_code=500, detail="Demo-domain API unavailable")