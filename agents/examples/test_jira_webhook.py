#!/usr/bin/env python
"""
Example script to send a mock Jira webhook to test the JiraAgent.
"""
import httpx
import json
import asyncio


async def send_mock_jira_webhook():
    """Send a mock Jira webhook for testing."""
    webhook_payload = {
        "webhookEvent": "jira:issue_updated",
        "issue": {
            "key": "TASK-101",
            "fields": {
                "summary": "Implement user authentication with OAuth2",
                "description": "Add OAuth2 support to the API. Should handle Google and GitHub logins.",
                "issuetype": {"name": "Story"},
                "status": {"name": "Development Waiting"},
                "labels": ["backend", "auth", "security"],
            }
        }
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "http://localhost:8002/webhooks/jira",
            json=webhook_payload,
        )
        print(f"Webhook response: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2))


if __name__ == "__main__":
    asyncio.run(send_mock_jira_webhook())
