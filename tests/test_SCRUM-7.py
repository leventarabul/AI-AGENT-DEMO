import pytest
from httpx import Response
from unittest.mock import AsyncMock

@pytest.fixture
def mock_httpx_response():
    return AsyncMock(Response)

@pytest.mark.asyncio
async def test_register_event_successful(mock_httpx_response):
    mock_httpx_response.return_value.json.return_value = {"event_id": 1}
    
    with patch("httpx.AsyncClient.post", return_value=mock_httpx_response) as mock_post:
        result = await register_event({"name": "event1"})
        
    assert result == {"event_id": 1}

@pytest.mark.asyncio
async def test_register_event_unauthorized(mock_httpx_response):
    mock_httpx_response.return_value.status_code = 401
    
    with patch("httpx.AsyncClient.post", return_value=mock_httpx_response) as mock_post:
        with pytest.raises(httpx.HTTPStatusError):
            await register_event({"name": "event1"})

@pytest.mark.asyncio
async def test_register_event_server_error(mock_httpx_response):
    mock_httpx_response.return_value.status_code = 500
    
    with patch("httpx.AsyncClient.post", return_value=mock_httpx_response) as mock_post:
        with pytest.raises(httpx.HTTPStatusError):
            await register_event({"name": "event1"})

@pytest.mark.asyncio
async def test_register_event_timeout(mock_httpx_response):
    mock_httpx_response.side_effect = httpx.ReadTimeout
    
    with patch("httpx.AsyncClient.post", return_value=mock_httpx_response) as mock_post:
        with pytest.raises(httpx.ReadTimeout):
            await register_event({"name": "event1"})