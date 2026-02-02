import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from api_server import app
from models.events import Event

@pytest.fixture
def event_data():
    return {
        "event_code": "test_event",
        "customer_id": "12345",
        "transaction_id": "67890",
        "merchant_id": "M123",
        "amount": 100.0,
        "event_data": {"key": "value"},
        "transaction_date": "2022-01-01",
        "channel": "web"
    }

def test_create_event_success(event_data):
    client = TestClient(app)
    response = client.post("/events", json=event_data)
    assert response.status_code == 200
    assert response.json() == {"message": "Event created successfully"}

@patch('api_server.register_event')
def test_create_event_register_event_called(mock_register_event, event_data):
    mock_register_event.return_value = 1
    client = TestClient(app)
    response = client.post("/events", json=event_data)
    assert mock_register_event.called

def test_create_event_missing_channel(event_data):
    del event_data["channel"]
    client = TestClient(app)
    response = client.post("/events", json=event_data)
    assert response.status_code == 422
    assert response.json() == {"detail": [{"loc": ["body", "channel"], "msg": "field required", "type": "value_error"}]}