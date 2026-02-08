# Add a new field 'multiplier' to the Event model
class Event(BaseModel):
    event_code: str
    customer_id: str
    transaction_id: str
    merchant_id: str
    amount: float
    transaction_date: datetime
    event_data: Dict[str, Any]
    status: str
    matched_rule_id: Optional[int]
    error_message: Optional[str]
    created_at: datetime
    recorded_at: datetime
    processed_at: Optional[datetime]
    multiplier: int = 1


# Update the event registration endpoint to include the 'multiplier' field
@app.post("/events")
async def register_event(event: Event):
    try:
        # Validate event data
        validate_event(event)

        # Call ai-management to get suggestion based on event data
        prompt = construct_prompt(event)
        suggestion = await ai_management_client.get_suggestion(prompt)

        # Calculate earnings based on the suggestion and multiplier
        earnings_amount = suggestion * event.multiplier

        # Register the event in the demo-domain
        event_id = await demo_domain_client.register_event(event)
        
        # Create earnings record
        await demo_domain_client.create_earnings(event_id, earnings_amount)

        return {"event_id": event_id, "status": "pending"}
    except Exception as e:
        logging.error(f"Error registering event: {str(e)}")
        return {"error": "An error occurred while registering the event"}, 500