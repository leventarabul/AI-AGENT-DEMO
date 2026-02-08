# agents/src/clients/demo_domain_client.py

import httpx

async def register_event(event_data: dict):
    async with httpx.AsyncClient() as client:
        url = "http://demo-domain-api:8000/events"
        headers = {"Content-Type": "application/json"}
        auth = ("admin", "admin123")
        response = await client.post(url, headers=headers, auth=auth, json=event_data)
        response.raise_for_status()
        return response.json()

# agents/src/knowledge/context_loader.py

async def load_context(channel: str):
    # Load context based on channel
    return {"channel": channel}