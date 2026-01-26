"""Integration test for TestingAgent with orchestrator.

Tests:
- TestingAgent is properly integrated with orchestrator
- PASS status allows pipeline to continue
- FAIL status stops pipeline immediately
- Test results are propagated correctly
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from orchestrator.orchestrator import Orchestrator
from agents.testing_agent import TestingAgent, TestStatus


def test_testing_agent_pass_continues_pipeline():
    """Test that PASS status allows pipeline to continue."""
    print("\n▶ Testing: PASS status continues pipeline")
    
    # Create mock TestingAgent that always passes
    class MockPassingTestAgent:
        def execute(self, context):
            from agents.testing_agent import TestResult, TestStatus
            return TestResult(
                success=True,
                status=TestStatus.PASS,
                test_count=5,
                passed_count=5,
                failed_count=0,
                summary="All 5 tests passed",
            )
    
    # Create orchestrator and inject mock agent
    orchestrator = Orchestrator()
    orchestrator._agent_instances["testing_agent"] = MockPassingTestAgent()
    
    # Check that PASS status is allowed to continue
    mock_output = MockPassingTestAgent().execute({})
    should_continue, error = orchestrator._check_agent_result("testing_agent", mock_output)
    
    assert should_continue == True, "PASS status should allow pipeline to continue"
    assert error is None, "PASS status should not have error message"
    
    print("  ✓ PASS status allows continuation")


def test_testing_agent_fail_stops_pipeline():
    """Test that FAIL status stops pipeline immediately."""
    print("\n▶ Testing: FAIL status stops pipeline")
    
    # Create mock TestingAgent that always fails
    class MockFailingTestAgent:
        def execute(self, context):
            from agents.testing_agent import TestResult, TestStatus, TestFailure
            return TestResult(
                success=False,
                status=TestStatus.FAIL,
                test_count=5,
                passed_count=3,
                failed_count=2,
                failures=[
                    TestFailure(
                        test_name="test_example.py::test_addition",
                        error_message="AssertionError: assert 3 == 4"
                    ),
                    TestFailure(
                        test_name="test_example.py::test_multiplication",
                        error_message="AssertionError: assert 12 == 13"
                    ),
                ],
                summary="2 test(s) failed out of 5",
            )
    
    # Create orchestrator and inject mock agent
    orchestrator = Orchestrator()
    orchestrator._agent_instances["testing_agent"] = MockFailingTestAgent()
    
    # Check that FAIL status stops pipeline
    mock_output = MockFailingTestAgent().execute({})
    should_continue, error = orchestrator._check_agent_result("testing_agent", mock_output)
    
    assert should_continue == False, "FAIL status should stop pipeline"
    assert error is not None, "FAIL status should have error message"
    assert "Tests FAILED" in error, "Error should mention 'Tests FAILED'"
    assert "2 failures" in error or "2 test(s) failed" in error, "Error should mention failure count"
    
    print("  ✓ FAIL status stops pipeline")
    print(f"  ✓ Error message: {error}")


def test_testing_agent_in_orchestrator_registry():
    """Test that TestingAgent is properly registered in orchestrator."""
    print("\n▶ Testing: TestingAgent registration")
    
    orchestrator = Orchestrator()
    
    # Get testing agent
    agent = orchestrator._get_agent("testing_agent")
    
    assert agent is not None, "Should be able to get testing_agent"
    assert isinstance(agent, TestingAgent), "Should return TestingAgent instance"
    assert hasattr(agent, 'execute'), "Agent should have execute method"
    
    print("  ✓ TestingAgent is registered")
    print("  ✓ Agent has execute() method")


def test_testing_agent_execute_returns_valid_structure():
    """Test that TestingAgent returns valid structure expected by orchestrator."""
    print("\n▶ Testing: TestingAgent output structure")
    
    agent = TestingAgent()
    
    # Execute with minimal context
    result = agent.execute({"test_path": "tests/"})
    
    # Verify structure expected by orchestrator
    assert hasattr(result, 'success'), "Result must have success field"
    assert hasattr(result, 'status'), "Result must have status field"
    assert result.status in [TestStatus.PASS, TestStatus.FAIL], "Status must be PASS or FAIL"
    
    print("  ✓ Result has required fields")
    print(f"  ✓ Status: {result.status}")


def test_deterministic_test_results():
    """Test that same tests produce same results (determinism)."""
    print("\n▶ Testing: Deterministic behavior")
    
    agent = TestingAgent()
    
    # Parse same output twice
    stdout = "===== 10 passed in 3.14s ====="
    result1 = agent._parse_pytest_output(returncode=0, stdout=stdout, stderr="")
    result2 = agent._parse_pytest_output(returncode=0, stdout=stdout, stderr="")
    
    # Results should be identical
    assert result1.status == result2.status, "Same input should produce same status"
    assert result1.test_count == result2.test_count, "Same input should produce same counts"
    assert result1.summary == result2.summary, "Same input should produce same summary"
    
    print("  ✓ Same input produces same output")
    print("  ✓ Deterministic behavior verified")


def run_all_tests():
    """Run all integration tests."""
    print("\n" + "="*60)
    print("TESTING AGENT INTEGRATION TESTS")
    print("="*60)
    
    test_testing_agent_pass_continues_pipeline()
    test_testing_agent_fail_stops_pipeline()
    test_testing_agent_in_orchestrator_registry()
    test_testing_agent_execute_returns_valid_structure()
    test_deterministic_test_results()
    
    print("\n" + "="*60)
    print("✅ ALL INTEGRATION TESTS PASSED")
    print("="*60 + "\n")


if __name__ == "__main__":
    run_all_tests()
