"""Tests for Jira webhook MVP dispatch behavior."""

import os
import sys
import asyncio
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ai_server import JiraWebhookRequest, jira_webhook, TARGET_STATUS


def test_jira_webhook_skipped_when_status_not_target():
    request = JiraWebhookRequest(
        webhookEvent="jira:issue_updated",
        issue={
            "key": "ABC-1",
            "fields": {"status": {"name": "In Progress"}},
        },
    )
    background_tasks = MagicMock()
    background_tasks.add_task = MagicMock()

    result = asyncio.run(jira_webhook(request, background_tasks))

    assert result["status"] == "skipped"
    assert result["status_current"] == "In Progress"
    background_tasks.add_task.assert_not_called()


def test_jira_webhook_accepted_when_status_matches_target():
    request = JiraWebhookRequest(
        webhookEvent="jira:issue_updated",
        issue={
            "key": "ABC-2",
            "fields": {"status": {"name": TARGET_STATUS}},
        },
    )
    background_tasks = MagicMock()
    background_tasks.add_task = MagicMock()

    with patch("ai_server.run_mvp_jira_flow") as flow_mock:
        result = asyncio.run(jira_webhook(request, background_tasks))

    assert result["status"] == "accepted"
    assert result["issue_key"] == "ABC-2"
    background_tasks.add_task.assert_called_once()
    called_args = background_tasks.add_task.call_args[0]
    assert called_args[0] is flow_mock
