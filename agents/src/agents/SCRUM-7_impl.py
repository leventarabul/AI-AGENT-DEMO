# Update the data model for events to include the new channel field
class Event(BaseModel):
    event_code: str
    customer_id: str
    transaction_id: str
    merchant_id: str
    amount: float
    event_data: Dict[str, Any]
    transaction_date: datetime
    channel: str  # New field for channel information

# Update the event registration endpoint to accept the channel field
@app.post("/events")
async def create_event(event: Event, channel: str):
    event.channel = channel
    # Save the event to the database with the channel information
    # Return the event details with the new channel field