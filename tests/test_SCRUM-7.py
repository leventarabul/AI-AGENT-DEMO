import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

@pytest.fixture
def event_data():
    return {"key": "value"}

@pytest.fixture
def mocked_httpx_response(event_data):
    async def mocked_response(*args, **kwargs):
        response = AsyncMock()
        response.json.return_value = {"data": event_data}
        response.raise_for_status.return_value = None
        return response

    return mocked_response

def test_create_event_success(event_data, mocked_httpx_response, monkeypatch):
    monkeypatch.setattr("httpx.AsyncClient.post", mocked_httpx_response)

    from main import app

    client = TestClient(app)

    data = {
        "event_code": "123",
        "customer_id": "456",
        "transaction_id": "789",
        "merchant_id": "987",
        "amount": 100.0,
        "transaction_date": "2022-01-01",
        "event_data": {},
        "channel": "test"
    }

    response = client.post("/events", json=data)

    assert response.status_code == 200
    assert response.json() == {"status": "Event registered successfully", "event_data": event_data}

def test_create_event_ai_management_error(mocked_httpx_response, monkeypatch):
    async def mocked_raise_for_status(*args, **kwargs):
        raise httpx.HTTPStatusError(response=AsyncMock(status_code=500))

    monkeypatch.setattr("httpx.AsyncClient.post", mocked_httpx_response)
    monkeypatch.setattr("httpx.Response", mocked_raise_for_status)

    from main import app

    client = TestClient(app)

    data = {
        "event_code": "123",
        "customer_id": "456",
        "transaction_id": "789",
        "merchant_id": "987",
        "amount": 100.0,
        "transaction_date": "2022-01-01",
        "event_data": {},
        "channel": "test"
    }

    response = client.post("/events", json=data)

    assert response.status_code == 500
    assert response.json() == {"detail": "AI Management error"}

def test_create_event_internal_server_error(mocked_httpx_response, monkeypatch):
    async def mocked_raise_for_status(*args, **kwargs):
        raise Exception()

    monkeypatch.setattr("httpx.AsyncClient.post", mocked_httpx_response)
    monkeypatch.setattr("httpx.Response", mocked_raise_for_status)

    from main import app

    client = TestClient(app)

    data = {
        "event_code": "123",
        "customer_id": "456",
        "transaction_id": "789",
        "merchant_id": "987",
        "amount": 100.0,
        "transaction_date": "2022-01-01",
        "event_data": {},
        "channel": "test"
    }

    response = client.post("/events", json=data)

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal Server Error"}