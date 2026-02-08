import pytest
from unittest.mock import MagicMock

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
        status="pending",
        created_at=datetime.now(),
        recorded_at=datetime.now(),
    )

@pytest.fixture
def ai_management_client():
    return MagicMock()

@pytest.fixture
def demo_domain_client():
    return MagicMock()

def test_register_event_success(event, ai_management_client, demo_domain_client):
    ai_management_client.get_suggestion.return_value = 50
    demo_domain_client.register_event.return_value = "event_id"
    demo_domain_client.create_earnings.return_value = True

    response = register_event(event)

    assert response["event_id"] == "event_id"
    assert response["status"] == "pending"

def test_register_event_exception(event, ai_management_client, demo_domain_client):
    ai_management_client.get_suggestion.side_effect = Exception("AI service not available")

    response = register_event(event)

    assert response == {"error": "An error occurred while registering the event"}, 500

def test_register_event_earnings_amount(event, ai_management_client, demo_domain_client):
    ai_management_client.get_suggestion.return_value = 50

    response = register_event(event)

    demo_domain_client.create_earnings.assert_called_with("event_id", 50)