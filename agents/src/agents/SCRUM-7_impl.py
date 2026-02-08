# Add a new field 'channel' to the Event model
from pydantic import BaseModel

class Event(BaseModel):
    event_code: str
    customer_id: str
    transaction_id: str
    merchant_id: str
    amount: float
    channel: str
    transaction_date: str
    event_data: dict

# Update the event registration endpoint to include 'channel' field
@app.post("/events")
async def create_event(event: Event):
    try:
        # Save event data to the database
        # Include the 'channel' field
        # Return the created event with proper status
    except Exception as e:
        logging.error(f"Error creating event: {str(e)}")
        return JSONResponse(status_code=500, content={"message": "Internal Server Error"})