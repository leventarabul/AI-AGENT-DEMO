# agents/src/clients/demo_domain_client.py

import httpx

async def update_event_channel(event_id: int, channel: str):
    async with httpx.AsyncClient() as client:
        url = f"http://demo-domain-api:8000/events/{event_id}"
        payload = {"channel": channel}
        headers = {"Content-Type": "application/json"}
        response = await client.patch(url, json=payload, headers=headers)
        response.raise_for_status()