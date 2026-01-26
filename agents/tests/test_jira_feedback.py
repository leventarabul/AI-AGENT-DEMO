"""Tests for Jira feedback integration.

Tests the SDLC feedback loop: execution trace → Jira comment + status update.
"""

import sys
import os
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from orchestrator.jira_feedback import JiraFeedbackService, post_trace_to_jira
from orchestrator.execution_trace import (
    ExecutionTrace,
    TriggerInfo,
    PipelineStatus,
    StepStatus,
    get_trace_store,
)


def test_format_trace_comment_success():
    """Test formatting successful pipeline trace as Jira comment."""
    
    # Create a successful trace
    trace = ExecutionTrace(
        trace_id="test-123",
        trigger=TriggerInfo(source="jira_webhook", issue_key="DEMO-42", intent_type="review_code"),
        intent_type="review_code",
        pipeline_status=PipelineStatus.SUCCESS,
        started_at="2026-01-26T10:00:00",
        execution_plan_summary="code_review_agent",
    )
    
    # Add a successful step
    step = trace.add_step(
        agent_name="code_review_agent",
        agent_task="Review pull request",
        status=StepStatus.SUCCESS,
    )
    trace.update_step(
        step_number=step.step_number,
        status=StepStatus.SUCCESS,
        success=True,
        output_summary="Decision: APPROVE",
    )
    
    trace.complete(PipelineStatus.SUCCESS)
    
    # Create mock client and service
    mock_client = MagicMock()
    service = JiraFeedbackService(mock_client)
    
    # Format comment
    comment = service._format_trace_comment(trace)
    
    # Verify comment structure
    assert "✅ **Pipeline Execution Report**" in comment
    assert "test-123" in comment
    assert "review_code" in comment
    assert "SUCCESS" in comment
    assert "code_review_agent" in comment
    assert "Decision: APPROVE" in comment
    assert "AI Agent Orchestrator" in comment
    
    print("✅ Test passed: Successful trace formatted correctly")


def test_format_trace_comment_failure():
    """Test formatting failed pipeline trace as Jira comment."""
    
    # Create a failed trace
    trace = ExecutionTrace(
        trace_id="test-456",
        trigger=TriggerInfo(source="jira_webhook", issue_key="DEMO-43", intent_type="run_tests"),
        intent_type="run_tests",
        pipeline_status=PipelineStatus.PARTIAL,
        started_at="2026-01-26T10:05:00",
        execution_plan_summary="testing_agent",
    )
    
    # Add a failed step
    step = trace.add_step(
        agent_name="testing_agent",
        agent_task="Run unit tests",
        status=StepStatus.FAIL,
    )
    trace.update_step(
        step_number=step.step_number,
        status=StepStatus.FAIL,
        success=False,
        error_message="Tests FAILED: 3 failures",
    )
    
    trace.complete(PipelineStatus.PARTIAL, "Tests FAILED: 3 failures")
    
    # Create mock client and service
    mock_client = MagicMock()
    service = JiraFeedbackService(mock_client)
    
    # Format comment
    comment = service._format_trace_comment(trace)
    
    # Verify comment structure
    assert "⚠️ **Pipeline Execution Report**" in comment
    assert "test-456" in comment
    assert "run_tests" in comment
    assert "PARTIAL" in comment
    assert "testing_agent" in comment
    assert "Tests FAILED: 3 failures" in comment
    assert "❌" in comment  # Failed step emoji
    
    print("✅ Test passed: Failed trace formatted correctly")


async def test_post_feedback_success():
    """Test posting successful pipeline feedback to Jira."""
    
    # Create a successful trace
    trace = ExecutionTrace(
        trace_id="test-789",
        trigger=TriggerInfo(source="jira_webhook", issue_key="DEMO-44", intent_type="review_code"),
        intent_type="review_code",
        pipeline_status=PipelineStatus.SUCCESS,
        started_at="2026-01-26T10:10:00",
    )
    
    step = trace.add_step(
        agent_name="code_review_agent",
        agent_task="Review code",
        status=StepStatus.SUCCESS,
    )
    trace.update_step(step.step_number, StepStatus.SUCCESS, success=True)
    trace.complete(PipelineStatus.SUCCESS)
    
    # Create mock client
    mock_client = AsyncMock()
    mock_client.add_comment = AsyncMock(return_value={"id": "comment-123"})
    mock_client.get_transitions = AsyncMock(return_value=[
        {"id": "11", "name": "Done"},
        {"id": "21", "name": "In Progress"},
    ])
    mock_client.transition_issue = AsyncMock()
    
    # Post feedback
    service = JiraFeedbackService(mock_client)
    await service.post_feedback(trace, update_status=True)
    
    # Verify comment was posted
    mock_client.add_comment.assert_called_once()
    call_args = mock_client.add_comment.call_args
    assert call_args[0][0] == "DEMO-44"  # Issue key
    assert "Pipeline Execution Report" in call_args[0][1]  # Comment text
    
    # Verify status was updated to Done
    mock_client.get_transitions.assert_called_once_with("DEMO-44")
    mock_client.transition_issue.assert_called_once_with("DEMO-44", "11")
    
    print("✅ Test passed: Successful feedback posted with status update")


async def test_post_feedback_failure():
    """Test posting failed pipeline feedback to Jira."""
    
    # Create a failed trace
    trace = ExecutionTrace(
        trace_id="test-999",
        trigger=TriggerInfo(source="jira_webhook", issue_key="DEMO-45", intent_type="run_tests"),
        intent_type="run_tests",
        pipeline_status=PipelineStatus.PARTIAL,
        started_at="2026-01-26T10:15:00",
    )
    
    step = trace.add_step(
        agent_name="testing_agent",
        agent_task="Run tests",
        status=StepStatus.FAIL,
    )
    trace.update_step(step.step_number, StepStatus.FAIL, success=False, error_message="Tests failed")
    trace.complete(PipelineStatus.PARTIAL, "Tests failed")
    
    # Create mock client
    mock_client = AsyncMock()
    mock_client.add_comment = AsyncMock(return_value={"id": "comment-456"})
    mock_client.get_transitions = AsyncMock(return_value=[
        {"id": "31", "name": "Blocked"},
        {"id": "21", "name": "In Progress"},
    ])
    mock_client.transition_issue = AsyncMock()
    
    # Post feedback
    service = JiraFeedbackService(mock_client)
    await service.post_feedback(trace, update_status=True)
    
    # Verify comment was posted
    mock_client.add_comment.assert_called_once()
    call_args = mock_client.add_comment.call_args
    assert call_args[0][0] == "DEMO-45"
    assert "PARTIAL" in call_args[0][1]
    assert "Tests failed" in call_args[0][1]
    
    # Verify status was updated to Blocked
    mock_client.get_transitions.assert_called_once_with("DEMO-45")
    mock_client.transition_issue.assert_called_once_with("DEMO-45", "31")
    
    print("✅ Test passed: Failed feedback posted with Blocked status")


async def test_post_trace_to_jira_by_id():
    """Test posting trace to Jira by trace ID."""
    
    # Create and store a trace
    trace = ExecutionTrace(
        trace_id="trace-abc",
        trigger=TriggerInfo(source="jira_webhook", issue_key="DEMO-46", intent_type="review_code"),
        intent_type="review_code",
        pipeline_status=PipelineStatus.SUCCESS,
        started_at="2026-01-26T10:20:00",
    )
    trace.complete(PipelineStatus.SUCCESS)
    
    # Store trace
    get_trace_store().store(trace)
    
    # Mock the JiraClient
    with patch('orchestrator.jira_feedback.JiraClient') as MockJiraClient:
        mock_client_instance = AsyncMock()
        MockJiraClient.return_value = mock_client_instance
        
        mock_client_instance.add_comment = AsyncMock()
        mock_client_instance.get_transitions = AsyncMock(return_value=[
            {"id": "11", "name": "Done"},
        ])
        mock_client_instance.transition_issue = AsyncMock()
        
        # Post trace by ID
        await post_trace_to_jira(
            trace_id="trace-abc",
            jira_url="https://jira.example.com",
            username="test@example.com",
            api_token="test-token",
            update_status=True,
        )
        
        # Verify comment was posted
        mock_client_instance.add_comment.assert_called_once()
        assert mock_client_instance.add_comment.call_args[0][0] == "DEMO-46"
    
    print("✅ Test passed: Trace posted to Jira by ID")


async def test_no_feedback_without_issue_key():
    """Test that feedback is skipped when trace has no issue key."""
    
    # Create trace without issue key
    trace = ExecutionTrace(
        trace_id="test-no-key",
        trigger=TriggerInfo(source="manual", intent_type="review_code"),  # No issue_key
        intent_type="review_code",
        pipeline_status=PipelineStatus.SUCCESS,
        started_at="2026-01-26T10:25:00",
    )
    trace.complete(PipelineStatus.SUCCESS)
    
    # Create mock client
    mock_client = AsyncMock()
    mock_client.add_comment = AsyncMock()
    
    # Post feedback
    service = JiraFeedbackService(mock_client)
    await service.post_feedback(trace, update_status=True)
    
    # Verify no comment was posted
    mock_client.add_comment.assert_not_called()
    
    print("✅ Test passed: No feedback posted when issue_key is missing")


async def test_status_update_fallback():
    """Test that status update falls back from Blocked to In Review."""
    
    # Create a failed trace
    trace = ExecutionTrace(
        trace_id="test-fallback",
        trigger=TriggerInfo(source="jira_webhook", issue_key="DEMO-47", intent_type="run_tests"),
        intent_type="run_tests",
        pipeline_status=PipelineStatus.PARTIAL,
        started_at="2026-01-26T10:30:00",
    )
    trace.complete(PipelineStatus.PARTIAL, "Some error")
    
    # Create mock client with only "In Review" transition available
    mock_client = AsyncMock()
    mock_client.add_comment = AsyncMock()
    mock_client.get_transitions = AsyncMock(return_value=[
        {"id": "21", "name": "In Review"},
        {"id": "31", "name": "In Progress"},
    ])
    mock_client.transition_issue = AsyncMock()
    
    # Post feedback
    service = JiraFeedbackService(mock_client)
    await service.post_feedback(trace, update_status=True)
    
    # Verify status was updated to "In Review" (fallback from "Blocked")
    mock_client.transition_issue.assert_called_once_with("DEMO-47", "21")
    
    print("✅ Test passed: Status update falls back to In Review when Blocked not available")


if __name__ == "__main__":
    print("\n=== Running Jira Feedback Tests ===\n")
    
    # Synchronous tests
    test_format_trace_comment_success()
    test_format_trace_comment_failure()
    
    # Async tests
    asyncio.run(test_post_feedback_success())
    asyncio.run(test_post_feedback_failure())
    asyncio.run(test_post_trace_to_jira_by_id())
    asyncio.run(test_no_feedback_without_issue_key())
    asyncio.run(test_status_update_fallback())
    
    print("\n✅ ALL JIRA FEEDBACK TESTS PASSED\n")
