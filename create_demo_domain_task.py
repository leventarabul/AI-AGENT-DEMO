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
        print("❌ Jira credentials not set in .env")
        print(f"   JIRA_URL={jira_url}")
        print(f"   JIRA_USERNAME={jira_user}")
        print(f"   JIRA_TOKEN={jira_token}")
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
                print(f"✅ Created Jira task: {key}")
                print(f"   URL: {jira_url}/browse/{key}")
                print(f"\nThis task describes demo-domain requirements.")
                print(f"The agent now has demo-domain context and can generate:")
                print(f"  - Database migration code")
                print(f"  - API endpoint changes")
                print(f"  - Business logic updates")
                print(f"  - Unit tests")
                return key
            else:
                print(f"❌ Failed to create task: {resp.status_code}")
                print(resp.text)
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
