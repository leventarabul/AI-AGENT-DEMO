"""Integration test for Jira feedback with real orchestrator execution.

Tests the full SDLC feedback loop:
1. Orchestrator executes pipeline
2. ExecutionTrace is created
3. Jira feedback is posted with trace details
"""

import sys
import os
import asyncio
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from orchestrator.orchestrator import Orchestrator, Intent
from orchestrator.jira_feedback import post_trace_to_jira
from orchestrator.execution_trace import get_trace_store
from unittest.mock import patch


# Mock agent for testing
class MockSuccessAgent:
    """Mock agent that always succeeds."""
    
    def execute(self, context):
        return MagicMock(
            success=True,
            output="Test output",
            decision=None,
            status=None,
        )


class MockFailingAgent:
    """Mock agent that always fails."""
    
    def execute(self, context):
        return MagicMock(
            success=False,
            error="Mock failure",
        )


async def test_successful_pipeline_with_jira_feedback():
    """Test complete flow: successful pipeline → Jira comment + Done status."""
    
    print("\n=== Test: Successful Pipeline with Jira Feedback ===")
    
    # Create orchestrator with mock agent
    orchestrator = Orchestrator()
    orchestrator._agent_instances["event_agent"] = MockSuccessAgent()
    
    # Create intent with Jira context and all required fields
    intent = Intent(
        type="register_event",
        context={
            "event_code": "PURCHASE",
            "customer_id": "cust-123",
            "transaction_id": "txn-456",
            "merchant_id": "merch-789",
            "amount": 100.0,
            "issue_key": "DEMO-100",
        },
        metadata={"source": "jira_webhook"},
    )
    
    # Execute pipeline
    result = orchestrator.execute(intent)
    
    # Verify execution succeeded
    assert result.status == "success", f"Expected success, got {result.status}"
    assert result.trace_id is not None
    
    print(f"✓ Pipeline executed successfully, trace_id: {result.trace_id}")
    
    # Verify trace exists
    trace = get_trace_store().get(result.trace_id)
    assert trace is not None
    assert trace.trigger.issue_key == "DEMO-100"
    assert trace.pipeline_status.value == "SUCCESS"
    
    print(f"✓ Trace stored correctly with issue_key: {trace.trigger.issue_key}")
    
    # Mock Jira client and post feedback
    with patch('orchestrator.jira_feedback.JiraClient') as MockJiraClient:
        mock_client = AsyncMock()
        MockJiraClient.return_value = mock_client
        
        mock_client.add_comment = AsyncMock(return_value={"id": "comment-1"})
        mock_client.get_transitions = AsyncMock(return_value=[
            {"id": "11", "name": "Done"},
        ])
        mock_client.transition_issue = AsyncMock()
        
        # Post feedback
        await post_trace_to_jira(
            trace_id=result.trace_id,
            jira_url="https://jira.example.com",
            username="test@example.com",
            api_token="test-token",
            update_status=True,
        )
        
        # Verify Jira was updated
        mock_client.add_comment.assert_called_once()
        call_args = mock_client.add_comment.call_args[0]
        
        assert call_args[0] == "DEMO-100", f"Expected DEMO-100, got {call_args[0]}"
        comment_text = call_args[1]
        
        # Verify comment content
        assert "✅" in comment_text  # Success emoji
        assert "Pipeline Execution Report" in comment_text
        assert result.trace_id in comment_text
        assert "register_event" in comment_text
        assert "SUCCESS" in comment_text
        
        print(f"✓ Jira comment posted with success status")
        
        # Verify status transition to Done
        mock_client.transition_issue.assert_called_once_with("DEMO-100", "11")
        
        print(f"✓ Jira issue transitioned to Done")
    
    print("✅ Test passed: Successful pipeline with Jira feedback")


async def test_failed_pipeline_with_jira_feedback():
    """Test complete flow: failed pipeline → Jira comment + Blocked status."""
    
    print("\n=== Test: Failed Pipeline with Jira Feedback ===")
    
    # Create orchestrator with failing mock agent
    orchestrator = Orchestrator()
    orchestrator._agent_instances["event_agent"] = MockFailingAgent()
    
    # Create intent with Jira context and all required fields
    intent = Intent(
        type="register_event",
        context={
            "event_code": "PURCHASE",
            "customer_id": "cust-456",
            "transaction_id": "txn-789",
            "merchant_id": "merch-123",
            "amount": 200.0,
            "issue_key": "DEMO-101",
        },
        metadata={"source": "jira_webhook"},
    )
    
    # Execute pipeline
    result = orchestrator.execute(intent)
    
    # Verify execution failed
    assert result.status == "partial", f"Expected partial, got {result.status}"
    assert result.error is not None
    assert result.trace_id is not None
    
    print(f"✓ Pipeline failed as expected, trace_id: {result.trace_id}")
    
    # Verify trace exists with failure
    trace = get_trace_store().get(result.trace_id)
    assert trace is not None
    assert trace.trigger.issue_key == "DEMO-101"
    assert trace.pipeline_status.value == "PARTIAL"
    assert trace.final_error is not None
    
    print(f"✓ Trace stored with failure, error: {trace.final_error}")
    
    # Mock Jira client and post feedback
    with patch('orchestrator.jira_feedback.JiraClient') as MockJiraClient:
        mock_client = AsyncMock()
        MockJiraClient.return_value = mock_client
        
        mock_client.add_comment = AsyncMock(return_value={"id": "comment-2"})
        mock_client.get_transitions = AsyncMock(return_value=[
            {"id": "31", "name": "Blocked"},
            {"id": "21", "name": "In Review"},
        ])
        mock_client.transition_issue = AsyncMock()
        
        # Post feedback
        await post_trace_to_jira(
            trace_id=result.trace_id,
            jira_url="https://jira.example.com",
            username="test@example.com",
            api_token="test-token",
            update_status=True,
        )
        
        # Verify Jira was updated
        mock_client.add_comment.assert_called_once()
        call_args = mock_client.add_comment.call_args[0]
        
        assert call_args[0] == "DEMO-101"
        comment_text = call_args[1]
        
        # Verify comment content
        assert "⚠️" in comment_text  # Partial failure emoji
        assert "Pipeline Execution Report" in comment_text
        assert result.trace_id in comment_text
        assert "PARTIAL" in comment_text
        assert "Mock failure" in comment_text
        
        print(f"✓ Jira comment posted with failure details")
        
        # Verify status transition to Blocked
        mock_client.transition_issue.assert_called_once_with("DEMO-101", "31")
        
        print(f"✓ Jira issue transitioned to Blocked")
    
    print("✅ Test passed: Failed pipeline with Jira feedback")


async def test_pipeline_without_jira_issue():
    """Test that feedback is skipped for pipelines without Jira issue key."""
    
    print("\n=== Test: Pipeline Without Jira Issue ===")
    
    # Create orchestrator with mock agent
    orchestrator = Orchestrator()
    orchestrator._agent_instances["event_agent"] = MockSuccessAgent()
    
    # Create intent WITHOUT issue_key but with all required fields
    intent = Intent(
        type="register_event",
        context={
            "event_code": "PURCHASE",
            "customer_id": "cust-789",
            "transaction_id": "txn-123",
            "merchant_id": "merch-456",
            "amount": 300.0,
        },
        metadata={"source": "manual"},
    )
    
    # Execute pipeline
    result = orchestrator.execute(intent)
    
    # Verify execution succeeded
    assert result.status == "success"
    assert result.trace_id is not None
    
    print(f"✓ Pipeline executed, trace_id: {result.trace_id}")
    
    # Mock Jira client and try to post feedback
    with patch('orchestrator.jira_feedback.JiraClient') as MockJiraClient:
        mock_client = AsyncMock()
        MockJiraClient.return_value = mock_client
        
        mock_client.add_comment = AsyncMock()
        
        # Post feedback
        await post_trace_to_jira(
            trace_id=result.trace_id,
            jira_url="https://jira.example.com",
            username="test@example.com",
            api_token="test-token",
            update_status=True,
        )
        
        # Verify NO Jira calls were made
        mock_client.add_comment.assert_not_called()
        
        print(f"✓ No Jira updates made (no issue_key)")
    
    print("✅ Test passed: Pipeline without Jira issue skips feedback")


if __name__ == "__main__":
    print("\n=== Running Jira Feedback Integration Tests ===\n")
    
    asyncio.run(test_successful_pipeline_with_jira_feedback())
    asyncio.run(test_failed_pipeline_with_jira_feedback())
    asyncio.run(test_pipeline_without_jira_issue())
    
    print("\n✅ ALL JIRA FEEDBACK INTEGRATION TESTS PASSED\n")
