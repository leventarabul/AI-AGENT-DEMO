import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

@pytest.fixture
def client():
    from main import app
    return TestClient(app)

@pytest.mark.asyncio
async def test_create_event(client):
    event_data = {
        "event_code": "test_code",
        "customer_id": "test_customer_id",
        "transaction_id": "test_transaction_id",
        "merchant_id": "test_merchant_id",
        "amount": 100.0,
        "transaction_date": "2022-01-01",
        "event_data": {},
        "channel": "web"
    }

    with patch("httpx.AsyncClient") as MockAsyncClient:
        mock_post = MockAsyncClient.return_value.post
        mock_post.return_value.json = asyncmock.CoroutineMock(return_value={"success": True})
        
        response = await client.post("/events", json=event_data)
        assert response.status_code == 200
        assert response.json() == {"success": True}

@pytest.mark.asyncio
async def test_trigger_event_processing_job(client):
    with patch("httpx.AsyncClient") as MockAsyncClient:
        mock_post = MockAsyncClient.return_value.post
        mock_post.return_value.json = asyncmock.CoroutineMock(return_value={"success": True})
        
        response = await client.post("/admin/jobs/process-events")
        assert response.status_code == 200
        assert response.json() == {"success": True}

@pytest.mark.asyncio
async def test_create_event_connection_error(client):
    with patch("httpx.AsyncClient") as MockAsyncClient:
        mock_post = MockAsyncClient.return_value.post
        mock_post.side_effect = httpx.RequestError
        
        response = await client.post("/events")
        assert response.status_code == 500
        assert response.json() == {"detail": "Error connecting to demo-domain service"}