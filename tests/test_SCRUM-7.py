import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock

@pytest.fixture
def mock_client():
    async with AsyncClient() as client:
        yield client

@pytest.mark.asyncio
async def test_register_event_success(mock_client):
    event_data = {"name": "Test Event", "date": "2022-01-01"}
    expected_response = {"id": 1, "name": "Test Event", "date": "2022-01-01"}
    
    mock_client.post = AsyncMock(return_value=AsyncMock(json=AsyncMock(return_value=expected_response)))
    
    response = await register_event(event_data)
    
    assert response == expected_response

@pytest.mark.asyncio
async def test_register_event_error(mock_client):
    event_data = {"name": "Test Event", "date": "2022-01-01"}
    
    mock_client.post = AsyncMock(side_effect=httpx.HTTPError)
    
    with pytest.raises(httpx.HTTPError):
        await register_event(event_data)

@pytest.mark.asyncio
async def test_register_event_timeout(mock_client):
    event_data = {"name": "Test Event", "date": "2022-01-01"}
    
    mock_client.post = AsyncMock(side_effect=httpx.ReadTimeout)
    
    with pytest.raises(httpx.ReadTimeout):
        await register_event(event_data)