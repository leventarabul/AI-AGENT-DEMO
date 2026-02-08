import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app import app
from app import create_event

@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client

def test_create_event_success(client):
    event_data = {
        "event_code": "test_event",
        "customer_id": "12345",
        "transaction_id": "67890",
        "merchant_id": "54321",
        "amount": 100.0,
        "transaction_date": "2022-01-01",
        "event_data": {"key": "value"},
        "channel": "web"
    }

    response = client.post("/events/", json=event_data)

    assert response.status_code == 200
    assert response.json() == {"message": "Event created successfully"}

@patch('app.httpx.AsyncClient')
def test_create_event_http_error(mock_http_client, client):
    mock_http_client.return_value.post.side_effect = Exception("Mocked HTTPError")

    event_data = {
        "event_code": "test_event",
        "customer_id": "12345",
        "transaction_id": "67890",
        "merchant_id": "54321",
        "amount": 100.0,
        "transaction_date": "2022-01-01",
        "event_data": {"key": "value"},
        "channel": "web"
    }

    response = client.post("/events/", json=event_data)

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal Server Error"}