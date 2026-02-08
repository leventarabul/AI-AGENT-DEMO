# agents/src/clients/demo_domain_client.py

from typing import Optional
from pydantic import BaseModel
import httpx

class EventChannelRequest(BaseModel):
    channel: str

async def register_event_with_channel(event_data: dict, channel: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post("http://demo-domain-api:8000/events", json=event_data)
        response.raise_for_status()
        
        event_id = response.json()["id"]
        
        channel_data = EventChannelRequest(channel=channel)
        await client.patch(f"http://demo-domain-api:8000/events/{event_id}", json=channel_data)
        
        return response.json()