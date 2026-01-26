"""
Scheduled job orchestrator for automated agent execution.
Runs background jobs every 5 minutes to process Jira tasks in various stages.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import asyncio
import os
from typing import List, Tuple
import httpx
import logging

logger = logging.getLogger(__name__)

class AgentScheduler:
    """Manages scheduled execution of AI agents."""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._jira_client = None
        # Cache env vars at init time (before scheduler starts)
        self.jira_url = os.getenv("JIRA_URL")
        self.jira_username = os.getenv("JIRA_USERNAME")
        self.jira_token = os.getenv("JIRA_API_TOKEN")
        self.ai_management_url = os.getenv("AI_MANAGEMENT_URL")
        self.git_repo_path = os.getenv("GIT_REPO_PATH", "/tmp/repo")
    
    def start(self):
        """Start the scheduler."""
        if self.scheduler.running:
            logger.warning("Scheduler already running")
            return
        
        # Add scheduled jobs (every 30 seconds)
        self.scheduler.add_job(
            self._process_development_waiting,
            IntervalTrigger(seconds=30),
            id='process_development_waiting',
            name='Process Development Waiting tasks',
            misfire_grace_time=60
        )
        
        self.scheduler.add_job(
            self._process_in_review,
            IntervalTrigger(seconds=30),
            id='process_in_review',
            name='Process In Review tasks',
            misfire_grace_time=60
        )
        
        self.scheduler.add_job(
            self._process_testing,
            IntervalTrigger(seconds=30),
            id='process_testing',
            name='Process Testing tasks',
            misfire_grace_time=60
        )
        
        self.scheduler.start()
        logger.info("✅ Scheduler started with 30-second intervals")
    
    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("⏹️  Scheduler stopped")
    
    async def _get_jira_client(self):
        """Lazy-load and return Jira client."""
        if self._jira_client is None:
            from src.clients.jira_client import JiraClient
            self._jira_client = JiraClient(
                jira_url=self.jira_url,
                username=self.jira_username,
                api_token=self.jira_token,
            )
        return self._jira_client
    
    async def _process_development_waiting(self):
        """Find and process all 'Waiting Development' tasks."""
        try:
            logger.info("🔍 Searching for 'Waiting Development' tasks...")
            jira_client = await self._get_jira_client()
            
            # JQL to find all Waiting Development tasks
            jql = 'status = "Waiting Development" AND assignee is EMPTY'
            issues = await jira_client.search_issues(jql)
            
            if not issues:
                logger.info("  No 'Waiting Development' tasks found")
                return
            
            logger.info(f"  Found {len(issues)} task(s) to process")
            
            # Process each issue (key or id fallback)
            for issue in issues:
                if isinstance(issue, dict):
                    issue_key = issue.get('key') or issue.get('id') or str(issue)
                else:
                    issue_key = str(issue)
                if not issue_key:
                    logger.warning(f"  Skipping issue without key: {issue}")
                    continue
                await self._trigger_jira_agent(issue_key)
        
        except Exception as e:
            logger.error(f"❌ Error in _process_development_waiting: {e}")
    
    async def _process_in_review(self):
        """Find and process all 'In Review' tasks."""
        try:
            logger.info("🔍 Searching for 'In Review' tasks...")
            jira_client = await self._get_jira_client()
            
            # JQL to find all review-ready tasks
            jql = 'status in ("Code Review", "In Review")'
            issues = await jira_client.search_issues(jql)
            
            if not issues:
                logger.info("  No 'In Review' tasks found")
                return
            
            logger.info(f"  Found {len(issues)} task(s) to review")
            
            # Process each issue
            for issue in issues:
                issue_key = issue.get('key')
                await self._trigger_code_review_agent(issue_key)
        
        except Exception as e:
            logger.error(f"❌ Error in _process_in_review: {e}")
    
    async def _process_testing(self):
        """Find and process all 'Testing' tasks."""
        try:
            logger.info("🔍 Searching for 'Testing' tasks...")
            jira_client = await self._get_jira_client()
            
            # JQL to find all Testing tasks
            jql = 'status = "Testing"'
            issues = await jira_client.search_issues(jql)
            
            if not issues:
                logger.info("  No 'Testing' tasks found")
                return
            
            logger.info(f"  Found {len(issues)} task(s) to test")
            
            # Process each issue
            for issue in issues:
                issue_key = issue.get('key')
                await self._trigger_testing_agent(issue_key)
        
        except Exception as e:
            logger.error(f"❌ Error in _process_testing: {e}")
    
    async def _trigger_jira_agent(self, issue_key: str):
        """Trigger JiraAgent for an issue."""
        try:
            from src.agents.jira_agent import JiraAgent
            
            logger.info(f"  🚀 Processing {issue_key} with JiraAgent...")
            agent = JiraAgent(
                jira_url=self.jira_url,
                jira_username=self.jira_username,
                jira_token=self.jira_token,
                ai_management_url=self.ai_management_url,
                git_repo_path=self.git_repo_path,
            )
            result = await agent.process_task(issue_key)
            logger.info(f"  ✅ {issue_key} processed successfully")
        
        except Exception as e:
            logger.error(f"  ❌ Error processing {issue_key}: {e}")
    
    async def _trigger_code_review_agent(self, issue_key: str):
        """Trigger CodeReviewAgent for an issue."""
        try:
            from src.agents.code_review_agent import CodeReviewAgent
            
            logger.info(f"  🔍 Reviewing {issue_key} with CodeReviewAgent...")
            agent = CodeReviewAgent(
                ai_management_url=self.ai_management_url,
                jira_url=self.jira_url,
                jira_username=self.jira_username,
                jira_token=self.jira_token,
            )
            result = await agent.review_pull_request(issue_key, [])
            logger.info(f"  ✅ {issue_key} reviewed successfully")
        
        except Exception as e:
            logger.error(f"  ❌ Error reviewing {issue_key}: {e}")
    
    async def _trigger_testing_agent(self, issue_key: str):
        """Trigger TestingAgent for an issue."""
        try:
            from src.agents.testing_agent import TestingAgent
            
            logger.info(f"  🧪 Testing {issue_key} with TestingAgent...")
            agent = TestingAgent(
                jira_url=self.jira_url,
                jira_username=self.jira_username,
                jira_token=self.jira_token,
                repo_path=self.git_repo_path,
            )
            result = await agent.run_tests(issue_key, [])
            logger.info(f"  ✅ {issue_key} tested successfully")
        
        except Exception as e:
            logger.error(f"  ❌ Error testing {issue_key}: {e}")

# Global scheduler instance
_scheduler_instance = None

def get_scheduler() -> AgentScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = AgentScheduler()
    return _scheduler_instance
