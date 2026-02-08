# agents/src/clients/demo_domain_client.py

import httpx

DEMO_DOMAIN_URL = "http://demo-domain-api:8000"

async def register_event(event_data: dict) -> dict:
    url = f"{DEMO_DOMAIN_URL}/events"
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=event_data)
        response.raise_for_status()
        return response.json()