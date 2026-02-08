import importlib.util
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

SCRUM_8_PATH = (
    Path(__file__).resolve().parents[1]
    / "agents"
    / "src"
    / "agents"
    / "SCRUM-8_impl.py"
)

spec = importlib.util.spec_from_file_location("scrum8_impl", SCRUM_8_PATH)
scrum8_impl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scrum8_impl)

Event = scrum8_impl.Event
register_event = scrum8_impl.register_event

@pytest.fixture
def event():
    return Event(
        event_code="12345",
        customer_id="67890",
        transaction_id="abcde",
        merchant_id="fghij",
        amount=100.0,
        transaction_date=datetime.now(),
        event_data={"key": "value"},
    )

@pytest.fixture
def ai_management_client():
    client = MagicMock()
    client.get_suggestion = AsyncMock(return_value=50)
    return client

@pytest.fixture
def demo_domain_client():
    client = MagicMock()
    client.register_event = AsyncMock(return_value={"id": "event_id"})
    client.create_earnings = AsyncMock(return_value=True)
    return client

@pytest.mark.asyncio
async def test_register_event_success(event, ai_management_client, demo_domain_client):
    response = await register_event(
        event,
        ai_management_client=ai_management_client,
        demo_domain_client=demo_domain_client,
    )

    assert response["event_id"] == "event_id"
    assert response["status"] == "pending"

@pytest.mark.asyncio
async def test_register_event_exception(event, ai_management_client, demo_domain_client):
    ai_management_client.get_suggestion.side_effect = Exception("AI service not available")

    response = await register_event(
        event,
        ai_management_client=ai_management_client,
        demo_domain_client=demo_domain_client,
    )

    assert response == {"error": "An error occurred while registering the event"}, 500

@pytest.mark.asyncio
async def test_register_event_earnings_amount(event, ai_management_client, demo_domain_client):
    event.multiplier = 2

    await register_event(
        event,
        ai_management_client=ai_management_client,
        demo_domain_client=demo_domain_client,
    )

    demo_domain_client.create_earnings.assert_called_with("event_id", 100)