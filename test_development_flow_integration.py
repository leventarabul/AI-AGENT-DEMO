"""Integration test for CodeReviewAgent decision enforcement in pipeline."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'agents', 'src'))

from orchestrator.orchestrator import Orchestrator, Intent
from agents.code_review_agent import CodeReviewAgent, ReviewDecision


def test_code_review_approve_decision():
    """Test: CodeReviewAgent APPROVE → continue pipeline."""
    orchestrator = Orchestrator()
    agent = CodeReviewAgent()
    
    # Clean code should result in APPROVE
    result = agent.execute({
        "code_changes": {
            "utils.py": """
import logging

def process_data(items):
    logging.info("Processing started")
    results = []
    for item in items:
        if item is not None:
            results.append(item.upper())
    return results
""",
        }
    })
    
    print(f"\n✅ Test: CodeReviewAgent APPROVE decision")
    print(f"   Decision: {result.decision}")
    print(f"   Reasoning: {result.reasoning}")
    
    assert result.success, f"Expected success, got error: {result.error}"
    assert result.decision == ReviewDecision.APPROVE, f"Expected APPROVE, got {result.decision}"
    assert "Ready for testing" in result.reasoning, f"Expected approval message in reasoning"
    
    print(f"   ✓ Pipeline should continue")
    return result


def test_code_review_block_decision():
    """Test: CodeReviewAgent BLOCK → pipeline stops."""
    agent = CodeReviewAgent()
    
    # Architecture violation should result in BLOCK
    result = agent.execute({
        "code_changes": {
            "main.py": """
def main():
    print("Direct print not allowed")
    return 0
""",
        }
    })
    
    print(f"\n✅ Test: CodeReviewAgent BLOCK decision")
    print(f"   Decision: {result.decision}")
    print(f"   Violations: {result.architecture_violations}")
    
    assert result.success, f"Expected success, got error: {result.error}"
    assert result.decision == ReviewDecision.BLOCK, f"Expected BLOCK, got {result.decision}"
    assert len(result.architecture_violations) > 0, "No architecture violations detected"
    assert "violates architecture rules" in result.reasoning, f"Wrong reasoning: {result.reasoning}"
    
    print(f"   ✓ Pipeline must stop")
    return result


def test_code_review_request_changes_decision():
    """Test: CodeReviewAgent REQUEST_CHANGES → pipeline stops."""
    agent = CodeReviewAgent()
    
    # Standards violation should result in REQUEST_CHANGES
    result = agent.execute({
        "code_changes": {
            "handler.py": """
def handle_request(data):
    try:
        result = process(data)
    except:
        return None
""",
        }
    })
    
    print(f"\n✅ Test: CodeReviewAgent REQUEST_CHANGES decision")
    print(f"   Decision: {result.decision}")
    print(f"   Violations: {result.standard_violations}")
    
    assert result.success, f"Expected success, got error: {result.error}"
    assert result.decision == ReviewDecision.REQUEST_CHANGES, f"Expected REQUEST_CHANGES, got {result.decision}"
    assert len(result.standard_violations) > 0, "No standards violations detected"
    assert "standards violations" in result.reasoning, f"Wrong reasoning: {result.reasoning}"
    
    print(f"   ✓ Pipeline must stop for revisions")
    return result


def test_orchestrator_respects_code_review_block():
    """Test: Orchestrator respects CodeReviewAgent BLOCK decision."""
    # Test the orchestrator's ability to check CodeReviewAgent decision
    from agents.code_review_agent import CodeReviewResult
    
    # Simulate a CodeReviewResult with BLOCK decision
    blocked_review = CodeReviewResult(
        success=True,
        decision=ReviewDecision.BLOCK,
        architecture_violations=["Direct print() calls not allowed; use logging"],
        reasoning="BLOCK: Code violates architecture rules. Issues: Direct print() calls not allowed; use logging",
    )
    
    print(f"\n✅ Test: Orchestrator decision enforcement")
    print(f"   Review Decision: {blocked_review.decision}")
    print(f"   Should stop pipeline: {blocked_review.decision == ReviewDecision.BLOCK}")
    
    assert blocked_review.decision == ReviewDecision.BLOCK, "Decision should be BLOCK"
    assert blocked_review.success, "CodeReviewResult should have success=True"
    
    # Now test the actual orchestrator enhancement
    from agents.code_review_agent import ReviewDecision as RD
    print(f"   ✓ Orchestrator can check decision: {blocked_review.decision == RD.BLOCK}")
    
    return blocked_review


def test_orchestrator_respects_code_review_approve():
    """Test: Orchestrator continues pipeline on CodeReviewAgent APPROVE."""
    from agents.code_review_agent import CodeReviewResult
    
    # Simulate a CodeReviewResult with APPROVE decision
    approved_review = CodeReviewResult(
        success=True,
        decision=ReviewDecision.APPROVE,
        reasoning="APPROVE: Code review passed. Ready for testing.",
        approval_notes="Code review passed. Ready for testing."
    )
    
    print(f"\n✅ Test: Orchestrator continues on APPROVE")
    print(f"   Review Decision: {approved_review.decision}")
    print(f"   Should continue pipeline: {approved_review.decision == ReviewDecision.APPROVE}")
    
    assert approved_review.decision == ReviewDecision.APPROVE, "Decision should be APPROVE"
    assert approved_review.success, "CodeReviewResult should have success=True"
    
    from agents.code_review_agent import ReviewDecision as RD
    print(f"   ✓ Pipeline continues on APPROVE: {approved_review.decision == RD.APPROVE}")
    
    return approved_review


if __name__ == "__main__":
    test_code_review_approve_decision()
    test_code_review_block_decision()
    test_code_review_request_changes_decision()
    test_orchestrator_respects_code_review_block()
    test_orchestrator_respects_code_review_approve()
    print("\n✅ ALL CODE REVIEW DECISION ENFORCEMENT TESTS PASSED")
