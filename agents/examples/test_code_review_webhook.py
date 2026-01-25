#!/usr/bin/env python
"""
Example script to send a mock code review webhook to test the CodeReviewAgent.
"""
import httpx
import json
import asyncio


async def send_mock_code_review_webhook():
    """Send a mock code review webhook for testing."""
    
    # Mock code to be reviewed
    mock_code = """
import asyncio
import httpx
from typing import Optional, Dict, Any

class UserService:
    \"\"\"Service for user management.\"\"\"
    
    def __init__(self, db_url: str):
        self.db_url = db_url
    
    async def get_user(self, user_id: int) -> Dict[str, Any]:
        \"\"\"Fetch user by ID.\"\"\"
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{self.db_url}/users/{user_id}")
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPError as e:
                print(f"Error: {e}")
                return None
    
    async def create_user(self, name: str, email: str) -> Dict[str, Any]:
        \"\"\"Create a new user.\"\"\"
        payload = {"name": name, "email": email}
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.db_url}/users", json=payload)
            resp.raise_for_status()
            return resp.json()
"""

    mock_test_code = """
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from user_service import UserService

@pytest.fixture
def user_service():
    \"\"\"Fixture for UserService.\"\"\"
    return UserService("http://localhost:5432")

@pytest.mark.asyncio
async def test_get_user_success(user_service):
    \"\"\"Test successful user retrieval.\"\"\"
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = AsyncMock()
        mock_response.json.return_value = {"id": 1, "name": "John"}
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
        
        result = await user_service.get_user(1)
        assert result["name"] == "John"

@pytest.mark.asyncio
async def test_create_user_success(user_service):
    \"\"\"Test successful user creation.\"\"\"
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = AsyncMock()
        mock_response.json.return_value = {"id": 2, "name": "Jane", "email": "jane@example.com"}
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
        
        result = await user_service.create_user("Jane", "jane@example.com")
        assert result["id"] == 2
"""
    
    webhook_payload = {
        "webhookEvent": "pull_request.opened",
        "issue": {
            "key": "TASK-101",
            "fields": {
                "summary": "Implement user authentication with OAuth2",
                "status": {"name": "In Review"},
                "issuetype": {"name": "Story"},
            }
        },
        "pull_request": {
            "title": "[TASK-101] Implement user authentication",
            "url": "https://github.com/example/repo/pull/1",
        },
        "code_files": [
            ("src/user_service.py", mock_code),
            ("tests/test_user_service.py", mock_test_code),
        ]
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "http://localhost:8002/webhooks/code-review",
            json=webhook_payload,
        )
        print(f"Webhook response: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2))


if __name__ == "__main__":
    asyncio.run(send_mock_code_review_webhook())
