from fastapi import FastAPI, HTTPException
from typing import Optional

app = FastAPI()

@app.post("/events")
async def create_event(channel: Optional[str] = None):
    try:
        # Save event with channel info
        return {"message": "Event created successfully with channel info"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error creating event")

# You can add database queries and updates to save the channel information