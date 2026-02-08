# Add a new field 'channel' to the Event model
class Event(BaseModel):
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

# Update the API endpoint to include 'channel' in the request payload
@app.post("/events")
async def create_event(event: Event):
    # Save the event with the 'channel' field
    event_dict = event.dict()
    # Include the 'channel' field in the insert query
    # Execute the insert query and return the response