# Add a new field 'channel' to the events table for logging purposes
from pydantic import BaseModel
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from tortoise.models import Model
from tortoise import fields
from tortoise.contrib.fastapi import register_tortoise

# Define the new field in the database model
class Event(Model):
    id = fields.IntField(pk=True)
    event_code = fields.CharField(max_length=255)
    customer_id = fields.CharField(max_length=255)
    transaction_id = fields.CharField(max_length=255)
    merchant_id = fields.CharField(max_length=255)
    amount = fields.DecimalField(max_digits=10, decimal_places=2)
    transaction_date = fields.DatetimeField()
    event_data = fields.JSONField()
    status = fields.CharField(max_length=255)
    matched_rule_id = fields.IntField(null=True)
    error_message = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    recorded_at = fields.DatetimeField(auto_now=True)
    processed_at = fields.DatetimeField(null=True)
    channel = fields.CharField(max_length=255, null=True)  # New field for logging

# Update the API endpoint to accept the 'channel' field
class EventRequest(BaseModel):
    event_code: str
    customer_id: str
    transaction_id: str
    merchant_id: str
    amount: float
    event_data: dict
    transaction_date: str
    channel: str  # New field

# Update the event registration endpoint with the new field
@app.post("/events")
async def create_event(event_request: EventRequest):
    event = Event(
        event_code=event_request.event_code,
        customer_id=event_request.customer_id,
        transaction_id=event_request.transaction_id,
        merchant_id=event_request.merchant_id,
        amount=event_request.amount,
        transaction_date=event_request.transaction_date,
        event_data=event_request.event_data,
        status="pending",
        channel=event_request.channel  # Assign the new field value
    )
    await event.save()
    return event

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Tortoise models
register_tortoise(
    app,
    db_url="sqlite://./db.sqlite3",
    modules={"models": ["__main__"]},
    generate_schemas=True,
)