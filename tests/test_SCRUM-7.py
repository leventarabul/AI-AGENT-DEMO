import pytest
from unittest.mock import MagicMock, patch
from app import create_event, save_event

@pytest.fixture
def event_data():
    return {
        "name": "Test Event",
        "date": "2022-01-01",
        "description": "This is a test event"
    }

@pytest.fixture
def event_create():
    return {
        "name": "Test Event",
        "date": "2022-01-01",
        "description": "This is a test event",
        "channel": "Test Channel"
    }

@pytest.mark.asyncio
async def test_create_event(event_data, event_create):
    with patch('app.save_event') as mock_save_event:
        mock_save_event.return_value = MagicMock()
        
        result = await create_event(event_create)
        
        assert mock_save_event.called
        assert result is not None

@pytest.mark.asyncio
async def test_save_event(event_data):
    with patch('app.Event.save') as mock_save:
        mock_event = MagicMock()
        mock_save.return_value = mock_event
        
        result = await save_event(event_data, "Test Channel")
        
        assert mock_save.called
        assert result is not None