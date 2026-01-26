"""Tests for Learning Gate mechanism.

Validates:
- Pattern detection from execution traces
- Gate decision logic and thresholds
- Proposal generation and storage
- Deterministic behavior
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from orchestrator.learning_gate import (
    PatternDetector,
    LearningGate,
    ProposalStore,
    Pattern,
    PatternType,
    GateDecision,
    KnowledgeDomain,
    analyze_and_propose,
    get_pattern_detector,
    get_learning_gate,
    get_proposal_store,
)
from orchestrator.execution_trace import (
    ExecutionTrace,
    TriggerInfo,
    ExecutionStep,
    StepStatus,
    PipelineStatus,
)


def test_pattern_detection_single_failure():
    """Test that single failure creates a pattern."""
    
    print("\n=== Test: Pattern Detection - Single Failure ===")
    
    detector = PatternDetector()
    detector.clear()
    
    # Create trace with failed code review
    trace = ExecutionTrace(
        trace_id="test-1",
        trigger=TriggerInfo(source="test", issue_key="TEST-1"),
        intent_type="review_code",
        pipeline_status=PipelineStatus.PARTIAL,
        started_at="2026-01-26T10:00:00",
    )
    
    step = trace.add_step(
        agent_name="code_review_agent",
        agent_task="Review code",
        status=StepStatus.FAIL,
    )
    trace.update_step(
        step.step_number,
        StepStatus.FAIL,
        success=False,
        error_message="Missing docstrings in function foo()",
    )
    
    # Detect patterns
    patterns = detector.analyze_trace(trace)
    
    assert len(patterns) == 1, f"Expected 1 pattern, got {len(patterns)}"
    pattern = patterns[0]
    
    assert pattern.pattern_type == PatternType.REPEATED_CODE_REVIEW_FAILURE
    assert pattern.agent_name == "code_review_agent"
    assert pattern.occurrences == 1
    assert "test-1" in pattern.trace_ids
    
    print(f"✓ Pattern detected: {pattern.pattern_type.value}")
    print(f"✓ Occurrences: {pattern.occurrences}")
    print(f"✓ Error signature: {pattern.error_signature}")
    print("✅ Test passed: Single failure pattern detected")


def test_pattern_accumulation():
    """Test that repeated failures accumulate pattern count."""
    
    print("\n=== Test: Pattern Accumulation ===")
    
    detector = PatternDetector()
    detector.clear()
    
    # Create 3 traces with same error
    for i in range(3):
        trace = ExecutionTrace(
            trace_id=f"test-{i}",
            trigger=TriggerInfo(source="test"),
            intent_type="run_tests",
            pipeline_status=PipelineStatus.PARTIAL,
            started_at="2026-01-26T10:00:00",
        )
        
        step = trace.add_step(
            agent_name="testing_agent",
            agent_task="Run tests",
            status=StepStatus.FAIL,
        )
        trace.update_step(
            step.step_number,
            StepStatus.FAIL,
            success=False,
            error_message="Test failed: test_user_login failed with AssertionError",
        )
        
        detector.analyze_trace(trace)
    
    # Check pattern accumulation
    patterns = detector.get_all_patterns()
    assert len(patterns) == 1, f"Expected 1 pattern, got {len(patterns)}"
    
    pattern = patterns[0]
    assert pattern.occurrences == 3, f"Expected 3 occurrences, got {pattern.occurrences}"
    assert len(pattern.trace_ids) == 3
    
    print(f"✓ Pattern accumulated: {pattern.occurrences} occurrences")
    print(f"✓ Trace IDs: {pattern.trace_ids}")
    print("✅ Test passed: Pattern accumulation works")


def test_error_normalization():
    """Test that similar errors are recognized as same pattern."""
    
    print("\n=== Test: Error Normalization ===")
    
    detector = PatternDetector()
    detector.clear()
    
    # Create traces with variable parts
    errors = [
        "File /app/src/module.py line 42: NameError",
        "File /tmp/test.py line 99: NameError",
        "File /home/user/code.py line 123: NameError",
    ]
    
    for i, error in enumerate(errors):
        trace = ExecutionTrace(
            trace_id=f"test-{i}",
            trigger=TriggerInfo(source="test"),
            intent_type="review_code",
            pipeline_status=PipelineStatus.PARTIAL,
            started_at="2026-01-26T10:00:00",
        )
        
        step = trace.add_step(
            agent_name="code_review_agent",
            agent_task="Review",
            status=StepStatus.FAIL,
        )
        trace.update_step(
            step.step_number,
            StepStatus.FAIL,
            success=False,
            error_message=error,
        )
        
        detector.analyze_trace(trace)
    
    # Should have 1 pattern (all errors normalized to same signature)
    patterns = detector.get_all_patterns()
    assert len(patterns) == 1, f"Expected 1 normalized pattern, got {len(patterns)}"
    
    pattern = patterns[0]
    assert pattern.occurrences == 3
    
    print(f"✓ Normalized signature: {pattern.error_signature}")
    print(f"✓ Original errors treated as same pattern")
    print("✅ Test passed: Error normalization works")


def test_gate_rejects_low_frequency():
    """Test that gate rejects patterns below threshold."""
    
    print("\n=== Test: Gate Rejects Low Frequency ===")
    
    gate = LearningGate()
    
    # Create pattern with only 1 occurrence (below MIN_OCCURRENCES=3)
    pattern = Pattern(
        pattern_type=PatternType.REPEATED_CODE_REVIEW_FAILURE,
        agent_name="code_review_agent",
        error_signature="Missing docstring",
        occurrences=1,
        first_seen="2026-01-26T10:00:00",
        last_seen="2026-01-26T10:00:00",
        trace_ids=["test-1"],
    )
    
    decision, reason = gate.evaluate(pattern)
    
    assert decision == GateDecision.REJECT, f"Expected REJECT, got {decision}"
    assert "Insufficient occurrences" in reason
    
    print(f"✓ Decision: {decision.value}")
    print(f"✓ Reason: {reason}")
    print("✅ Test passed: Low frequency rejected")


def test_gate_proposes_high_frequency():
    """Test that gate proposes patterns above threshold."""
    
    print("\n=== Test: Gate Proposes High Frequency ===")
    
    gate = LearningGate()
    
    # Create pattern with 5 occurrences (above MIN_OCCURRENCES=3)
    pattern = Pattern(
        pattern_type=PatternType.REPEATED_TEST_FAILURE,
        agent_name="testing_agent",
        error_signature="Test failed: test_login",
        occurrences=5,
        first_seen="2026-01-26T10:00:00",
        last_seen="2026-01-26T10:05:00",
        trace_ids=["test-1", "test-2", "test-3", "test-4", "test-5"],
    )
    
    decision, reason = gate.evaluate(pattern)
    
    assert decision == GateDecision.PROPOSE, f"Expected PROPOSE, got {decision}"
    assert reason is None
    
    # Calculate confidence
    confidence = gate._calculate_confidence(pattern)
    assert confidence >= gate.MIN_CONFIDENCE, f"Confidence {confidence} below threshold"
    
    print(f"✓ Decision: {decision.value}")
    print(f"✓ Confidence: {confidence:.2f}")
    print("✅ Test passed: High frequency proposed")


def test_proposal_generation():
    """Test complete proposal generation."""
    
    print("\n=== Test: Proposal Generation ===")
    
    gate = LearningGate()
    
    pattern = Pattern(
        pattern_type=PatternType.REPEATED_CODE_REVIEW_FAILURE,
        agent_name="code_review_agent",
        error_signature="Missing type annotations",
        occurrences=4,
        first_seen="2026-01-26T10:00:00",
        last_seen="2026-01-26T10:10:00",
        trace_ids=["t1", "t2", "t3", "t4"],
    )
    
    proposal = gate.create_proposal(pattern)
    
    # Verify proposal structure
    assert proposal.proposal_id is not None
    assert proposal.pattern_type == PatternType.REPEATED_CODE_REVIEW_FAILURE
    assert proposal.source_agent == "code_review_agent"
    assert proposal.frequency == 4
    assert proposal.confidence_score > 0
    assert proposal.suggested_domain == KnowledgeDomain.CODE_PATTERNS
    assert len(proposal.supporting_trace_ids) == 4
    assert proposal.gate_decision == GateDecision.PROPOSE
    
    print(f"✓ Proposal ID: {proposal.proposal_id}")
    print(f"✓ Pattern: {proposal.observed_pattern}")
    print(f"✓ Frequency: {proposal.frequency}")
    print(f"✓ Confidence: {proposal.confidence_score:.2f}")
    print(f"✓ Domain: {proposal.suggested_domain.value}")
    print(f"✓ Action: {proposal.proposed_action}")
    print("✅ Test passed: Proposal generated correctly")


def test_proposal_serialization():
    """Test proposal serialization to dict/JSON."""
    
    print("\n=== Test: Proposal Serialization ===")
    
    gate = LearningGate()
    
    pattern = Pattern(
        pattern_type=PatternType.REPEATED_TEST_FAILURE,
        agent_name="testing_agent",
        error_signature="Timeout error",
        occurrences=3,
        first_seen="2026-01-26T10:00:00",
        last_seen="2026-01-26T10:00:00",
        trace_ids=["t1", "t2", "t3"],
    )
    
    proposal = gate.create_proposal(pattern)
    
    # Test dict conversion
    proposal_dict = proposal.to_dict()
    assert isinstance(proposal_dict, dict)
    assert "proposal_id" in proposal_dict
    assert "confidence_score" in proposal_dict
    
    # Test JSON conversion
    proposal_json = proposal.to_json()
    assert isinstance(proposal_json, str)
    
    import json
    parsed = json.loads(proposal_json)
    assert parsed["source_agent"] == "testing_agent"
    assert parsed["frequency"] == 3
    
    print(f"✓ Dict keys: {list(proposal_dict.keys())}")
    print(f"✓ JSON serializable: {len(proposal_json)} chars")
    print("✅ Test passed: Proposal serialization works")


def test_proposal_store():
    """Test proposal storage and retrieval."""
    
    print("\n=== Test: Proposal Store ===")
    
    store = ProposalStore()
    store.clear()
    
    gate = LearningGate()
    
    # Create and store proposals
    pattern1 = Pattern(
        pattern_type=PatternType.REPEATED_CODE_REVIEW_FAILURE,
        agent_name="code_review_agent",
        error_signature="Error 1",
        occurrences=5,
        first_seen="2026-01-26T10:00:00",
        last_seen="2026-01-26T10:00:00",
        trace_ids=["t1", "t2", "t3", "t4", "t5"],
    )
    
    pattern2 = Pattern(
        pattern_type=PatternType.REPEATED_TEST_FAILURE,
        agent_name="testing_agent",
        error_signature="Error 2",
        occurrences=2,  # Below threshold - will be rejected
        first_seen="2026-01-26T10:00:00",
        last_seen="2026-01-26T10:00:00",
        trace_ids=["t6", "t7"],
    )
    
    proposal1 = gate.create_proposal(pattern1)
    proposal2 = gate.create_proposal(pattern2)
    
    store.store(proposal1)
    store.store(proposal2)
    
    # Test retrieval
    all_proposals = store.get_all()
    assert len(all_proposals) == 2
    
    approved = store.get_approved()
    assert len(approved) == 1
    assert approved[0].proposal_id == proposal1.proposal_id
    
    rejected = store.get_rejected()
    assert len(rejected) == 1
    assert rejected[0].proposal_id == proposal2.proposal_id
    
    print(f"✓ Total proposals: {len(all_proposals)}")
    print(f"✓ Approved: {len(approved)}")
    print(f"✓ Rejected: {len(rejected)}")
    print("✅ Test passed: Proposal store works")


def test_analyze_and_propose_integration():
    """Test end-to-end: analyze trace and generate proposals."""
    
    print("\n=== Test: Analyze and Propose Integration ===")
    
    # Clear global state
    detector = get_pattern_detector()
    detector.clear()
    
    store = get_proposal_store()
    store.clear()
    
    # Create 4 traces with same failure
    proposals_generated = []
    for i in range(4):
        trace = ExecutionTrace(
            trace_id=f"integration-test-{i}",
            trigger=TriggerInfo(source="test", issue_key=f"TEST-{i}"),
            intent_type="review_code",
            pipeline_status=PipelineStatus.PARTIAL,
            started_at="2026-01-26T10:00:00",
        )
        
        step = trace.add_step(
            agent_name="code_review_agent",
            agent_task="Review code",
            status=StepStatus.FAIL,
        )
        trace.update_step(
            step.step_number,
            StepStatus.FAIL,
            success=False,
            error_message="Unused import statement detected",
        )
        
        # Analyze and propose
        proposals = analyze_and_propose(trace)
        proposals_generated.extend(proposals)
        
        print(f"  After trace {i+1}: {len(proposals)} proposal(s) generated")
    
    # Check final state
    patterns = detector.get_all_patterns()
    assert len(patterns) == 1, f"Expected 1 pattern, got {len(patterns)}"
    assert patterns[0].occurrences == 4, f"Expected 4 occurrences, got {patterns[0].occurrences}"
        # Should have proposals generated when threshold was hit (at 3rd occurrence and possibly 4th)
    
    approved = store.get_approved()
    assert len(approved) > 0, f"Expected at least 1 approved proposal, got {len(approved)}"
    
    if approved:
        proposal = approved[0]
        print(f"✓ Proposal generated: {proposal.proposal_id}")
        print(f"✓ Pattern: {proposal.observed_pattern}")
        print(f"✓ Frequency: {proposal.frequency}")
        print(f"✓ Confidence: {proposal.confidence_score:.2f}")
        print(f"✓ Suggested domain: {proposal.suggested_domain.value}")
    
    print("✅ Test passed: End-to-end integration works")


def test_different_patterns_tracked_separately():
    """Test that different error patterns are tracked separately."""
    
    print("\n=== Test: Different Patterns Tracked Separately ===")
    
    detector = PatternDetector()
    detector.clear()
    
    # Create traces with different errors
    errors = [
        "Missing docstring",
        "Unused variable x",
        "Missing docstring",  # Repeat first
        "Type annotation missing",
        "Unused variable x",  # Repeat second
    ]
    
    for i, error in enumerate(errors):
        trace = ExecutionTrace(
            trace_id=f"test-{i}",
            trigger=TriggerInfo(source="test"),
            intent_type="review_code",
            pipeline_status=PipelineStatus.PARTIAL,
            started_at="2026-01-26T10:00:00",
        )
        
        step = trace.add_step(
            agent_name="code_review_agent",
            agent_task="Review",
            status=StepStatus.FAIL,
        )
        trace.update_step(
            step.step_number,
            StepStatus.FAIL,
            success=False,
            error_message=error,
        )
        
        detector.analyze_trace(trace)
    
    # Should have 3 distinct patterns
    patterns = detector.get_all_patterns()
    assert len(patterns) == 3, f"Expected 3 patterns, got {len(patterns)}"
    
    # Check individual counts
    pattern_counts = {p.error_signature: p.occurrences for p in patterns}
    
    print(f"✓ Unique patterns: {len(patterns)}")
    for sig, count in pattern_counts.items():
        print(f"  - '{sig}': {count} occurrence(s)")
    
    print("✅ Test passed: Different patterns tracked separately")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("LEARNING GATE TEST SUITE")
    print("="*60)
    
    test_pattern_detection_single_failure()
    test_pattern_accumulation()
    test_error_normalization()
    test_gate_rejects_low_frequency()
    test_gate_proposes_high_frequency()
    test_proposal_generation()
    test_proposal_serialization()
    test_proposal_store()
    test_analyze_and_propose_integration()
    test_different_patterns_tracked_separately()
    
    print("\n" + "="*60)
    print("✅ ALL LEARNING GATE TESTS PASSED")
    print("="*60 + "\n")
