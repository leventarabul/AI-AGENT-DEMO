# test_api_server.py

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from datetime import datetime
from api_server import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_create_event(client):
    event_data = {
        "event_code": "12345",
        "customer_id": "67890",
        "transaction_id": "abcde",
        "merchant_id": "54321",
        "amount": 100.0,
        "event_data": {"channel": "web"},
        "transaction_date": datetime.now()
    }
    response = client.post("/events", json=event_data)
    assert response.status_code == 200
    assert response.json() == {"status": "pending", "channel": "web"}

def test_create_event_missing_channel(client):
    event_data = {
        "event_code": "12345",
        "customer_id": "67890",
        "transaction_id": "abcde",
        "merchant_id": "54321",
        "amount": 100.0,
        "event_data": {},
        "transaction_date": datetime.now()
    }
    response = client.post("/events", json=event_data)
    assert response.status_code == 200
    assert response.json() == {"status": "pending", "channel": "web"}

def test_create_event_no_event_data(client):
    event_data = {
        "event_code": "12345",
        "customer_id": "67890",
        "transaction_id": "abcde",
        "merchant_id": "54321",
        "amount": 100.0,
        "transaction_date": datetime.now()
    }
    response = client.post("/events", json=event_data)
    assert response.status_code == 200
    assert response.json() == {"status": "pending", "channel": "web"}

@patch('api_server.datetime')
def test_create_event_mock_datetime(mock_datetime, client):
    mock_datetime.now.return_value = datetime(2022, 1, 1, 0, 0, 0)
    event_data = {
        "event_code": "12345",
        "customer_id": "67890",
        "transaction_id": "abcde",
        "merchant_id": "54321",
        "amount": 100.0,
        "event_data": {"channel": "web"},
    }
    response = client.post("/events", json=event_data)
    assert response.status_code == 200
    assert response.json() == {"status": "pending", "channel": "web"}