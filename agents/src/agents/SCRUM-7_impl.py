import logging
from fastapi import FastAPI

# Initialize FastAPI app
app = FastAPI()

# Logger configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define API endpoint for receiving event channel information
@app.post("/event/channel")
async def receive_event_channel(channel: str):
    try:
        # Log the received channel information
        logger.info(f"Received event channel: {channel}")
        
        # Any additional business logic can be added here
        
        return {"message": "Event channel information received successfully"}
    except Exception as e:
        logger.error(f"Error processing event channel: {e}")
        return {"message": "Error processing event channel"}