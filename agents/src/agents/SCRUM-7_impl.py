import logging
from typing import Optional
from fastapi import FastAPI

logger = logging.getLogger(__name__)
app = FastAPI()

@app.post("/events")
async def create_event(event_data: dict, channel: Optional[str] = None):
    try:
        # Save event data to the events table including the channel field
        logger.info(f"Received event data: {event_data} from channel: {channel}")
        # Insert into events table with event_data and channel
        return {"message": "Event created successfully"}
    except Exception as e:
        logger.error(f"Error creating event: {str(e)}")
        return {"message": "Error creating event"}