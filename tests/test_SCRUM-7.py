import pytest
from app import create_event

@pytest.mark.asyncio
async def test_create_event_success():
    # Test creating an event with valid channel information
    event_data = {"channel": "test_channel"}
    response = await create_event(event_data)
    assert response["status"] == "pending"

@pytest.mark.asyncio
async def test_create_event_missing_channel():
    # Test creating an event with missing channel information
    event_data = {}
    with pytest.raises(Exception):
        await create_event(event_data)

@pytest.mark.asyncio
async def test_save_event_to_db_success():
    # Test saving event data to the database with valid inputs
    event_data = {"channel": "test_channel"}
    event_id = await save_event_to_db(event_data, channel)
    assert event_id is not None

@pytest.mark.asyncio
async def test_save_event_to_db_missing_channel():
    # Test saving event data to the database with missing channel information
    event_data = {}
    with pytest.raises(Exception):
        await save_event_to_db(event_data, channel)