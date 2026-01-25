import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from unittest.mock import patch
from your_module import app  # Replace with the name of the module where your FastAPI app is

client = TestClient(app)


def test_run_task3_success():
    with patch('your_module.task3') as mock:
        mock.return_value = {"key": "value"}

        response = client.get("/task3")

        assert response.status_code == 200
        assert response.json() == {"key": "value"}
        mock.assert_called_once()


def test_run_task3_error():
    with patch('your_module.task3') as mock:
        mock.side_effect = HTTPException(status_code=500, detail="An error occurred")

        response = client.get("/task3")

        assert response.status_code == 500
        assert response.json() == {"detail": "An error occurred"}
        mock.assert_called_once()


@pytest.mark.asyncio
async def test_task3_success():
    with patch('httpx.AsyncClient.get') as mock:
        mock.return_value = type('MockResponse', (object,), {'status_code': 200, 'json': lambda: {"key": "value"}})

        result = await app.task3()

        assert result == {"key": "value"}


@pytest.mark.asyncio
async def test_task3_failed_fetch():
    with patch('httpx.AsyncClient.get') as mock:
        mock.return_value = type('MockResponse', (object,), {'status_code': 500, 'json': lambda: {}})

        with pytest.raises(HTTPException) as excinfo:
            await app.task3()

        assert excinfo.value.status_code == 500
        assert str(excinfo.value.detail) == "Failed to fetch data"


@pytest.mark.asyncio
async def test_task3_exception():
    with patch('httpx.AsyncClient.get') as mock:
        mock.side_effect = Exception("An error occurred")

        with pytest.raises(HTTPException) as excinfo:
            await app.task3()

        assert excinfo.value.status_code == 500
        assert str(excinfo.value.detail) == "An error occurred"