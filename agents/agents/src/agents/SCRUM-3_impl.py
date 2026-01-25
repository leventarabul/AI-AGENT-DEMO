# Assuming FastAPI based on the information given.
from fastapi import FastAPI, HTTPException
from typing import Any
import httpx
import logging

app = FastAPI()
logger = logging.getLogger(__name__)

async def task3() -> Any:
    logger.info("Starting task 3")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get('http://example.com')  # Replace with actual URL
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch data, status code: {response.status_code}")
                raise HTTPException(status_code=500, detail="Failed to fetch data")
            
            return response.json()
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred")


@app.get("/task3")
async def run_task3():
    return await task3()