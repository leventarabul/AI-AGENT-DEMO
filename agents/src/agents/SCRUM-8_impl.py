import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional, Tuple, Union

from fastapi import FastAPI
from pydantic import BaseModel, Field

from src.clients.ai_management_client import AIManagementClient
from src.clients.demo_domain_client import DemoDomainClient

logger = logging.getLogger(__name__)
app = FastAPI()


class Event(BaseModel):
    event_code: str
    customer_id: str
    transaction_id: str
    merchant_id: str
    amount: float
    transaction_date: datetime
    event_data: Dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"
    matched_rule_id: Optional[int] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    recorded_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    multiplier: float = Field(default=1.0, ge=0)


def validate_event(event: Event) -> None:
    if event.multiplier <= 0:
        raise ValueError("Multiplier must be greater than 0")
    if event.amount < 0:
        raise ValueError("Amount must be non-negative")


def construct_prompt(event: Event) -> str:
    return (
        f"Event: event_code={event.event_code}, customer_id={event.customer_id}, "
        f"merchant_id={event.merchant_id}, amount={event.amount}. "
        "Ödül miktarını sadece sayısal değer olarak döndür."
    )


def _get_clients(
    ai_management_client: Optional[Any],
    demo_domain_client: Optional[Any],
) -> Tuple[Optional[Any], Optional[Any]]:
    return ai_management_client, demo_domain_client


async def _get_suggestion(ai_client: Any, prompt: str) -> float:
    if hasattr(ai_client, "get_suggestion"):
        result = await ai_client.get_suggestion(prompt)
        return float(result)

    response = await ai_client.generate(prompt)
    if isinstance(response, dict):
        text = response.get("text")
        if text is None:
            raise ValueError("AI response missing 'text'")
        return float(text)
    return float(response)


async def _register_with_clients(event: Event, ai_client: Any, demo_client: Any) -> Dict[str, Any]:
    prompt = construct_prompt(event)
    suggestion = await _get_suggestion(ai_client, prompt)
    earnings_amount = suggestion * event.multiplier

    transaction_date = event.transaction_date.isoformat()
    event_response = await demo_client.register_event(
        event_code=event.event_code,
        customer_id=event.customer_id,
        transaction_id=event.transaction_id,
        merchant_id=event.merchant_id,
        amount=event.amount,
        transaction_date=transaction_date,
        event_data=event.event_data,
    )

    if isinstance(event_response, dict):
        event_id = event_response.get("id")
    else:
        event_id = event_response

    if hasattr(demo_client, "create_earnings"):
        await demo_client.create_earnings(event_id, earnings_amount)

    return {"event_id": event_id, "status": "pending"}


# Update the event registration endpoint to include the 'multiplier' field
@app.post("/events")
async def register_event(
    event: Event,
    ai_management_client: Optional[Any] = None,
    demo_domain_client: Optional[Any] = None,
):
    try:
        validate_event(event)

        ai_client, demo_client = _get_clients(
            ai_management_client,
            demo_domain_client,
        )

        if ai_client is None or demo_client is None:
            ai_url = os.getenv("AI_MANAGEMENT_URL", "http://ai-management-service:8001")
            demo_url = os.getenv("DEMO_DOMAIN_URL", "http://demo-domain-api:8000")
            demo_user = os.getenv("DEMO_DOMAIN_USER", "admin")
            demo_pass = os.getenv("DEMO_DOMAIN_PASSWORD", "admin123")

            async with AIManagementClient(ai_url) as ai_client_ctx:
                async with DemoDomainClient(demo_url, demo_user, demo_pass) as demo_client_ctx:
                    return await _register_with_clients(event, ai_client_ctx, demo_client_ctx)

        return await _register_with_clients(event, ai_client, demo_client)
    except Exception as e:
        logger.error("Error registering event: %s", e)
        return {"error": "An error occurred while registering the event"}, 500