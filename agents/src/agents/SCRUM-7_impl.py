import logging
from fastapi import FastAPI

logger = logging.getLogger(__name__)
app = FastAPI()

@app.post("/events")
async def create_event(event_data: dict):
    try:
        # Extract channel data from event payload
        channel = event_data.get("channel", "N/A")
        
        # Save event with channel information
        # Your code to save event with channel information
        
        return {"message": "Event created successfully with channel information"}
    except Exception as e:
        logger.error(f"Error creating event: {str(e)}")
        return {"message": "Failed to create event with channel information"}