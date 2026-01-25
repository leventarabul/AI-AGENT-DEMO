#!/usr/bin/env python3
import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, '/Users/levent/Documents/AI-Agent-demo/agents')

from dotenv import load_dotenv
from src.agents.jira_agent import JiraAgent

load_dotenv()

async def test():
    print("🚀 Testing JiraAgent with SCRUM-1...")
    
    agent = JiraAgent(
        jira_url=os.getenv("JIRA_URL"),
        jira_username=os.getenv("JIRA_USERNAME"),
        jira_token=os.getenv("JIRA_API_TOKEN"),
        ai_management_url=os.getenv("AI_MANAGEMENT_URL"),
        git_repo_path="/Users/levent/Documents/AI-Agent-demo/agents",
    )
    
    try:
        result = await agent.process_task("SCRUM-1")
        print("\n✅ RESULT:")
        print(result)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
