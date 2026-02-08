import pytest
from httpx import HTTPStatusError
from fastapi.testclient import TestClient
from demo_environment.api_server import app

@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client

@pytest.mark.asyncio
async def test_register_event_success(client, mocker):
    mocker.patch("httpx.AsyncClient.post", return_value={"message": "Event created successfully"})
    event_data = {
        "event_code": "TEST",
        "customer_id": "12345",
        "transaction_id": "67890",
        "merchant_id": "54321",
        "amount": 100.00,
        "transaction_date": "2022-01-01",
        "event_data": {},
        "channel": "web"
    }
    response = await client.post("/events", json=event_data)
    assert response.status_code == 200
    assert response.json() == {"message": "Event created successfully"}

@pytest.mark.asyncio
async def test_register_event_failure(client, mocker):
    mocker.patch("httpx.AsyncClient.post", side_effect=HTTPStatusError(response={"status_code": 500}))
    event_data = {
        "event_code": "TEST",
        "customer_id": "12345",
        "transaction_id": "67890",
        "merchant_id": "54321",
        "amount": 100.00,
        "transaction_date": "2022-01-01",
        "event_data": {},
        "channel": "web"
    }
    response = await client.post("/events", json=event_data)
    assert response.status_code == 500