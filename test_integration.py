#!/usr/bin/env python3
"""Integration test for hardened CodeReviewAgent."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'agents', 'src'))

from orchestrator.orchestrator import Orchestrator, Intent
from agents.code_review_agent import CodeReviewAgent, ReviewDecision

def test_orchestrator_routing():
    """Test that orchestrator correctly routes review_code intent."""
    orchestrator = Orchestrator()
    
    # Route review_code intent
    intent = Intent(
        type="review_code",
        context={
            "repository": "AI-Agent-demo",
            "target_branch": "feature/test",
            "code_changes": {
                "test.py": "import logging\nlogging.info('test')"
            }
        }
    )
    decision = orchestrator.route(intent)
    
    assert decision.status == "success", f"Orchestrator routing failed: {decision.error}"
    assert len(decision.agents) > 0, "No agents returned"
    assert "code_review_agent" in decision.agents, f"code_review_agent not in agents: {decision.agents}"
    
    print("✅ Orchestrator routing test passed")
    print(f"   Intent: {intent.type}")
    print(f"   Agents: {decision.agents}")
    return decision

def test_code_review_direct():
    """Test CodeReviewAgent execution directly."""
    agent = CodeReviewAgent()
    
    # Execute with clean code
    result = agent.execute({
        "code_changes": {
            "test.py": "import logging\nlogging.info('test')"
        }
    })
    
    assert result.success, f"Execution failed: {result.error}"
    assert result.decision == ReviewDecision.APPROVE, f"Expected APPROVE, got {result.decision}"
    assert "Ready for testing" in result.reasoning, f"Expected approval reasoning, got {result.reasoning}"
    
    print("✅ CodeReviewAgent direct execution test passed")
    print(f"   Decision: {result.decision}")
    print(f"   Reasoning: {result.reasoning}")
    return result

def test_code_review_with_violations():
    """Test CodeReviewAgent with architecture violations."""
    agent = CodeReviewAgent()
    
    # Execute with architecture violation
    result = agent.execute({
        "code_changes": {
            "test.py": "def main():\n    print('not allowed')"
        }
    })
    
    assert result.success, f"Execution failed: {result.error}"
    assert result.decision == ReviewDecision.BLOCK, f"Expected BLOCK, got {result.decision}"
    assert len(result.architecture_violations) > 0, "No architecture violations detected"
    assert "violates architecture rules" in result.reasoning, f"Wrong reasoning: {result.reasoning}"
    
    print("✅ CodeReviewAgent violation detection test passed")
    print(f"   Decision: {result.decision}")
    print(f"   Violations: {result.architecture_violations}")
    return result

if __name__ == "__main__":
    test_orchestrator_routing()
    test_code_review_direct()
    test_code_review_with_violations()
    print("\n✅ ALL INTEGRATION TESTS PASSED")
