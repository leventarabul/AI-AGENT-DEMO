import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from unittest import mock
from app import app, get_provision_code, handle_event  # Replace 'app' with your module name


@pytest.fixture
def event_data():
    return {"provision_code": "12345678"}


@pytest.mark.asyncio
async def test_get_provision_code(event_data):
    provision_code = await get_provision_code(event_data)
    assert provision_code == event_data["provision_code"]

    with pytest.raises(ValueError):
        await get_provision_code({})


@pytest.mark.asyncio
async def test_handle_event(event_data):
    with mock.patch.object(AsyncClient, 'get', return_value=mock.Mock(status_code=200, json=mock.Mock(return_value={"rule": "test_rule"}))):
        response = await handle_event(event_data)
        assert response["provision_code"] == event_data["provision_code"]
        assert response["campaign_rule"]["rule"] == "test_rule"

    with pytest.raises(HTTPException):
        with mock.patch.object(AsyncClient, 'get', return_value=mock.Mock(status_code=400, text="Bad Request")):
            await handle_event(event_data)

    with pytest.raises(HTTPException):
        await handle_event({})