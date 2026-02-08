import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from agents.SCRUM-7_impl import router, NewEvent

@pytest.fixture
def test_client():
    return TestClient(router)

@pytest.mark.asyncio
async def test_create_event_success(test_client):
    event_data = {
        "event_code": "TEST123",
        "customer_id": "CUST123",
        "transaction_id": "TRANS123",
        "merchant_id": "MERCH123",
        "amount": 100.0,
        "channel": "online",
        "transaction_date": "2022-01-01",
        "event_data": {}
    }
    response_data = {"status": "success"}
    
    with patch('agents.SCRUM-7_impl.AsyncClient') as mock_client:
        mock_client.return_value.post = AsyncMock()
        mock_client.return_value.post.return_value.json = AsyncMock(return_value=response_data)
        
        response = await test_client.post("/events", json=event_data)
        assert response.status_code == 200
        assert response.json() == response_data

@pytest.mark.asyncio
async def test_create_event_error(test_client):
    event_data = {
        "event_code": "TEST123",
        "customer_id": "CUST123",
        "transaction_id": "TRANS123",
        "merchant_id": "MERCH123",
        "amount": 100.0,
        "channel": "online",
        "transaction_date": "2022-01-01",
        "event_data": {}
    }
    
    with patch('agents.SCRUM-7_impl.AsyncClient') as mock_client:
        mock_client.return_value.post = AsyncMock(side_effect=Exception("Mocked error"))
        
        response = await test_client.post("/events", json=event_data)
        assert response.status_code == 500