"""Test suite for hardened TestingAgent.

Validates:
- Execute method returns structured dict
- PASS/FAIL status is correctly determined
- Test counts are parsed accurately
- Failures are extracted properly
- Deterministic behavior (same tests = same results)
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agents.testing_agent import TestingAgent, TestResult, TestStatus, TestFailure


def test_execute_method_signature():
    """Test that execute() method exists and has correct signature."""
    agent = TestingAgent()
    
    # Execute with minimal context
    context = {"test_path": "tests/"}
    result = agent.execute(context)
    
    # Verify result structure
    assert isinstance(result, dict), "execute() must return a structured dict"
    assert "success" in result, "Result must include success field"
    assert "summary" in result, "Result must include summary field"
    assert "failed_tests" in result, "Result must include failed_tests field"
    assert "evidence" in result, "Result must include evidence field"
    
    print("✓ test_execute_method_signature passed")


def test_pass_status():
    """Test PASS status when all tests pass."""
    agent = TestingAgent()
    
    # Simulate passing tests by parsing pytest output
    result = agent._parse_pytest_output(
        returncode=0,
        stdout="===== 5 passed in 1.23s =====",
        stderr="",
    )
    
    assert result.status == TestStatus.PASS, "Status should be PASS when returncode is 0"
    assert result.success == True, "success should be True for passing tests"
    assert result.passed_count == 5, "Should parse 5 passed tests"
    assert result.failed_count == 0, "Should have 0 failed tests"
    assert len(result.failures) == 0, "Should have no failure details"
    assert "passed" in result.summary.lower(), "Summary should mention 'passed'"
    
    print("✓ test_pass_status passed")


def test_fail_status():
    """Test FAIL status when tests fail."""
    agent = TestingAgent()
    
    # Simulate failing tests
    result = agent._parse_pytest_output(
        returncode=1,
        stdout="""
FAILED tests/test_example.py::test_addition - AssertionError: assert 3 == 4
FAILED tests/test_example.py::test_subtraction - AssertionError: assert 1 == 2
===== 3 passed, 2 failed in 2.45s =====
        """,
        stderr="",
    )
    
    assert result.status == TestStatus.FAIL, "Status should be FAIL when returncode is non-zero"
    assert result.success == False, "success should be False for failing tests"
    assert result.passed_count == 3, "Should parse 3 passed tests"
    assert result.failed_count == 2, "Should parse 2 failed tests"
    assert result.test_count == 5, "Should calculate total as 5"
    assert len(result.failures) == 2, "Should extract 2 failure details"
    assert "failed" in result.summary.lower(), "Summary should mention 'failed'"
    
    # Verify failure details
    failure_names = [f.test_name for f in result.failures]
    assert "tests/test_example.py::test_addition" in failure_names
    assert "tests/test_example.py::test_subtraction" in failure_names
    
    print("✓ test_fail_status passed")


def test_failure_extraction():
    """Test that failure details are extracted correctly."""
    agent = TestingAgent()
    
    stdout = """
FAILED tests/test_math.py::test_divide_by_zero - ZeroDivisionError: division by zero
FAILED tests/test_strings.py::test_empty - ValueError: empty string
===== 0 passed, 2 failed in 0.5s =====
    """
    
    failures = agent._extract_failures(stdout)
    
    assert len(failures) == 2, "Should extract 2 failures"
    
    # Check first failure
    assert failures[0].test_name == "tests/test_math.py::test_divide_by_zero"
    assert "ZeroDivisionError" in failures[0].error_message
    assert failures[0].file_path == "tests/test_math.py"
    
    # Check second failure
    assert failures[1].test_name == "tests/test_strings.py::test_empty"
    assert "ValueError" in failures[1].error_message
    assert failures[1].file_path == "tests/test_strings.py"
    
    print("✓ test_failure_extraction passed")


def test_deterministic_behavior():
    """Test that same input produces same output."""
    agent = TestingAgent()
    
    stdout = "===== 10 passed in 3.14s ====="
    
    # Run parsing twice
    result1 = agent._parse_pytest_output(returncode=0, stdout=stdout, stderr="")
    result2 = agent._parse_pytest_output(returncode=0, stdout=stdout, stderr="")
    
    # Results should be identical
    assert result1.status == result2.status
    assert result1.success == result2.success
    assert result1.test_count == result2.test_count
    assert result1.passed_count == result2.passed_count
    assert result1.failed_count == result2.failed_count
    assert result1.summary == result2.summary
    
    print("✓ test_deterministic_behavior passed")


def test_skipped_tests():
    """Test parsing of skipped tests."""
    agent = TestingAgent()
    
    result = agent._parse_pytest_output(
        returncode=0,
        stdout="===== 5 passed, 2 skipped in 1.5s =====",
        stderr="",
    )
    
    assert result.passed_count == 5, "Should parse 5 passed tests"
    assert result.skipped_count == 2, "Should parse 2 skipped tests"
    assert result.test_count == 7, "Total should be 7"
    assert result.status == TestStatus.PASS, "Skipped tests don't fail the run"
    
    print("✓ test_skipped_tests passed")


def test_duration_parsing():
    """Test that duration is extracted."""
    agent = TestingAgent()
    
    result = agent._parse_pytest_output(
        returncode=0,
        stdout="===== 10 passed in 12.34s =====",
        stderr="",
    )
    
    assert result.duration_seconds == 12.34, "Should parse duration correctly"
    
    print("✓ test_duration_parsing passed")


def test_error_handling():
    """Test that errors are properly captured."""
    agent = TestingAgent()
    
    # Test with context that will cause an error (bad path)
    # Note: pytest may still return valid output even for bad paths
    # So we test that the agent handles it gracefully
    context = {"test_path": "/nonexistent/path/to/tests"}
    result = agent.execute(context)
    
    # Should return a valid result (even if no tests found)
    assert isinstance(result, dict), "Should return structured dict"
    assert "success" in result, "Result should include success"
    assert "summary" in result, "Result should include summary"
    
    print("✓ test_error_handling passed")


def test_read_only_behavior():
    """Test that agent doesn't modify code or call other agents."""
    agent = TestingAgent()
    
    # Verify no methods that modify code
    agent_methods = dir(agent)
    forbidden_methods = ['write_file', 'modify_code', 'commit', 'push', 'call_agent']
    
    for forbidden in forbidden_methods:
        assert forbidden not in agent_methods, f"Agent should not have {forbidden} method"
    
    # Verify only has execute and internal methods
    public_methods = [m for m in agent_methods if not m.startswith('_') and callable(getattr(agent, m))]
    assert public_methods == ['execute'], "Agent should only expose execute() method"
    
    print("✓ test_read_only_behavior passed")


def run_all_tests():
    """Run all test cases."""
    print("\n" + "="*60)
    print("TESTING AGENT TEST SUITE")
    print("="*60 + "\n")
    
    test_execute_method_signature()
    test_pass_status()
    test_fail_status()
    test_failure_extraction()
    test_deterministic_behavior()
    test_skipped_tests()
    test_duration_parsing()
    test_error_handling()
    test_read_only_behavior()
    
    print("\n" + "="*60)
    print("✅ ALL TESTING AGENT TESTS PASSED")
    print("="*60 + "\n")


if __name__ == "__main__":
    run_all_tests()
