# Add a new field 'channel' to the events table in the database
ALTER TABLE events ADD COLUMN channel VARCHAR(255);

# Update the API endpoint to accept 'channel' in the request payload
@app.post("/events")
async def create_event(event: Event):
    # Extract channel from the request payload
    channel = event.channel
    # Save the event to the database with the channel information

# Update the Event model to include the new 'channel' field
class Event(BaseModel):
    event_code: str
    customer_id: str
    transaction_id: str
    merchant_id: str
    amount: float
    transaction_date: datetime
    event_data: dict
    channel: str

# Update the database query to include the 'channel' field when inserting events
async def save_event_to_db(event: Event):
    query = events.insert().values(
        event_code=event.event_code,
        customer_id=event.customer_id,
        transaction_id=event.transaction_id,
        merchant_id=event.merchant_id,
        amount=event.amount,
        transaction_date=event.transaction_date,
        event_data=event.event_data,
        channel=event.channel
    )
    await database.execute(query)