import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app import app, Event, create_event, process_event, match_campaign_rules

@pytest.fixture
def test_client():
    client = TestClient(app)
    return client

def test_create_event_with_channel(test_client):
    event_data = {
        "event_code": "123",
        "customer_id": "456",
        "transaction_id": "789",
        "merchant_id": "101112",
        "amount": 100.0,
        "transaction_date": "2022-01-01T00:00:00",
        "event_data": {"key": "value"},
        "status": "success",
        "matched_rule_id": None,
        "error_message": None,
        "created_at": "2022-01-01T00:00:00",
        "recorded_at": "2022-01-01T00:00:00",
        "processed_at": None,
        "channel": "web"
    }
    response = test_client.post("/events", json=event_data)
    assert response.status_code == 200
    assert response.json()["channel"] == "web"

def test_process_event_with_channel():
    event = Event(event_code="123", customer_id="456", transaction_id="789", merchant_id="101112", amount=100.0, transaction_date="2022-01-01T00:00:00", event_data={"key": "value"}, status="success", matched_rule_id=None, error_message=None, created_at="2022-01-01T00:00:00", recorded_at="2022-01-01T00:00:00", processed_at=None, channel="web")
    # Mock the event processing logic
    with patch('app.process_event') as mock_process_event:
        mock_process_event.return_value = None
        process_event(event)
        mock_process_event.assert_called_once_with(event)

def test_match_campaign_rules_with_channel():
    event = Event(event_code="123", customer_id="456", transaction_id="789", merchant_id="101112", amount=100.0, transaction_date="2022-01-01T00:00:00", event_data={"key": "value"}, status="success", matched_rule_id=None, error_message=None, created_at="2022-01-01T00:00:00", recorded_at="2022-01-01T00:00:00", processed_at=None, channel="web")
    # Mock the campaign rule matching logic
    with patch('app.match_campaign_rules') as mock_match_campaign_rules:
        mock_match_campaign_rules.return_value = None
        match_campaign_rules(event)
        mock_match_campaign_rules.assert_called_once_with(event)