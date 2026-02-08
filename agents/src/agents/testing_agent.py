"""Testing agent: Hardened implementation for SDLC pipeline.

Executes real tests (pytest), captures results, and reports deterministic outcomes.
Provides two-level results: PASS or FAIL.

No code modification. No inter-agent calls.
Structured, deterministic output.
"""

import subprocess
import os
import re
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import httpx
from enum import Enum


class TestStatus(str, Enum):
    """Test execution status."""
    PASS = "PASS"
    FAIL = "FAIL"


@dataclass
class TestFailure:
    """Single test failure details."""
    test_name: str
    error_message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None


@dataclass
class TestCaseResult:
    """Single QA test case result."""
    name: str
    status: str
    details: str = ""


@dataclass
class TestResult:
    """Structured result from test execution."""
    success: bool
    status: TestStatus
    test_count: int = 0
    passed_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    failures: List[TestFailure] = field(default_factory=list)
    summary: str = ""
    coverage_percent: Optional[float] = None
    duration_seconds: Optional[float] = None
    raw_output: str = ""
    error: Optional[str] = None
    case_results: List[TestCaseResult] = field(default_factory=list)


class TestingAgent:
    """Hardened testing agent for SDLC pipeline."""
    
    def __init__(self, repo_root: str = None):
        """Initialize testing agent.
        
        Args:
            repo_root: Root directory of the repository (defaults to current directory)
        """
        self.repo_root = repo_root or os.getcwd()
    
    def execute(self, context: Dict[str, Any]) -> TestResult:
        """Execute tests and return structured results.
        
        Args:
            context: Execution context containing:
                - test_files: Optional list of specific test files to run
                - test_path: Optional path to test directory (defaults to "tests/")
                - pytest_args: Optional additional pytest arguments
        
        Returns:
            TestResult with PASS or FAIL status and detailed metrics
        """
        try:
            if context.get("qa_mode"):
                return self._run_qa_tests(context)

            test_files = context.get("test_files", None)
            test_path = context.get("test_path", "tests/")
            pytest_args = context.get("pytest_args", [])

            # Execute pytest
            result = self._run_pytest(test_files, test_path, pytest_args)

            return result
            
        except Exception as e:
            return TestResult(
                success=False,
                status=TestStatus.FAIL,
                error=f"Test execution error: {str(e)}",
                summary="Test execution failed due to internal error",
            )
    
    def _run_pytest(
        self,
        test_files: Optional[List[str]],
        test_path: str,
        pytest_args: List[str],
    ) -> TestResult:
        """Run pytest and parse results.
        
        Args:
            test_files: Specific test files to run (or None for all)
            test_path: Default test directory path
            pytest_args: Additional pytest arguments
        
        Returns:
            Parsed TestResult
        """
        # Build pytest command
        cmd = ["python", "-m", "pytest", "-v", "--tb=short"]
        
        # Add additional args
        cmd.extend(pytest_args)
        
        # Add test targets
        if test_files:
            cmd.extend(test_files)
        else:
            cmd.append(test_path)
        
        try:
            # Execute pytest
            result = subprocess.run(
                cmd,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )
            
            # Parse output
            return self._parse_pytest_output(
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
            )
            
        except subprocess.TimeoutExpired:
            return TestResult(
                success=False,
                status=TestStatus.FAIL,
                error="Test execution timed out (5 minute limit)",
                summary="Tests exceeded time limit",
                failures=[
                    TestFailure(
                        test_name="timeout",
                        error_message="Test suite exceeded 5 minute timeout",
                    )
                ],
            )
        
        except FileNotFoundError:
            return TestResult(
                success=False,
                status=TestStatus.FAIL,
                error="pytest not available - is pytest installed?",
                summary="Test framework not found",
            )
        
        except Exception as e:
            return TestResult(
                success=False,
                status=TestStatus.FAIL,
                error=f"Unexpected error: {str(e)}",
                summary="Test execution failed",
            )
    
    def _parse_pytest_output(
        self,
        returncode: int,
        stdout: str,
        stderr: str,
    ) -> TestResult:
        """Parse pytest output and extract structured results.
        
        Args:
            returncode: Pytest exit code (0 = all passed, non-zero = failures/errors)
            stdout: Standard output from pytest
            stderr: Standard error from pytest
        
        Returns:
            Structured TestResult
        """
        raw_output = f"{stdout}\n{stderr}"
        
        # Parse test counts from pytest output
        # Typical pytest output: "===== 5 passed, 2 failed in 1.23s ====="
        test_count = 0
        passed_count = 0
        failed_count = 0
        skipped_count = 0
        duration = None
        
        # Look for summary line
        for line in stdout.split("\n"):
            if "passed" in line or "failed" in line:
                # Extract numbers
                passed_match = re.search(r"(\d+)\s+passed", line)
                if passed_match:
                    passed_count = int(passed_match.group(1))
                
                failed_match = re.search(r"(\d+)\s+failed", line)
                if failed_match:
                    failed_count = int(failed_match.group(1))
                
                skipped_match = re.search(r"(\d+)\s+skipped", line)
                if skipped_match:
                    skipped_count = int(skipped_match.group(1))
                
                # Extract duration
                duration_match = re.search(r"in\s+([\d.]+)s", line)
                if duration_match:
                    duration = float(duration_match.group(1))
        
        test_count = passed_count + failed_count + skipped_count
        
        # Parse failures
        failures = self._extract_failures(stdout)
        
        # Determine status
        if returncode == 0:
            status = TestStatus.PASS
            success = True
            summary = f"All {test_count} tests passed"
        else:
            status = TestStatus.FAIL
            success = False
            if failed_count > 0:
                summary = f"{failed_count} test(s) failed out of {test_count}"
            else:
                summary = "Test execution failed"
        
        return TestResult(
            success=success,
            status=status,
            test_count=test_count,
            passed_count=passed_count,
            failed_count=failed_count,
            skipped_count=skipped_count,
            failures=failures,
            summary=summary,
            duration_seconds=duration,
            raw_output=raw_output,
        )

    def _run_qa_tests(self, context: Dict[str, Any]) -> TestResult:
        issue_key = context.get("issue_key") or context.get("jira_issue_key")
        base_url = os.getenv("DEMO_DOMAIN_URL", "http://demo-domain-api:8000")
        username = os.getenv("API_USERNAME", "admin")
        password = os.getenv("API_PASSWORD", "admin123")
        auth = (username, password)
        cases: List[TestCaseResult] = []
        failures: List[TestFailure] = []

        def record_case(name: str, ok: bool, details: str = "") -> None:
            status = "PASS" if ok else "FAIL"
            cases.append(TestCaseResult(name=name, status=status, details=details))
            if not ok:
                failures.append(
                    TestFailure(test_name=name, error_message=details or "Failed")
                )

        try:
            with httpx.Client(timeout=30, auth=auth) as client:
                # Case 1: Health check
                resp = client.get(f"{base_url}/health")
                record_case(
                    "health_check",
                    resp.status_code == 200,
                    f"status={resp.status_code}",
                )

                # Case 2: Create campaign
                campaign_payload = {
                    "name": f"QA {issue_key or 'event'} {int(time.time())}",
                    "description": "QA campaign",
                }
                resp = client.post(f"{base_url}/campaigns", json=campaign_payload)
                if resp.status_code == 200:
                    campaign = resp.json()
                    campaign_id = campaign.get("id")
                    record_case("create_campaign", True, f"id={campaign_id}")
                else:
                    campaign_id = None
                    record_case(
                        "create_campaign",
                        False,
                        f"status={resp.status_code}",
                    )

                # Case 3: Create rule
                rule_id = None
                if campaign_id:
                    rule_payload = {
                        "rule_name": "QA Rule",
                        "rule_condition": {
                            "merchant_id": "QA_MERCHANT",
                            "event_code": "QA_EVENT",
                        },
                        "reward_amount": 10.0,
                        "rule_priority": 1,
                    }
                    resp = client.post(
                        f"{base_url}/campaigns/{campaign_id}/rules",
                        json=rule_payload,
                    )
                    if resp.status_code == 200:
                        rule = resp.json()
                        rule_id = rule.get("id")
                        record_case("create_rule", True, f"id={rule_id}")
                    else:
                        record_case(
                            "create_rule",
                            False,
                            f"status={resp.status_code}",
                        )
                else:
                    record_case("create_rule", False, "campaign missing")

                # Case 4: Register event (with channel for SCRUM-7)
                event_payload = {
                    "event_code": "QA_EVENT",
                    "customer_id": "QA_CUSTOMER",
                    "transaction_id": f"qa-{int(time.time())}",
                    "merchant_id": "QA_MERCHANT",
                    "amount": 50.0,
                    "transaction_date": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "event_data": {"source": "qa"},
                }
                if issue_key and "SCRUM-7" in issue_key:
                    event_payload["channel"] = "web"

                resp = client.post(f"{base_url}/events", json=event_payload)
                if resp.status_code == 200:
                    event = resp.json()
                    event_id = event.get("id")
                    record_case("register_event", True, f"id={event_id}")
                else:
                    event_id = None
                    record_case(
                        "register_event",
                        False,
                        f"status={resp.status_code}",
                    )

                # Case 5: Trigger processing job
                resp = client.post(f"{base_url}/admin/jobs/process-events")
                record_case(
                    "trigger_job",
                    resp.status_code == 200,
                    f"status={resp.status_code}",
                )

                # Case 6: Verify event status
                if event_id:
                    status = None
                    matched_rule = None
                    for _ in range(5):
                        time.sleep(1)
                        resp = client.get(f"{base_url}/events/{event_id}")
                        if resp.status_code != 200:
                            continue
                        event = resp.json()
                        status = event.get("status")
                        matched_rule = event.get("matched_rule_id")
                        if status in ("processed", "skipped", "failed"):
                            break

                    ok = status in ("processed", "skipped", "failed")
                    details = f"status={status}, matched_rule={matched_rule}"
                    record_case("verify_event", ok, details)
                else:
                    record_case("verify_event", False, "event missing")

        except Exception as e:
            record_case("qa_tests", False, str(e))

        test_count = len(cases)
        failed_count = len([c for c in cases if c.status == "FAIL"])
        passed_count = test_count - failed_count
        status = TestStatus.PASS if failed_count == 0 else TestStatus.FAIL
        summary = f"QA cases: {passed_count}/{test_count} passed"

        return TestResult(
            success=failed_count == 0,
            status=status,
            test_count=test_count,
            passed_count=passed_count,
            failed_count=failed_count,
            failures=failures,
            summary=summary,
            case_results=cases,
        )
    
    def _extract_failures(self, stdout: str) -> List[TestFailure]:
        """Extract failure details from pytest output.
        
        Args:
            stdout: Pytest standard output
        
        Returns:
            List of TestFailure objects
        """
        failures = []
        
        # Look for FAILED test lines
        # Format: "FAILED tests/test_example.py::test_function - AssertionError: ..."
        for line in stdout.split("\n"):
            if line.startswith("FAILED"):
                match = re.match(r"FAILED\s+([^\s]+)\s+-\s+(.+)", line)
                if match:
                    test_name = match.group(1)
                    error_message = match.group(2).strip()
                    
                    # Extract file path
                    file_match = re.match(r"([^:]+)::", test_name)
                    file_path = file_match.group(1) if file_match else None
                    
                    failures.append(
                        TestFailure(
                            test_name=test_name,
                            error_message=error_message,
                            file_path=file_path,
                        )
                    )
        
        return failures
