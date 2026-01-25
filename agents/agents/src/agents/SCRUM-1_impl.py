import logging
from typing import Dict
from fastapi import FastAPI, HTTPException
import httpx

app = FastAPI()
logger = logging.getLogger(__name__)

async def get_provision_code(event: Dict):
    try:
        provision_code = event.get('provision_code')
        if not provision_code:
            logger.error(f"Provision code not found in event: {event}")
            raise ValueError("Provision code not found")

        return provision_code
    except Exception as e:
        logger.error(f"Error getting provision code: {str(e)}")
        raise

@app.post("/event")
async def handle_event(event: Dict):
    try:
        provision_code = await get_provision_code(event)
        
        async with httpx.AsyncClient() as client:
            campaign_rule_response = await client.get(f"http://localhost:8000/campaign_rule/{provision_code}")

            if campaign_rule_response.status_code != 200:
                logger.error(f"Error getting campaign rule: {campaign_rule_response.text}")
                raise HTTPException(status_code=500, detail="Error getting campaign rule")

            campaign_rule = campaign_rule_response.json()

        return {"provision_code": provision_code, "campaign_rule": campaign_rule}

    except Exception as e:
        logger.error(f"Error handling event: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))