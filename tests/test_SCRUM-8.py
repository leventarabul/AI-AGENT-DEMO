import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture
def event_data():
    return {
        "event_code": "123",
        "customer_id": "456",
        "transaction_id": "789",
        "merchant_id": "10",
        "amount": 100.0,
        "transaction_date": datetime.now(),
        "event_data": {"key": "value"},
        "status": "success",
        "matched_rule_id": None,
        "error_message": None,
        "created_at": datetime.now(),
        "recorded_at": datetime.now(),
        "processed_at": None,
        "multiplier": 2
    }

@pytest.fixture
def ai_management_mock():
    with patch('app.ai_management_client.get_suggestion') as mock:
        mock.return_value = 10
        yield mock

@pytest.fixture
def demo_domain_mock():
    with patch('app.demo_domain_client.register_event') as mock:
        mock.return_value = 12345
        yield mock

@pytest.mark.asyncio
async def test_register_event_success(event_data, ai_management_mock, demo_domain_mock):
    response = await register_event(event_data)
    assert response == {"event_id": 12345, "status": "pending"}

@pytest.mark.asyncio
async def test_register_event_exception(event_data, ai_management_mock, demo_domain_mock):
    demo_domain_mock.side_effect = Exception("Error registering event")
    response = await register_event(event_data)
    assert response == {"error": "An error occurred while registering the event"}, 500

@pytest.mark.asyncio
async def test_register_event_earnings_calculation(event_data, ai_management_mock, \
demo_domain_mock):
    response = await register_event(event_data)
    assert ai_management_mock.call_count == 1
    assert demo_domain_mock.call_count == 1