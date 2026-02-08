# agents/src/clients/demo_domain_client.py

import httpx

DEMO_DOMAIN_URL = "http://demo-domain-api:8000"

async def create_event(channel: str, event_data: dict) -> dict:
    url = f"{DEMO_DOMAIN_URL}/events"
    payload = {
        "channel": channel,
        "event_data": event_data
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, json=payload, auth=("admin", "admin123"))
        response.raise_for_status()
        return response.json()