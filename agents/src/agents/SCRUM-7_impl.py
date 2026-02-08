# demo-domain/src/demo-environment/api_server.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
import logging

app = FastAPI()

# Sample database operation to insert event with channel
def save_event(event_code: str, customer_id: str, transaction_id: str, merchant_id: str, amount: float, transaction_date: str, event_data: dict, channel: str):
    # Simulate database insert
    logging.info(f"Saving event with channel: {channel}")
    return {
        "id": 1,
        "event_code": event_code,
        "customer_id": customer_id,
        "transaction_id": transaction_id,
        "merchant_id": merchant_id,
        "amount": amount,
        "transaction_date": transaction_date,
        "event_data": event_data,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "recorded_at": datetime.now().isoformat()
    }

class Event(BaseModel):
    event_code: str
    customer_id: str
    transaction_id: str
    merchant_id: str
    amount: float
    transaction_date: str
    event_data: dict
    channel: str

@app.post("/events")
async def create_event(event: Event):
    try:
        # Save event with channel
        saved_event = save_event(event.event_code, event.customer_id, event.transaction_id, event.merchant_id, event.amount, event.transaction_date, event.event_data, event.channel)
        return saved_event
    except Exception as e:
        logging.error(f"Error creating event: {e}")
        raise HTTPException(status_code=500, detail="Error creating event")