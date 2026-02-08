import logging
logger = logging.getLogger(__name__)
#!/usr/bin/env python3
"""Test that agents understand demo-domain context"""
import asyncio
import os
import sys

sys.path.insert(0, '/Users/levent/Documents/AI-Agent-demo/agents/src')
sys.path.insert(0, '/Users/levent/Documents/AI-Agent-demo/agents')

from src.knowledge.context_loader import build_ai_prompt
from src.agents.jira_agent import JiraAgent

async def main():
    # Check the prompt includes demo-domain
    prompt = build_ai_prompt(
        task_title="Add customer_segment field to campaigns",
        task_description="Add a new customer_segment field (VARCHAR 50) to the campaigns table. This field should store customer segment types like 'VIP', 'STANDARD', 'BASIC'. Update the API to accept and return this field. Update the rule matching to support filtering by customer_segment.",
        labels=["demo-domain", "backend"]
    )
    
    logger.info("✅ Prompt structure check:")
    logger.info(f"  - Total prompt size: {len(prompt)} bytes")
    logger.info(f"  - Has demo-domain API: {'Demo-Domain API Examples' in prompt}")
    logger.info(f"  - Has database schema: {'database' in prompt.lower()}")
    logger.info(f"  - Has campaigns table: {'campaigns' in prompt.lower()}")
    
    # Extract just the relevant section to see what demo-domain context looks like
    start_idx = prompt.find("## Demo-Domain")
    if start_idx != -1:
        end_idx = prompt.find("\nTASK TITLE:", start_idx)
        demo_section = prompt[start_idx:end_idx]
        logger.info(f"\n📋 Demo-Domain Context Section ({len(demo_section)} bytes):")
        logger.info(demo_section[:500] + "...\n" if len(demo_section) > 500 else demo_section)
    
    # Try to generate code
    logger.info("🤖 Testing code generation...")
    agent = JiraAgent(
        jira_url="http://localhost:8001",  # dummy
        jira_username="test",
        jira_token="test",
        git_repo_path="/tmp"
    )
    
    result = await agent.generate_code(
        task_title="Add customer_segment field to campaigns",
        task_description="Add a new customer_segment field (VARCHAR 50) to the campaigns table. This field should store customer segment types like 'VIP', 'STANDARD', 'BASIC'. Update the API to accept and return this field.",
        labels=["demo-domain", "backend"]
    )
    
    logger.info(f"✅ Code generated: {len(result['code'])} bytes")
    logger.info(f"\nFirst 800 chars of generated code:")
    logger.info("```python")
    logger.info(result['code'][:800])
    logger.info("...")
    logger.info("```")

if __name__ == "__main__":
    asyncio.run(main())
