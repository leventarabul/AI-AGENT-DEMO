# agents/src/clients/demo_domain_client.py

async def register_event_with_channel(event_data: dict, channel: str) -> dict:
    url = f"{DEMO_DOMAIN_URL}/events"
    payload = {**event_data, "channel": channel}
    
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, json=payload, auth=(API_USERNAME, API_PASSWORD))
        response.raise_for_status()
        return response.json()