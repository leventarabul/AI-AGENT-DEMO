#!/usr/bin/env python
"""
Example script to send a mock testing webhook to test the TestingAgent.
"""
import httpx
import json
import asyncio


async def send_mock_testing_webhook():
    """Send a mock testing webhook for testing."""
    webhook_payload = {
        "webhookEvent": "testing.status_changed",
        "issue": {
            "key": "TASK-101",
            "fields": {
                "summary": "Implement user authentication with OAuth2",
                "status": {"name": "Testing"},
                "issuetype": {"name": "Story"},
            }
        },
        "test_files": [
            "tests/test_user_service.py",
            "tests/test_auth.py",
        ]
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "http://localhost:8002/webhooks/testing",
            json=webhook_payload,
        )
        print(f"Webhook response: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2))


if __name__ == "__main__":
    asyncio.run(send_mock_testing_webhook())
