# agents/src/agents/SCRUM-7_impl.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class EventChannel(BaseModel):
    channel: str

@router.post("/events/{event_id}/channel")
async def add_channel(event_id: int, channel_info: EventChannel):
    # Simulate updating event with channel info
    # Replace with actual database update logic
    if event_id < 1:
        raise HTTPException(status_code=404, detail="Event not found")
    
    return {"event_id": event_id, "channel": channel_info.channel}