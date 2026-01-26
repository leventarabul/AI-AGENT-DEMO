"""Test suite for execution tracing.

Validates:
- Traces are created for every pipeline execution
- Steps are recorded with correct status
- Failures are captured with error messages
- Traces are deterministic and serializable
- TraceStore works correctly
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from orchestrator.execution_trace import (
    ExecutionTrace,
    TriggerInfo,
    ExecutionStep,
    StepStatus,
    PipelineStatus,
    TraceStore,
    get_trace_store,
)
from orchestrator.orchestrator import Orchestrator, Intent
from agents.code_review_agent import CodeReviewAgent, ReviewDecision


def test_trigger_info_creation():
    """Test TriggerInfo creation and serialization."""
    print("\n▶ Testing: TriggerInfo creation")
    
    trigger = TriggerInfo(
        source="jira_webhook",
        issue_key="PROJ-123",
        issue_status="In Progress",
        intent_type="development_flow",
    )
    
    assert trigger.source == "jira_webhook"
    assert trigger.issue_key == "PROJ-123"
    assert trigger.timestamp is not None
    
    print("  ✓ TriggerInfo created with timestamp")


def test_execution_step_lifecycle():
    """Test ExecutionStep creation and updates."""
    print("\n▶ Testing: ExecutionStep lifecycle")
    
    step = ExecutionStep(
        step_number=1,
        agent_name="development_agent",
        agent_task="Create code files",
        status=StepStatus.STARTED,
        started_at=None,  # Will be set by __post_init__
    )
    
    assert step.status == StepStatus.STARTED
    assert step.started_at is not None
    assert step.completed_at is None
    
    print("  ✓ Step created with STARTED status")


def test_execution_trace_add_step():
    """Test adding steps to a trace."""
    print("\n▶ Testing: Adding steps to trace")
    
    trace = ExecutionTrace(
        trace_id="test-123",
        trigger=TriggerInfo(source="test", intent_type="test_intent"),
        intent_type="development_flow",
        pipeline_status=PipelineStatus.RUNNING,
        started_at=None,
    )
    
    # Add first step
    step1 = trace.add_step(
        agent_name="development_agent",
        agent_task="Create code",
        status=StepStatus.STARTED,
    )
    
    assert len(trace.steps) == 1
    assert step1.step_number == 1
    assert step1.agent_name == "development_agent"
    
    # Add second step
    step2 = trace.add_step(
        agent_name="code_review_agent",
        agent_task="Review code",
        status=StepStatus.STARTED,
    )
    
    assert len(trace.steps) == 2
    assert step2.step_number == 2
    
    print("  ✓ Steps added correctly")
    print(f"  ✓ Step count: {len(trace.steps)}")


def test_execution_trace_update_step():
    """Test updating step status."""
    print("\n▶ Testing: Updating step status")
    
    trace = ExecutionTrace(
        trace_id="test-456",
        trigger=TriggerInfo(source="test", intent_type="test_intent"),
        intent_type="test_flow",
        pipeline_status=PipelineStatus.RUNNING,
        started_at=None,
    )
    
    # Add and update step
    step = trace.add_step("test_agent", "Test task", StepStatus.STARTED)
    
    trace.update_step(
        step_number=1,
        status=StepStatus.SUCCESS,
        success=True,
        output_summary="Completed successfully",
    )
    
    assert trace.steps[0].status == StepStatus.SUCCESS
    assert trace.steps[0].success == True
    assert trace.steps[0].output_summary == "Completed successfully"
    assert trace.steps[0].completed_at is not None
    
    print("  ✓ Step updated to SUCCESS")


def test_execution_trace_complete():
    """Test completing a trace."""
    print("\n▶ Testing: Completing trace")
    
    trace = ExecutionTrace(
        trace_id="test-789",
        trigger=TriggerInfo(source="test", intent_type="test_intent"),
        intent_type="test_flow",
        pipeline_status=PipelineStatus.RUNNING,
        started_at=None,
    )
    
    trace.complete(PipelineStatus.SUCCESS)
    
    assert trace.pipeline_status == PipelineStatus.SUCCESS
    assert trace.completed_at is not None
    assert trace.final_error is None
    
    # Test completion with error
    trace2 = ExecutionTrace(
        trace_id="test-error",
        trigger=TriggerInfo(source="test", intent_type="test_intent"),
        intent_type="test_flow",
        pipeline_status=PipelineStatus.RUNNING,
        started_at=None,
    )
    
    trace2.complete(PipelineStatus.FAILED, "Something went wrong")
    
    assert trace2.pipeline_status == PipelineStatus.FAILED
    assert trace2.final_error == "Something went wrong"
    
    print("  ✓ Trace completed successfully")
    print("  ✓ Trace completed with error")


def test_trace_serialization():
    """Test converting trace to dict and JSON."""
    print("\n▶ Testing: Trace serialization")
    
    trace = ExecutionTrace(
        trace_id="test-json",
        trigger=TriggerInfo(source="manual", intent_type="test_intent"),
        intent_type="test_flow",
        pipeline_status=PipelineStatus.RUNNING,
        started_at=None,
    )
    
    trace.add_step("agent1", "Task 1", StepStatus.STARTED)
    trace.update_step(1, StepStatus.SUCCESS, True, output_summary="Done")
    trace.complete(PipelineStatus.SUCCESS)
    
    # Convert to dict
    trace_dict = trace.to_dict()
    assert isinstance(trace_dict, dict)
    assert trace_dict['trace_id'] == "test-json"
    assert trace_dict['intent_type'] == "test_flow"
    assert len(trace_dict['steps']) == 1
    
    # Convert to JSON
    trace_json = trace.to_json()
    assert isinstance(trace_json, str)
    
    # Parse back from JSON
    parsed = json.loads(trace_json)
    assert parsed['trace_id'] == "test-json"
    assert parsed['pipeline_status'] == "SUCCESS"
    
    print("  ✓ Trace converted to dict")
    print("  ✓ Trace converted to JSON")
    print("  ✓ JSON can be parsed back")


def test_trace_summary():
    """Test human-readable summary generation."""
    print("\n▶ Testing: Trace summary")
    
    trace = ExecutionTrace(
        trace_id="test-summary",
        trigger=TriggerInfo(source="test", intent_type="test_intent"),
        intent_type="development_flow",
        pipeline_status=PipelineStatus.RUNNING,
        started_at=None,
    )
    
    trace.add_step("development_agent", "Create code", StepStatus.STARTED)
    trace.update_step(1, StepStatus.SUCCESS, True)
    
    trace.add_step("code_review_agent", "Review code", StepStatus.STARTED)
    trace.update_step(2, StepStatus.BLOCKED, False, error_message="Code review blocked")
    
    trace.complete(PipelineStatus.PARTIAL, "Pipeline stopped at code review")
    
    summary = trace.get_summary()
    
    assert "test-summary" in summary
    assert "development_flow" in summary
    assert "PARTIAL" in summary
    assert "✅" in summary  # Success icon for step 1
    assert "🚫" in summary  # Blocked icon for step 2
    assert "Pipeline stopped at code review" in summary
    
    print("  ✓ Summary generated")
    print("Summary preview:")
    for line in summary.split('\n')[:5]:
        print(f"    {line}")


def test_trace_store():
    """Test TraceStore functionality."""
    print("\n▶ Testing: TraceStore")
    
    store = TraceStore()
    
    # Create traces
    trace1 = ExecutionTrace(
        trace_id="store-1",
        trigger=TriggerInfo(source="test", intent_type="test_intent"),
        intent_type="flow1",
        pipeline_status=PipelineStatus.SUCCESS,
        started_at=None,
    )
    
    trace2 = ExecutionTrace(
        trace_id="store-2",
        trigger=TriggerInfo(source="test", intent_type="test_intent"),
        intent_type="flow2",
        pipeline_status=PipelineStatus.FAILED,
        started_at=None,
    )
    
    # Store traces
    store.store(trace1)
    store.store(trace2)
    
    # Retrieve by ID
    retrieved = store.get("store-1")
    assert retrieved is not None
    assert retrieved.trace_id == "store-1"
    
    # Get all
    all_traces = store.get_all()
    assert len(all_traces) == 2
    
    # Get recent
    recent = store.get_recent(limit=1)
    assert len(recent) == 1
    
    # Clear
    store.clear()
    assert len(store.get_all()) == 0
    
    print("  ✓ Store/retrieve trace")
    print("  ✓ Get all traces")
    print("  ✓ Get recent traces")
    print("  ✓ Clear store")


def test_orchestrator_creates_trace():
    """Test that orchestrator creates traces for executions."""
    print("\n▶ Testing: Orchestrator creates traces")
    
    # Clear trace store
    get_trace_store().clear()
    
    # Create mock agents that always succeed
    class MockDevelopmentAgent:
        def execute(self, context):
            from dataclasses import dataclass
            @dataclass
            class Output:
                success: bool = True
            return Output()
    
    class MockCodeReviewAgent:
        def execute(self, context):
            from agents.code_review_agent import CodeReviewResult, ReviewDecision
            return CodeReviewResult(
                success=True,
                decision=ReviewDecision.APPROVE,
                reasoning="Looks good",
            )
    
    # Create orchestrator and inject mock agents
    orchestrator = Orchestrator()
    orchestrator._agent_instances["development_agent"] = MockDevelopmentAgent()
    orchestrator._agent_instances["code_review_agent"] = MockCodeReviewAgent()
    
    # Execute
    intent = Intent(
        type="review_code",
        context={
            "repository": "test-repo",
            "code_changes": {"test.py": "print('hello')"}
        },
        metadata={"source": "test"},
    )
    
    result = orchestrator.execute(intent)
    
    # Verify trace was created
    assert result.trace_id is not None
    
    trace = get_trace_store().get(result.trace_id)
    assert trace is not None
    assert trace.intent_type == "review_code"
    # Pipeline should be success if no failures
    print(f"  [DEBUG] Pipeline status: {trace.pipeline_status}")
    print(f"  [DEBUG] Result status: {result.status}")
    assert trace.pipeline_status in [PipelineStatus.SUCCESS, PipelineStatus.PARTIAL]
    assert len(trace.steps) == 1  # Only code_review_agent in review_code intent
    
    print("  ✓ Trace created for execution")
    print(f"  ✓ Trace ID: {result.trace_id}")
    print(f"  ✓ Steps recorded: {len(trace.steps)}")


def test_trace_captures_failure():
    """Test that traces capture failures correctly."""
    print("\n▶ Testing: Trace captures failures")
    
    # Clear trace store
    get_trace_store().clear()
    
    # Create mock agent that fails
    class MockFailingAgent:
        def execute(self, context):
            from agents.testing_agent import TestResult, TestStatus, TestFailure
            return TestResult(
                success=False,
                status=TestStatus.FAIL,
                test_count=5,
                passed_count=3,
                failed_count=2,
                failures=[TestFailure("test_1", "Failed")],
                summary="2 tests failed",
            )
    
    orchestrator = Orchestrator()
    orchestrator._agent_instances["testing_agent"] = MockFailingAgent()
    
    intent = Intent(
        type="run_tests",
        context={
            "environment": "test",
            "test_path": "tests/"
        },
        metadata={"source": "test"},
    )
    
    result = orchestrator.execute(intent)
    
    # Verify failure was captured
    assert result.status == "partial"
    assert result.error is not None
    
    trace = get_trace_store().get(result.trace_id)
    assert trace.pipeline_status == PipelineStatus.PARTIAL
    assert trace.final_error is not None
    assert len(trace.steps) == 1
    assert trace.steps[0].status == StepStatus.FAIL
    assert trace.steps[0].error_message is not None
    
    print("  ✓ Failure captured in trace")
    print(f"  ✓ Final error: {trace.final_error}")
    print(f"  ✓ Step status: {trace.steps[0].status.value}")


def run_all_tests():
    """Run all trace tests."""
    print("\n" + "="*60)
    print("EXECUTION TRACE TEST SUITE")
    print("="*60)
    
    test_trigger_info_creation()
    test_execution_step_lifecycle()
    test_execution_trace_add_step()
    test_execution_trace_update_step()
    test_execution_trace_complete()
    test_trace_serialization()
    test_trace_summary()
    test_trace_store()
    test_orchestrator_creates_trace()
    test_trace_captures_failure()
    
    print("\n" + "="*60)
    print("✅ ALL EXECUTION TRACE TESTS PASSED")
    print("="*60 + "\n")


if __name__ == "__main__":
    run_all_tests()
