import logging
logger = logging.getLogger(__name__)
"""Code review agent: Hardened implementation for SDLC pipeline.

Reviews code changes against architecture rules, coding standards, and edge cases.
Provides three-level decisions: APPROVE, REQUEST_CHANGES, BLOCK.

No code modification. No inter-agent calls.
Structured, deterministic output.
"""

import subprocess
import os
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum


class ReviewDecision(str, Enum):
    """Code review decision levels."""
    APPROVE = "APPROVE"
    REQUEST_CHANGES = "REQUEST_CHANGES"
    BLOCK = "BLOCK"


@dataclass
class ReviewIssue:
    """Single code review issue."""
    severity: str
    category: str
    message: str
    line_number: Optional[int] = None
    file_path: Optional[str] = None


@dataclass
class CodeReviewResult:
    """Structured result from code review."""
    success: bool
    decision: ReviewDecision
    issues: List[ReviewIssue] = field(default_factory=list)
    architecture_violations: List[str] = field(default_factory=list)
    standard_violations: List[str] = field(default_factory=list)
    edge_cases: List[str] = field(default_factory=list)
    reasoning: str = ""
    approval_notes: Optional[str] = None
    error: Optional[str] = None


def format_review_comment(result: CodeReviewResult) -> str:
    """Format a Jira comment summarizing code review results."""
    decision = result.decision.value if result.decision else "UNKNOWN"
    header = f"**Code Review نتیجه:** {decision}"
    reasoning = result.reasoning or ""

    issues = result.issues or []
    by_file: Dict[str, List[ReviewIssue]] = {}
    for issue in issues:
        key = issue.file_path or "unknown"
        by_file.setdefault(key, []).append(issue)

    lines = [header]
    if reasoning:
        lines.append(f"**Reasoning:** {reasoning}")

    if issues:
        lines.append(f"**Issues ({len(issues)}):**")
        for file_path, file_issues in by_file.items():
            lines.append(f"- {file_path}")
            for issue in file_issues[:5]:
                loc = f"L{issue.line_number}" if issue.line_number else ""
                lines.append(f"  - [{issue.severity}] {issue.category} {loc}: {issue.message}")
            if len(file_issues) > 5:
                lines.append(f"  - ... {len(file_issues) - 5} more issue(s)")
    else:
        lines.append("**Issues:** None")

    return "\n".join(lines)


class ArchitectureRules:
    """Architecture rules for the project."""
    
    RULES = {
        "no_print_statements": {
            "pattern": r"print\(",
            "message": "Direct logger.info() calls not allowed; use logging",
        },
        "no_hardcoded_paths": {
            "pattern": r'["\']/(app|root|home)/\w+',
            "message": "Hardcoded file paths detected; use environment variables",
        },
    }


class CodingStandards:
    """Coding standards for the project."""
    MAX_LINE_LENGTH = 100


class CodeReviewAgent:
    """Hardened code review agent for SDLC pipeline."""
    
    def __init__(self, repo_root: str = None):
        """Initialize code review agent."""
        self.repo_root = repo_root or os.getcwd()
    
    def execute(self, context: Dict[str, Any]) -> CodeReviewResult:
        """Execute code review."""
        try:
            code_changes = context.get("code_changes", {})
            
            if not code_changes:
                return CodeReviewResult(
                    success=False,
                    decision=ReviewDecision.BLOCK,
                    error="No code changes to review",
                )
            
            issues = []
            architecture_violations = []
            standard_violations = []
            edge_cases = []
            
            for file_path, content in code_changes.items():
                file_issues = self._review_file(file_path, content)
                
                for issue in file_issues:
                    issues.append(issue)
                    
                    if issue.category == "architecture":
                        architecture_violations.append(issue.message)
                    elif issue.category == "standards":
                        standard_violations.append(issue.message)
                    elif issue.category == "edge_case":
                        edge_cases.append(issue.message)
            
            decision = self._make_decision(architecture_violations, standard_violations)
            reasoning = self._generate_reasoning(
                decision, architecture_violations, standard_violations, edge_cases
            )
            approval_notes = "Code review passed. Ready for testing." if decision == ReviewDecision.APPROVE \
            else None
            
            return CodeReviewResult(
                success=True,
                decision=decision,
                issues=issues,
                architecture_violations=architecture_violations,
                standard_violations=standard_violations,
                edge_cases=edge_cases,
                reasoning=reasoning,
                approval_notes=approval_notes,
            )
            
        except Exception as e:
            return CodeReviewResult(
                success=False,
                decision=ReviewDecision.BLOCK,
                error=str(e),
            )

    async def review_pull_request(
        self,
        issue_key: str,
        code_files: List[Tuple[str, str]],
    ) -> CodeReviewResult:
        """Review a pull request based on provided file contents.

        Args:
            issue_key: Jira issue key (for context/logging)
            code_files: List of (file_path, content) tuples

        Returns:
            CodeReviewResult
        """
        code_changes: Dict[str, str] = {}

        for file_path, content in code_files:
            if file_path and content is not None:
                code_changes[file_path] = content

        context = {
            "jira_issue_key": issue_key,
            "code_changes": code_changes,
        }

        return self.execute(context)
    
    def _review_file(self, file_path: str, content: str) -> List[ReviewIssue]:
        """Review a single file."""
        issues = []
        
        if not file_path.endswith(".py"):
            return issues
        
        lines = content.split("\n")
        
        for rule_name, rule in ArchitectureRules.RULES.items():
            for i, line in enumerate(lines, 1):
                if re.search(rule.get("pattern", ""), line):
                    issues.append(ReviewIssue(
                        severity="error",
                        category="architecture",
                        message=rule["message"],
                        line_number=i,
                        file_path=file_path,
                    ))
        
        issues.extend(self._check_standards(file_path, lines))
        issues.extend(self._check_edge_cases(file_path, content))
        
        return issues
    
    def _check_standards(self, file_path: str, lines: List[str]) -> List[ReviewIssue]:
        """Check coding standards."""
        issues = []
        
        for i, line in enumerate(lines, 1):
            if len(line) > CodingStandards.MAX_LINE_LENGTH:
                issues.append(ReviewIssue(
                    severity="warning",
                    category="standards",
                    message=f"Line too long ({len(line)} > {CodingStandards.MAX_LINE_LENGTH})",
                    line_number=i,
                    file_path=file_path,
                ))
            
            if re.search(r"except\s*:", line):
                issues.append(ReviewIssue(
                    severity="error",
                    category="standards",
                    message="Bare 'except:' not allowed; specify exception type",
                    line_number=i,
                    file_path=file_path,
                ))
            
            if re.search(r"from\s+\w+\s+import\s+\*", line):
                issues.append(ReviewIssue(
                    severity="error",
                    category="standards",
                    message="Wildcard imports not allowed",
                    line_number=i,
                    file_path=file_path,
                ))
        
        return issues
    
    def _check_edge_cases(self, file_path: str, content: str) -> List[ReviewIssue]:
        """Check for edge cases."""
        issues = []
        
        if re.search(r"\[\d+\]|\[0\]|\[-1\]", content):
            issues.append(ReviewIssue(
                severity="warning",
                category="edge_case",
                message="Direct array/list indexing detected; verify bounds",
                file_path=file_path,
            ))
        
        return issues
    
    def _make_decision(
        self,
        arch_violations: List[str],
        standard_violations: List[str],
    ) -> ReviewDecision:
        """Determine review decision."""
        if arch_violations:
            return ReviewDecision.BLOCK
        if standard_violations:
            return ReviewDecision.REQUEST_CHANGES
        return ReviewDecision.APPROVE
    
    def _generate_reasoning(
        self,
        decision: ReviewDecision,
        arch_violations: List[str],
        standard_violations: List[str],
        edge_cases: List[str],
    ) -> str:
        """Generate reasoning."""
        if decision == ReviewDecision.BLOCK:
            reasons = arch_violations[:3]
            return f"BLOCK: Code violates architecture rules. Issues: {'; '.join(reasons)}"
        elif decision == ReviewDecision.REQUEST_CHANGES:
            reasons = standard_violations[:3]
            return f"REQUEST_CHANGES: Code has standards violations. Issues: {'; '.join(reasons)}"
        else:
            if edge_cases:
                return f"APPROVE: Code meets requirements. Note: {len(edge_cases)} edge case(s) to verify."
            return "APPROVE: Code review passed. Ready for testing."

