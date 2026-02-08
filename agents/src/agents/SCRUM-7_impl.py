# Add a new field 'channel' to the events table in the database
ALTER TABLE events ADD COLUMN channel TEXT;

# Update the API endpoint to accept 'channel' field in the request body
@app.post("/events")
async def create_event(event: Event):
    # Extract the channel field from the request body
    channel = event.channel
    # Save the event to the database including the channel
    new_event = Event.create(event_code=event.event_code, customer_id=event.customer_id, transaction_id=event.transaction_id,
                             merchant_id=event.merchant_id, amount=event.amount, event_data=event.event_data, channel=channel)
    # Return the created event
    return new_event