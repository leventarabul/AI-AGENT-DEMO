import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime

from api_server import app, Event

@pytest.fixture
def client():
    return TestClient(app)

def test_create_event_success(client):
    event_data = {
        "event_code": "test_event",
        "customer_id": "12345",
        "transaction_id": "67890",
        "merchant_id": "54321",
        "amount": 100.0,
        "event_data": {"key": "value"},
        "transaction_date": datetime.now()
    }
    response = client.post("/events", json=event_data)
    assert response.status_code == 200
    assert response.json() == {"status": "success"}

@patch("api_server.httpx.AsyncClient")
def test_create_event_http_error(mock_client, client):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("HTTP Error")
    mock_client.return_value.post.return_value = mock_response

    event_data = {
        "event_code": "test_event",
        "customer_id": "12345",
        "transaction_id": "67890",
        "merchant_id": "54321",
        "amount": 100.0,
        "event_data": {"key": "value"},
        "transaction_date": datetime.now()
    }
    response = client.post("/events", json=event_data)
    assert response.status_code == 500
    assert response.json() == {"error": "Internal Server Error"}