# Update the events table schema to include a new field for channel
ALTER TABLE events ADD COLUMN channel TEXT;

# Update the API endpoint to accept and store the channel field
@app.post("/events")
async def create_event(event: EventCreate):
    event_data = event.dict()
    
    # Extract and store the channel field
    channel = event_data.pop("channel", None)
    
    # Save the event with the channel field
    new_event = await save_event(event_data, channel)
    return new_event

# Update the save_event function to include the channel field
async def save_event(event_data: dict, channel: str):
    new_event = Event(**event_data, channel=channel)
    await new_event.save()
    return new_event