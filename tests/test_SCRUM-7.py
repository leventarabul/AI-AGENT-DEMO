import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from main import app, Event

@pytest.fixture
def client():
    return TestClient(app)

@pytest.mark.asyncio
async def test_create_event(client):
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
    response_data = {"message": "Event created successfully"}
    
    with patch("httpx.AsyncClient") as MockClient:
        mock_client = MockClient.return_value
        mock_client.post.return_value.json.return_value = response_data
        response = await client.post("/events", json=event_data)
        
        assert response.status_code == 200
        assert response.json() == response_data

@pytest.mark.asyncio
async def test_create_event_http_error(client):
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
    
    with patch("httpx.AsyncClient") as MockClient:
        mock_client = MockClient.return_value
        mock_client.post.side_effect = httpx.HTTPStatusError(response=httpx.Response(400, json={"detail": "Bad request"}))
        response = await client.post("/events", json=event_data)
        
        assert response.status_code == 400
        assert response.json() == {"detail": "Bad request"}

@pytest.mark.asyncio
async def test_trigger_job(client):
    response_data = {"message": "Job triggered successfully"}

    with patch("httpx.AsyncClient") as MockClient:
        mock_client = MockClient.return_value
        mock_client.post.return_value.json.return_value = response_data
        response = await client.post("/admin/jobs/process-events")
        
        assert response.status_code == 200
        assert response.json() == response_data

@pytest.mark.asyncio
async def test_trigger_job_http_error(client):
    with patch("httpx.AsyncClient") as MockClient:
        mock_client = MockClient.return_value
        mock_client.post.side_effect = httpx.HTTPStatusError(response=httpx.Response(500, json={"detail": "Internal server error"}))
        response = await client.post("/admin/jobs/process-events")
        
        assert response.status_code == 500
        assert response.json() == {"detail": "Internal server error"}