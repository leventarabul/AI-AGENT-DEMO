import logging
logger = logging.getLogger(__name__)
#!/usr/bin/env python3
"""Check Jira status of tasks"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'agents/src'))

from clients.jira_client import JiraClient

async def check_jira():
    client = JiraClient(
        jira_url=os.getenv("JIRA_URL"),
        username=os.getenv("JIRA_USERNAME"),
        api_token=os.getenv("JIRA_API_TOKEN"),
    )
    
    # Check for tasks in Code Review
    logger.info("Checking for tasks in Code Review...")
    issues = await client.search_issues('status = "Code Review" ORDER BY updated DESC')
    
    if issues:
        logger.info(f"\nFound {len(issues)} task(s) in Code Review:\n")
        for issue in issues[:5]:
            key = issue.get('key', 'N/A')
            summary = issue.get('fields', {}).get('summary', 'N/A')
            status = issue.get('fields', {}).get('status', {}).get('name', 'N/A')
            logger.info(f"  • {key}: {summary}")
            logger.info(f"    Status: {status}\n")
    else:
        logger.info("No tasks in Code Review\n")
    
    # Check for Development Waiting
    logger.info("Checking for Development Waiting tasks...")
    issues = await client.search_issues('status = "Development Waiting" ORDER BY updated DESC')
    
    if issues:
        logger.info(f"\nFound {len(issues)} Development Waiting task(s):\n")
        for issue in issues[:5]:
            key = issue.get('key', 'N/A')
            summary = issue.get('fields', {}).get('summary', 'N/A')
            logger.info(f"  • {key}: {summary}\n")
    else:
        logger.info("No Development Waiting tasks\n")

if __name__ == "__main__":
    asyncio.run(check_jira())
