import pytest
from starlette.testclient import TestClient
from fastapi import HTTPException
from unittest.mock import patch, AsyncMock

import main  # assume our original code is in main.py

# instantiate our FastAPI app
client = TestClient(main.app)

@patch("main.get_provision_code", new_callable=AsyncMock)
def test_campaign_rule_success(mock_get_provision_code):
    mock_get_provision_code.return_value = {"provision_code": "1234"}

    response = client.get("/campaign_rule/test_event_id")
    assert response.status_code == 200
    assert response.json() == {"message": "Campaign rule applied successfully."}
    mock_get_provision_code.assert_called_once_with("test_event_id")


@patch("main.get_provision_code", new_callable=AsyncMock)
def test_campaign_rule_failure(mock_get_provision_code):
    mock_get_provision_code.side_effect = HTTPException(
        status_code=500, detail="An unexpected error occurred.")

    response = client.get("/campaign_rule/test_event_id")
    assert response.status_code == 500
    assert response.json() == {"detail": "An unexpected error occurred."}
    mock_get_provision_code.assert_called_once_with("test_event_id")


@patch("httpx.AsyncClient.get", new_callable=AsyncMock)
def test_get_provision_code_success(mock_get):
    mock_response = AsyncMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"provision_code": "1234"}
    mock_get.return_value = mock_response

    provision_code = main.get_provision_code("test_event_id")
    assert provision_code == {"provision_code": "1234"}


@patch("httpx.AsyncClient.get", new_callable=AsyncMock)
def test_get_provision_code_failure(mock_get):
    mock_response = AsyncMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError("Error", request=mock_get, response=mock_response)
    mock_get.return_value = mock_response

    with pytest.raises(HTTPException):
        main.get_provision_code("test_event_id")