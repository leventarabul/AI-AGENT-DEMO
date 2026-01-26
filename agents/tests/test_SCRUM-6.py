import pytest
from fastapi import HTTPException
from httpx import AsyncClient, HTTPStatusError
from unittest.mock import patch, Mock
from app import add_event, Event

@pytest.fixture
def event_data():
    return {"id": 1, "name": "test", "channel": "test_channel"}

@pytest.fixture
def event():
    return Event(id=1, name="test", "channel": "test_channel")

@pytest.mark.asyncio
@patch('httpx.AsyncClient.post')
async def test_add_event_success(mock_post, event, event_data):
    mock_post.return_value.__aenter__.return_value.json.return_value = event_data

    response = await add_event(event)

    mock_post.assert_called_once_with("http://localhost:8000/events/", json=event.dict())
    assert response == event_data

@pytest.mark.asyncio
@patch('httpx.AsyncClient.post')
async def test_add_event_http_error(mock_post, event, event_data):
    mock_post.return_value.__aenter__.side_effect = HTTPStatusError('error', request=Mock())
  
    with pytest.raises(HTTPException) as e:
        await add_event(event)

    mock_post.assert_called_once_with("http://localhost:8000/events/", json=event.dict())
    assert e.value.status_code == 400
    assert "An error occurred while adding the event" in str(e.value.detail)

@pytest.mark.asyncio
@patch('httpx.AsyncClient.post')
async def test_add_event_unexpected_error(mock_post, event, event_data):
    mock_post.return_value.__aenter__.side_effect = Exception('unexpected error')
  
    with pytest.raises(HTTPException) as e:
        await add_event(event)

    mock_post.assert_called_once_with("http://localhost:8000/events/", json=event.dict())
    assert e.value.status_code == 500
    assert "Unexpected error" in str(e.value.detail)