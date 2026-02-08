# Add a new field 'channel' to the events table for logging purposes
# This field is not used in business logic

from typing import Optional
from pydantic import BaseModel

class EventLog(BaseModel):
    channel: Optional[str]

async def save_event_log(event_id: int, channel: str):
    # Function to save channel information for an event
    pass