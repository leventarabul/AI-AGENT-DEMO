from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import httpx
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class Event(BaseModel):
    id: int
    name: str
    channel: Optional[str] = None

@router.post("/events/")
async def add_event(event: Event):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"http://localhost:8000/events/", json=event.dict())
            response.raise_for_status()
            
        logger.info('Event with id %s and channel %s has been successfully added.', event.id, event.channel)

        return response.json()

    except httpx.HTTPStatusError as exc:
        logger.error('Error while adding event with id %s and channel %s.', event.id, event.channel)
        raise HTTPException(status_code=400, detail=f"An error occurred while adding the event: {exc}")
    except Exception as e:
        logger.error('Unexpected error occurred while adding event with id %s and channel %s: %s', event.id, event.channel, e)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")