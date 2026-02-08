from agents.SCRUM-7_impl import create_event_endpoint, EventIn
from fastapi import HTTPException
from unittest.mock import patch

def test_create_event_endpoint_success():
    event = EventIn(event_code="test_event", customer_id="123", transaction_id="456", merchant_id="789", amount=100.0, event_data={"key": "value"}, channel="web")
    result = create_event_endpoint(event)
    assert result.event_code == event.event_code

def test_create_event_endpoint_no_channel():
    event = EventIn(event_code="test_event", customer_id="123", transaction_id="456", merchant_id="789", amount=100.0, event_data={"key": "value"})
    result = create_event_endpoint(event)
    assert result.event_code == event.event_code

@patch("agents.SCRUM-7_impl.create_event")
def test_create_event_endpoint_failure(mock_create_event):
    mock_create_event.return_value = False
    event = EventIn(event_code="test_event", customer_id="123", transaction_id="456", merchant_id="789", amount=100.0, event_data={"key": "value"}, channel="web")
    try:
        create_event_endpoint(event)
    except HTTPException as e:
        assert e.status_code == 400