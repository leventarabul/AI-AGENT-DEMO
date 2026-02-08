# agents/tests/test_demo_domain_client.py

import pytest
from unittest.mock import AsyncMock, patch
from httpx import HTTPStatusError
from agents.clients.demo_domain_client import register_event

@pytest.fixture
def event_data():
    return {
        "event_code": "test_code",
        "customer_id": "test_customer",
        "transaction_id": "test_transaction",
        "merchant_id": "test_merchant",
        "amount": 100.00,
        "transaction_date": "2022-01-01",
        "event_data": {"key": "value"},
        "channel": "test_channel"
    }

@pytest.mark.asyncio
async def test_register_event_success(event_data):
    expected_response = {"status": "success"}
    mock_client = AsyncMock()
    mock_client.post.return_value = expected_response

    with patch("agents.clients.demo_domain_client.httpx.AsyncClient", return_value=mock_client):
        response = await register_event(event_data)

    assert response == expected_response

@pytest.mark.asyncio
async def test_register_event_http_error(event_data):
    mock_client = AsyncMock()
    mock_client.post.side_effect = HTTPStatusError(response=Mock(status_code=500))

    with patch("agents.clients.demo_domain_client.httpx.AsyncClient", return_value=mock_client):
        response = await register_event(event_data)

    assert response is None

# demo-domain/tests/test_api_server.py

import pytest
from fastapi.testclient import TestClient
from demo_environment.api_server import app
from pydantic import ValidationError

@pytest.fixture
def client():
    return TestClient(app)

def test_create_event_success(client):
    event_data = {
        "event_code": "test_code",
        "customer_id": "test_customer",
        "transaction_id": "test_transaction",
        "merchant_id": "test_merchant",
        "amount": 100.00,
        "transaction_date": "2022-01-01",
        "event_data": {"key": "value"},
        "channel": "test_channel"
    }

    response = client.post("/events", json=event_data)

    assert response.status_code == 200
    assert response.json() == event_data

def test_create_event_validation_error(client):
    event_data = {
        "event_code": "test_code",
        "customer_id": "test_customer",
        "transaction_id": "test_transaction",
        "merchant_id": "test_merchant",
        "amount": 100.00,
        "transaction_date": "2022-01-01",
        "event_data": {"key": "value"},
        "channel": 123  # Invalid type
    }

    response = client.post("/events", json=event_data)

    assert response.status_code == 422