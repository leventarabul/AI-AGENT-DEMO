"""Tests for MVP Jira workflow completed logic."""

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


def test_completed_true_when_testing_success():
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
        jira.get_transitions = AsyncMock(return_value=[])

        dev_cls.return_value.execute = MagicMock(return_value=_mock_dev_result())
        review_cls.return_value.review_pull_request = AsyncMock(return_value=_mock_review_result())
        test_cls.return_value.execute = MagicMock(return_value={
            "success": True,
            "summary": "All tests passed",
            "failed_tests": [],
            "evidence": {},
        })

        result = asyncio.run(run_mvp_jira_flow("ABC-1", payload={}, dry_run=True))

        assert result["completed"] is True
        assert result["testing"]["success"] is True


def test_completed_false_when_testing_fails():
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
        jira.get_transitions = AsyncMock(return_value=[])

        dev_cls.return_value.execute = MagicMock(return_value=_mock_dev_result())
        review_cls.return_value.review_pull_request = AsyncMock(return_value=_mock_review_result())
        test_cls.return_value.execute = MagicMock(return_value={
            "success": False,
            "summary": "2 tests failed",
            "failed_tests": [{"test_name": "tests/test_demo.py::test_one", "error_message": "AssertionError"}],
            "evidence": {},
        })

        result = asyncio.run(run_mvp_jira_flow("ABC-2", payload={}, dry_run=True))

        assert result["completed"] is False
        assert result["testing"]["success"] is False
