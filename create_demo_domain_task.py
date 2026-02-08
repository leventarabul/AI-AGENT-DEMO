import logging
logger = logging.getLogger(__name__)
#!/usr/bin/env python3
"""Create a demo-domain task in Jira to test agent capabilities"""
import os
import asyncio
import httpx

async def main():
    jira_url = os.getenv("JIRA_URL")
    jira_user = os.getenv("JIRA_USERNAME")
    jira_token = os.getenv("JIRA_TOKEN")
    
    if not all([jira_url, jira_user, jira_token]):
        logger.info("❌ Jira credentials not set in .env")
        logger.info(f"   JIRA_URL={jira_url}")
        logger.info(f"   JIRA_USERNAME={jira_user}")
        logger.info(f"   JIRA_TOKEN={jira_token}")
        return
    
    task_data = {
        "fields": {
            "project": {"key": "DEMO"},
            "summary": "Add customer_segment filter to campaign rules",
            "description": "Add support for filtering campaign rules by customer_segment. The rule_condition should support matching customer_segment values like 'VIP', 'PREMIUM', 'STANDARD', 'BASIC'. Update the database schema, API, and job processor logic.",
            "issuetype": {"name": "Task"},
            "labels": ["demo-domain", "campaign-rules"],
        }
    }
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{jira_url}/rest/api/3/issues",
                json=task_data,
                auth=(jira_user, jira_token),
                timeout=10
            )
            if resp.status_code in [201, 200]:
                result = resp.json()
                key = result.get('key')
                logger.info(f"✅ Created Jira task: {key}")
                logger.info(f"   URL: {jira_url}/browse/{key}")
                logger.info(f"\nThis task describes demo-domain requirements.")
                logger.info(f"The agent now has demo-domain context and can generate:")
                logger.info(f"  - Database migration code")
                logger.info(f"  - API endpoint changes")
                logger.info(f"  - Business logic updates")
                logger.info(f"  - Unit tests")
                return key
            else:
                logger.info(f"❌ Failed to create task: {resp.status_code}")
                logger.info(resp.text)
        except Exception as e:
            logger.info(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
