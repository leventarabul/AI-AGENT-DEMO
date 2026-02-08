"""Tests for MVP Jira workflow transitions."""

import os
import sys
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from orchestrator.workflow import run_mvp_jira_flow


def _mock_dev_result():
    return SimpleNamespace(success=True, files=[], commit_message="msg", error=None)


def _mock_review_result():
    return SimpleNamespace(success=True, decision="APPROVE", error=None)


def test_transition_selected_when_available():
    with patch("orchestrator.workflow.JiraClient") as jira_cls, \
         patch("orchestrator.workflow.DevelopmentAgent") as dev_cls, \
         patch("orchestrator.workflow.CodeReviewAgent") as review_cls, \
         patch("orchestrator.workflow.TestingAgent") as test_cls, \
         patch("orchestrator.workflow.format_review_comment", return_value="ok"):
        jira = jira_cls.return_value
        jira.get_issue = AsyncMock(return_value={
            "fields": {"summary": "s", "description": "d", "status": {"name": "Waiting Development"}}
        })
        jira.add_comment = AsyncMock()
        jira.transition_issue = AsyncMock()
        jira.get_available_transitions = AsyncMock(return_value=[
            {"id": "11", "name": "Finish", "to_status": "Done"}
        ])

        dev_cls.return_value.execute = MagicMock(return_value=_mock_dev_result())
        review_cls.return_value.review_pull_request = AsyncMock(return_value=_mock_review_result())
        test_cls.return_value.execute = MagicMock(return_value={
            "success": True,
            "summary": "All tests passed",
            "failed_tests": [],
            "evidence": {},
        })

        asyncio.run(run_mvp_jira_flow("ABC-10", payload={}, dry_run=False))

        jira.transition_issue.assert_called_once_with("ABC-10", transition_id="11")
        jira.add_comment.assert_any_call(
            "ABC-10",
            "✅ Task automatically transitioned to Done",
        )


def test_transition_fallback_when_not_found():
    with patch("orchestrator.workflow.JiraClient") as jira_cls, \
         patch("orchestrator.workflow.DevelopmentAgent") as dev_cls, \
         patch("orchestrator.workflow.CodeReviewAgent") as review_cls, \
         patch("orchestrator.workflow.TestingAgent") as test_cls, \
         patch("orchestrator.workflow.format_review_comment", return_value="ok"):
        jira = jira_cls.return_value
        jira.get_issue = AsyncMock(return_value={
            "fields": {"summary": "s", "description": "d", "status": {"name": "Waiting Development"}}
        })
        jira.add_comment = AsyncMock()
        jira.transition_issue = AsyncMock()
        jira.get_available_transitions = AsyncMock(return_value=[
            {"id": "12", "name": "QA", "to_status": "In QA"}
        ])

        dev_cls.return_value.execute = MagicMock(return_value=_mock_dev_result())
        review_cls.return_value.review_pull_request = AsyncMock(return_value=_mock_review_result())
        test_cls.return_value.execute = MagicMock(return_value={
            "success": True,
            "summary": "All tests passed",
            "failed_tests": [],
            "evidence": {},
        })

        asyncio.run(run_mvp_jira_flow("ABC-11", payload={}, dry_run=False))

        jira.transition_issue.assert_not_called()
        jira.add_comment.assert_any_call(
            "ABC-11",
            "⚠️ Tests passed but no suitable DONE transition was found. Please transition manually.",
        )
