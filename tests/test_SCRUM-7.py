import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app
from models.event import Event

@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client

def test_create_event(client):
    event_data = {
        "event_code": "12345",
        "customer_id": "67890",
        "transaction_id": "abcde",
        "merchant_id": "54321",
        "amount": 100.0,
        "event_data": {"key": "value"},
        "transaction_date": "2022-01-01",
        "channel": "web"
    }
    response = client.post("/events", json=event_data)
    assert response.status_code == 200
    assert response.json() == {"message": "Event created successfully with channel info"}

def test_create_event_missing_channel(client):
    event_data = {
        "event_code": "12345",
        "customer_id": "67890",
        "transaction_id": "abcde",
        "merchant_id": "54321",
        "amount": 100.0,
        "event_data": {"key": "value"},
        "transaction_date": "2022-01-01"
    }
    response = client.post("/events", json=event_data)
    assert response.status_code == 200
    assert response.json() == {"message": "Event created successfully with channel info"}

def test_create_event_invalid_data(client):
    event_data = {
        "event_code": "12345",
        "customer_id": "67890",
        "transaction_id": "abcde",
        "merchant_id": "54321",
        "amount": "invalid_amount",
        "event_data": {"key": "value"},
        "transaction_date": "2022-01-01",
        "channel": "web"
    }
    response = client.post("/events", json=event_data)
    assert response.status_code == 422

@patch('app.routes.events.create_event')
def test_create_event_mocked(mock_create_event, client):
    event_data = {
        "event_code": "12345",
        "customer_id": "67890",
        "transaction_id": "abcde",
        "merchant_id": "54321",
        "amount": 100.0,
        "event_data": {"key": "value"},
        "transaction_date": "2022-01-01",
        "channel": "web"
    }
    response = client.post("/events", json=event_data)
    mock_create_event.assert_called_once_with(Event(**event_data))
    assert response.status_code == 200