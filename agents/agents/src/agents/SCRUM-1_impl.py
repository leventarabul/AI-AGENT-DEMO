import logging
from fastapi import FastAPI, HTTPException
from typing import Dict
import httpx

app = FastAPI()
logger = logging.getLogger(__name__)

async def get_provision_code(event_id: str) -> Dict:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"https://api.example.com/events/{event_id}/provision_code")
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(f"Error response {exc.response.status_code} while getting provision code.")
            raise HTTPException(status_code=exc.response.status_code, detail="Unable to get provision code.")
        except Exception as exc:
            logger.error(f"An unexpected error occurred while getting provision code: {exc}")
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    return response.json()

@app.get("/campaign_rule/{event_id}")
async def campaign_rule(event_id: str):
    provision_code = await get_provision_code(event_id)

    # Do some process with provision_code
    # ...

    return {"message": "Campaign rule applied successfully."}