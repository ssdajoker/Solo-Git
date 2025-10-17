"""
Test failure analyzer for intelligent diagnosis.

Analyzes test results to identify patterns, root causes, and suggest fixes.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum

from sologit.engines.test_orchestrator import TestResult, TestStatus
from sologit.utils.logger import get_logger

logger = get_logger(__name__)


class FailureCategory(Enum):
    """Categories of test failures."""
    ASSERTION_ERROR = "assertion_error"
    IMPORT_ERROR = "import_error"
    SYNTAX_ERROR = "syntax_error"
    TIMEOUT = "timeout"
    DEPENDENCY_ERROR = "dependency_error"
    NETWORK_ERROR = "network_error"
    PERMISSION_ERROR = "permission_error"
    RESOURCE_ERROR = "resource_error"
    UNKNOWN = "unknown"


@dataclass
class FailurePattern:
    """Pattern identified in test failure."""
    category: FailureCategory
    message: str
    file: Optional[str] = None
    line: Optional[int] = None
    count: int = 1


@dataclass
class TestAnalysis:
    """Analysis of test results."""
    total_tests: int
    passed: int
    failed: int
    timeout: int
    error: int
    status: str
    failure_patterns: List[FailurePattern] = field(default_factory=list)
    suggested_actions: List[str] = field(default_factory=list)
    estimated_fix_complexity: str = "low"  # low, medium, high


class TestAnalyzer:
    """
    Analyzes test results to identify failure patterns and suggest fixes.
    """
    
    # Patterns for different error types
    ERROR_PATTERNS = {
        FailureCategory.ASSERTION_ERROR: [
            r"AssertionError",
            r"assert .+ == .+",
            r"Expected .+ but got .+",
            r"Test failed"
        ],
        FailureCategory.IMPORT_ERROR: [
            r"ImportError",
            r"ModuleNotFoundError",
            r"cannot import name",
            r"No module named"
        ],
        FailureCategory.SYNTAX_ERROR: [
            r"SyntaxError",
            r"invalid syntax",
            r"unexpected EOF",
            r"IndentationError"
        ],
        FailureCategory.DEPENDENCY_ERROR: [
            r"DependencyError",
            r"requires .+ to be installed",
            r"pip install",
            r"missing dependency"
        ],
        FailureCategory.NETWORK_ERROR: [
            r"ConnectionError",
            r"TimeoutError",
            r"Connection refused",
            r"Network is unreachable"
        ],
        FailureCategory.PERMISSION_ERROR: [
            r"PermissionError",
            r"Permission denied",
            r"Access denied",
            r"Operation not permitted"
        ],
        FailureCategory.RESOURCE_ERROR: [
            r"MemoryError",
            r"Out of memory",
            r"Disk full",
            r"No space left"
        ]
    }
    
    def __init__(self):
        """Initialize analyzer."""
        logger.info("TestAnalyzer initialized")
    
    def analyze(self, results: List[TestResult]) -> TestAnalysis:
        """
        Analyze test results and provide insights.
        
        Args:
            results: List of test results to analyze
            
        Returns:
            Test analysis with patterns and suggestions
        """
        logger.info(f"Analyzing {len(results)} test results")
        
        # Count statuses
        passed = sum(1 for r in results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in results if r.status == TestStatus.FAILED)
        timeout = sum(1 for r in results if r.status == TestStatus.TIMEOUT)
        error = sum(1 for r in results if r.status == TestStatus.ERROR)
        
        # Overall status
        status = "green" if failed == 0 and timeout == 0 and error == 0 else "red"
        
        # Analyze failures
        failures = [r for r in results if r.status != TestStatus.PASSED]
        patterns = self._identify_patterns(failures)
        actions = self._suggest_actions(patterns, failures)
        complexity = self._estimate_complexity(patterns)
        
        analysis = TestAnalysis(
            total_tests=len(results),
            passed=passed,
            failed=failed,
            timeout=timeout,
            error=error,
            status=status,
            failure_patterns=patterns,
            suggested_actions=actions,
            estimated_fix_complexity=complexity
        )
        
        logger.info(f"Analysis complete: {status}, {len(patterns)} patterns, {len(actions)} suggestions")
        
        return analysis
    
    def _identify_patterns(self, failures: List[TestResult]) -> List[FailurePattern]:
        """Identify patterns in test failures."""
        patterns = []
        
        for result in failures:
            # Handle timeouts specially
            if result.status == TestStatus.TIMEOUT:
                patterns.append(FailurePattern(
                    category=FailureCategory.TIMEOUT,
                    message=f"Test '{result.name}' timed out",
                    count=1
                ))
                continue
            
            # Analyze output for error patterns
            output = result.stdout + result.stderr
            if result.error:
                output += result.error
            
            # Try to categorize
            category = self._categorize_failure(output)
            
            # Extract error message
            error_msg = self._extract_error_message(output)
            
            # Extract file and line if available
            file_info = self._extract_file_location(output)
            
            pattern = FailurePattern(
                category=category,
                message=error_msg or f"Test '{result.name}' failed",
                file=file_info.get('file'),
                line=file_info.get('line'),
                count=1
            )
            
            patterns.append(pattern)
        
        # Merge similar patterns
        merged = self._merge_patterns(patterns)
        
        return merged
    
    def _categorize_failure(self, output: str) -> FailureCategory:
        """Categorize failure based on output."""
        for category, patterns in self.ERROR_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, output, re.IGNORECASE):
                    return category
        
        return FailureCategory.UNKNOWN
    
    def _extract_error_message(self, output: str) -> Optional[str]:
        """Extract the main error message from output."""
        # Try common error message patterns
        patterns = [
            r"Error: (.+)",
            r"Exception: (.+)",
            r"AssertionError: (.+)",
            r"FAILED (.+)",
            r"(.+Error:.+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, output, re.MULTILINE)
            if match:
                return match.group(1).strip()[:200]  # Truncate long messages
        
        # Return first non-empty line if no pattern matches
        lines = [line.strip() for line in output.split('\n') if line.strip()]
        if lines:
            return lines[0][:200]
        
        return None
    
    def _extract_file_location(self, output: str) -> Dict[str, Optional[str]]:
        """Extract file and line number from output."""
        # Common patterns: "file.py:123", "File 'file.py', line 123"
        patterns = [
            r'File "([^"]+)", line (\d+)',
            r'(\w+\.py):(\d+)',
            r'at ([^:]+):(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, output)
            if match:
                return {
                    'file': match.group(1),
                    'line': int(match.group(2))
                }
        
        return {'file': None, 'line': None}
    
    def _merge_patterns(self, patterns: List[FailurePattern]) -> List[FailurePattern]:
        """Merge similar patterns and count occurrences."""
        merged = {}
        
        for pattern in patterns:
            # Create a key based on category and message (first 100 chars)
            key = (pattern.category, pattern.message[:100])
            
            if key in merged:
                merged[key].count += 1
            else:
                merged[key] = pattern
        
        # Sort by count (descending)
        result = sorted(merged.values(), key=lambda p: p.count, reverse=True)
        
        return result
    
    def _suggest_actions(
        self, 
        patterns: List[FailurePattern],
        failures: List[TestResult]
    ) -> List[str]:
        """Suggest actions based on failure patterns."""
        actions = []
        
        # No failures - no suggestions needed
        if not patterns:
            return actions
        
        # Category-specific suggestions
        categories = {p.category for p in patterns}
        
        if FailureCategory.IMPORT_ERROR in categories:
            actions.append("📦 Check missing dependencies - run 'pip install' for required packages")
            actions.append("🔍 Verify import paths and module names")
        
        if FailureCategory.SYNTAX_ERROR in categories:
            actions.append("✏️ Fix syntax errors in the code")
            actions.append("🔍 Run linter to catch syntax issues")
        
        if FailureCategory.ASSERTION_ERROR in categories:
            actions.append("🧪 Review test assertions and expected values")
            actions.append("🐛 Debug the failing test to understand the mismatch")
        
        if FailureCategory.TIMEOUT in categories:
            actions.append("⏱️ Optimize slow code or increase timeout limits")
            actions.append("🔍 Check for infinite loops or blocking operations")
        
        if FailureCategory.DEPENDENCY_ERROR in categories:
            actions.append("📦 Install missing dependencies")
            actions.append("🔧 Update dependency versions if needed")
        
        if FailureCategory.NETWORK_ERROR in categories:
            actions.append("🌐 Check network connectivity")
            actions.append("🔌 Verify service endpoints and configurations")
        
        if FailureCategory.PERMISSION_ERROR in categories:
            actions.append("🔐 Check file permissions")
            actions.append("👤 Verify user has necessary access rights")
        
        if FailureCategory.RESOURCE_ERROR in categories:
            actions.append("💾 Free up disk space or memory")
            actions.append("⚡ Optimize resource usage in tests")
        
        # Generic suggestions if patterns identified
        if patterns:
            actions.append("🔄 Review recent changes that may have introduced the issue")
            actions.append("📝 Check test logs for detailed error messages")
        
        # Multiple failures
        if len(failures) > 3:
            actions.append("⚠️ Multiple tests failing - may indicate a systemic issue")
            actions.append("🔍 Look for common dependencies or configurations")
        
        return actions
    
    def _estimate_complexity(self, patterns: List[FailurePattern]) -> str:
        """Estimate fix complexity based on failure patterns."""
        if not patterns:
            return "low"
        
        # Count by category
        category_counts = {}
        for pattern in patterns:
            category = pattern.category
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # High complexity indicators
        high_complexity = [
            FailureCategory.UNKNOWN,
            FailureCategory.RESOURCE_ERROR,
            FailureCategory.NETWORK_ERROR
        ]
        
        # Medium complexity
        medium_complexity = [
            FailureCategory.DEPENDENCY_ERROR,
            FailureCategory.PERMISSION_ERROR,
            FailureCategory.TIMEOUT
        ]
        
        # Check for high complexity issues
        if any(cat in category_counts for cat in high_complexity):
            return "high"
        
        # Check for medium complexity issues
        if any(cat in category_counts for cat in medium_complexity):
            return "medium"
        
        # Multiple different categories
        if len(category_counts) > 2:
            return "medium"
        
        # Many failures
        total_failures = sum(category_counts.values())
        if total_failures > 5:
            return "medium"
        
        return "low"
    
    def format_analysis(self, analysis: TestAnalysis) -> str:
        """Format analysis for display."""
        lines = []
        
        # Header
        lines.append("=" * 60)
        lines.append("TEST ANALYSIS REPORT")
        lines.append("=" * 60)
        lines.append("")
        
        # Summary
        status_icon = "✅" if analysis.status == "green" else "❌"
        lines.append(f"{status_icon} Overall Status: {analysis.status.upper()}")
        lines.append(f"   Total Tests: {analysis.total_tests}")
        lines.append(f"   Passed: {analysis.passed}")
        lines.append(f"   Failed: {analysis.failed}")
        if analysis.timeout > 0:
            lines.append(f"   Timeout: {analysis.timeout}")
        if analysis.error > 0:
            lines.append(f"   Error: {analysis.error}")
        lines.append("")
        
        # Failure patterns
        if analysis.failure_patterns:
            lines.append("📊 Failure Patterns:")
            for i, pattern in enumerate(analysis.failure_patterns, 1):
                lines.append(f"   {i}. {pattern.category.value.upper()}")
                lines.append(f"      Message: {pattern.message}")
                if pattern.file:
                    location = f"{pattern.file}"
                    if pattern.line:
                        location += f":{pattern.line}"
                    lines.append(f"      Location: {location}")
                if pattern.count > 1:
                    lines.append(f"      Count: {pattern.count} occurrences")
            lines.append("")
        
        # Suggested actions
        if analysis.suggested_actions:
            lines.append("💡 Suggested Actions:")
            for action in analysis.suggested_actions:
                lines.append(f"   • {action}")
            lines.append("")
        
        # Fix complexity
        complexity_icons = {
            "low": "🟢",
            "medium": "🟡",
            "high": "🔴"
        }
        icon = complexity_icons.get(analysis.estimated_fix_complexity, "⚪")
        lines.append(f"{icon} Estimated Fix Complexity: {analysis.estimated_fix_complexity.upper()}")
        lines.append("")
        lines.append("=" * 60)
        
        return "\n".join(lines)
