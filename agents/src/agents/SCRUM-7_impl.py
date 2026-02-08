# Add new field 'channel' to the Event model
class Event(BaseModel):
    id: Optional[int]
    event_code: str
    customer_id: str
    transaction_id: str
    merchant_id: str
    amount: float
    transaction_date: datetime
    event_data: dict
    status: str
    matched_rule_id: Optional[int]
    error_message: Optional[str]
    created_at: datetime
    recorded_at: datetime
    processed_at: Optional[datetime]
    channel: str

# Update the event registration API endpoint to include the 'channel' field
@app.post("/events")
async def create_event(event: Event, channel: str):
    # Save the event to the database with the provided channel
    event.channel = channel
    # Your logic to save the event
    return event

# Update the data flow to include the 'channel' field
# 1. Agents receives an event request
# 2. Builds AI prompt with customer context
# 3. Calls ai-management `/generate` for suggestion
# 4. Registers event in demo-domain (transaction amount and channel)
# 5. Returns suggested reward separately

# Update the Event model in the database schema to include the 'channel' field
ALTER TABLE events ADD COLUMN channel VARCHAR(255);