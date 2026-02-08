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
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post("http://ai-management:8001/generate", json={"prompt": event.channel})
            response.raise_for_status()
            event_data = response.json()["data"]
            
            # Save event with channel information
            # Insert event into the database with the channel field
            # Example database query: await database.insert_event(event, event_data, channel=event.channel)
            
            return {"status": "Event registered successfully", "event_data": event_data}
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail="AI Management error")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")