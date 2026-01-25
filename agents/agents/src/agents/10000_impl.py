import logging
from typing import Any
from fastapi import FastAPI
from httpx import AsyncClient

app = FastAPI()
logger = logging.getLogger("app_logger")

async def provision_code_handler(event: Any):
    try:
        provision_code = event.get('provision_code')
        if not provision_code:
            raise ValueError("Provision code not found in event.")
        
        # Assuming the campaign rule implementation to be a function named 'apply_campaign_rule'
        # which takes provision code as input and returns the result
        result = await apply_campaign_rule(provision_code)
        
        return result

    except Exception as e:
        logger.error(f"Error in handling provision code: {str(e)}")
        raise

@app.post("/event/")
async def event_handler(event: Any):
    async with AsyncClient() as client:
        try:
            response = await provision_code_handler(event)
            return response
        except Exception as e:
            logger.error(f"Error in event handler: {str(e)}")
            return {"error": str(e)}

async def apply_campaign_rule(provision_code: str) -> Any:
    try:
        # Assuming the rule implementation to be a HTTP API call which takes provision code as input
        # and returns the result
        url = f"http://campaignrule.api.com/{provision_code}"
        response = await client.get(url)

        if response.status_code != 200:
            raise Exception(f"API call failed with status code {response.status_code}")

        return response.json()

    except Exception as e:
        logger.error(f"Error in applying campaign rule: {str(e)}")
        raise