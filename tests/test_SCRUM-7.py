# test_demo_domain_client.py

import pytest
from httpx import AsyncClient
from unittest.mock import patch
from clients.demo_domain_client import create_event

@pytest.fixture
def event_data():
    return {
        "event_code": "123",
        "customer_id": "456",
        "transaction_id": "789",
        "merchant_id": "101112",
        "amount": 50.0,
        "transaction_date": "2022-01-01",
        "event_data": {}
    }

@pytest.mark.asyncio
async def test_create_event_success(event_data):
    with patch("clients.demo_domain_client.httpx.AsyncClient") as mock_client:
        mock_client.return_value.post.return_value.json.return_value = {"status": "success"}
        response = await create_event(event_data)
        assert response == {"status": "success"}

@pytest.mark.asyncio
async def test_create_event_add_channel(event_data):
    with patch("clients.demo_domain_client.httpx.AsyncClient") as mock_client:
        mock_client.return_value.post.return_value.json.return_value = {"status": "success"}
        response = await create_event(event_data)
        assert response["event_data"]["channel"] == "web"

@pytest.mark.asyncio
async def test_create_event_error(event_data):
    with patch("clients.demo_domain_client.httpx.AsyncClient") as mock_client:
        mock_client.return_value.post.side_effect = Exception("Connection error")
        with pytest.raises(Exception):
            await create_event(event_data)