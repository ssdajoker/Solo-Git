"""
Additional tests for test_analyzer.py to boost coverage to >90%.

These tests target specific uncovered lines identified in coverage analysis.
"""

import pytest
from sologit.analysis.test_analyzer import (
    TestAnalyzer, TestAnalysis, FailurePattern, FailureCategory
)
from sologit.engines.test_orchestrator import TestResult, TestStatus


@pytest.fixture
def analyzer():
    """Create test analyzer."""
    return TestAnalyzer()


class TestTestAnalyzerCoverageMissing:
    """Tests targeting specific uncovered lines."""
    
    def test_analyze_with_error_field(self, analyzer):
        """Test analyzing results with error field (line 170)."""
        results = [
            TestResult(
                name="test_with_error",
                status=TestStatus.FAILED,
                duration_ms=100,
                exit_code=1,
                stdout="Some output",
                stderr="Some stderr",
                error="ImportError: module not found"  # This exercises line 170
            )
        ]
        
        analysis = analyzer.analyze(results)
        assert analysis.failed == 1
        assert len(analysis.failure_patterns) > 0
        # Should detect import error from the error field
        assert any(p.category == FailureCategory.IMPORT_ERROR for p in analysis.failure_patterns)
    
    def test_extract_error_message_with_empty_output(self, analyzer):
        """Test extracting error message from empty output (line 226)."""
        # Empty output should return None
        message = analyzer._extract_error_message("")
        assert message is None
    
    def test_network_error_suggestions(self, analyzer):
        """Test suggestions for network errors (lines 301-302)."""
        results = [
            TestResult(
                name="test_network",
                status=TestStatus.FAILED,
                duration_ms=100,
                exit_code=1,
                stdout="ConnectionError: Failed to connect",
                stderr=""
            )
        ]
        
        analysis = analyzer.analyze(results)
        
        # Should include network-specific suggestions
        assert any("network" in action.lower() for action in analysis.suggested_actions)
        assert any("service" in action.lower() or "endpoint" in action.lower() 
                  for action in analysis.suggested_actions)
    
    def test_permission_error_suggestions(self, analyzer):
        """Test suggestions for permission errors (lines 305-306)."""
        results = [
            TestResult(
                name="test_permission",
                status=TestStatus.FAILED,
                duration_ms=100,
                exit_code=1,
                stdout="PermissionError: Access denied to file",
                stderr=""
            )
        ]
        
        analysis = analyzer.analyze(results)
        
        # Should include permission-specific suggestions
        assert any("permission" in action.lower() for action in analysis.suggested_actions)
        assert any("access" in action.lower() or "rights" in action.lower() 
                  for action in analysis.suggested_actions)
    
    def test_resource_error_suggestions(self, analyzer):
        """Test suggestions for resource errors (lines 309-310)."""
        results = [
            TestResult(
                name="test_resource",
                status=TestStatus.FAILED,
                duration_ms=100,
                exit_code=1,
                stdout="MemoryError: Out of memory",
                stderr=""
            )
        ]
        
        analysis = analyzer.analyze(results)
        
        # Should include resource-specific suggestions
        assert any("disk" in action.lower() or "memory" in action.lower() 
                  for action in analysis.suggested_actions)
        assert any("resource" in action.lower() or "optimize" in action.lower() 
                  for action in analysis.suggested_actions)
    
    def test_multiple_failures_suggestions(self, analyzer):
        """Test suggestions for multiple failures (lines 319-320)."""
        # Create more than 3 failures to trigger the multiple failures suggestion
        results = [
            TestResult(
                name=f"test_{i}",
                status=TestStatus.FAILED,
                duration_ms=100,
                exit_code=1,
                stdout=f"AssertionError: Test {i} failed",
                stderr=""
            )
            for i in range(5)  # 5 failures > 3
        ]
        
        analysis = analyzer.analyze(results)
        
        # Should include systemic issue suggestions
        assert any("multiple" in action.lower() for action in analysis.suggested_actions)
        assert any("common" in action.lower() or "systemic" in action.lower() 
                  for action in analysis.suggested_actions)
    
    def test_complexity_multiple_categories(self, analyzer):
        """Test complexity estimation with >2 categories (line 359)."""
        # Create failures with 3 different categories
        results = [
            TestResult(
                name="test_assert",
                status=TestStatus.FAILED,
                duration_ms=100,
                exit_code=1,
                stdout="AssertionError: Failed",
                stderr=""
            ),
            TestResult(
                name="test_import",
                status=TestStatus.FAILED,
                duration_ms=100,
                exit_code=1,
                stdout="ImportError: Module not found",
                stderr=""
            ),
            TestResult(
                name="test_syntax",
                status=TestStatus.FAILED,
                duration_ms=100,
                exit_code=1,
                stdout="SyntaxError: invalid syntax",
                stderr=""
            )
        ]
        
        analysis = analyzer.analyze(results)
        
        # With 3 different categories, complexity should be at least medium
        assert analysis.estimated_fix_complexity in ["medium", "high"]
    
    def test_complexity_many_failures(self, analyzer):
        """Test complexity estimation with >5 patterns (line 364)."""
        # Create 7 failures with DIFFERENT messages to create 7 distinct patterns
        results = [
            TestResult(
                name=f"test_{i}",
                status=TestStatus.FAILED,
                duration_ms=100,
                exit_code=1,
                stdout=f"AssertionError: Different error message {i}",  # Different messages
                stderr=""
            )
            for i in range(7)  # 7 distinct patterns > 5
        ]
        
        analysis = analyzer.analyze(results)
        
        # With >5 patterns, complexity should be at least medium
        assert analysis.estimated_fix_complexity in ["medium", "high"]
    
    def test_format_analysis_with_timeout(self, analyzer):
        """Test formatting analysis with timeout (lines 385-387)."""
        results = [
            TestResult(
                name="test_timeout",
                status=TestStatus.TIMEOUT,
                duration_ms=5000,
                exit_code=-1,
                stdout="",
                stderr=""
            ),
            TestResult(
                name="test_error",
                status=TestStatus.ERROR,
                duration_ms=100,
                exit_code=1,
                stdout="Error occurred",
                stderr=""
            )
        ]
        
        analysis = analyzer.analyze(results)
        formatted = analyzer.format_analysis(analysis)
        
        # Should display timeout count
        assert "Timeout:" in formatted
        assert "Error:" in formatted
    
    def test_format_analysis_with_file_location(self, analyzer):
        """Test formatting analysis with file location (lines 397-400)."""
        results = [
            TestResult(
                name="test_with_location",
                status=TestStatus.FAILED,
                duration_ms=100,
                exit_code=1,
                stdout='File "test_file.py", line 42, in test_func\nAssertionError: Failed',
                stderr=""
            )
        ]
        
        analysis = analyzer.analyze(results)
        formatted = analyzer.format_analysis(analysis)
        
        # Should display file location
        assert "Location:" in formatted
        assert "test_file.py" in formatted
        assert "42" in formatted
    
    def test_format_analysis_with_multiple_occurrences(self, analyzer):
        """Test formatting analysis with pattern count (line 402)."""
        # Create multiple identical failures
        results = [
            TestResult(
                name=f"test_{i}",
                status=TestStatus.FAILED,
                duration_ms=100,
                exit_code=1,
                stdout="AssertionError: Same error for all tests",
                stderr=""
            )
            for i in range(3)
        ]
        
        analysis = analyzer.analyze(results)
        formatted = analyzer.format_analysis(analysis)
        
        # Should display occurrence count
        assert "Count:" in formatted or "occurrences" in formatted
    
    def test_dependency_error_categorization(self, analyzer):
        """Test categorization of dependency errors."""
        output = "DependencyError: requires package to be installed"
        category = analyzer._categorize_failure(output)
        assert category == FailureCategory.DEPENDENCY_ERROR
    
    def test_resource_error_categorization(self, analyzer):
        """Test categorization of resource errors."""
        output = "Disk full: No space left on device"
        category = analyzer._categorize_failure(output)
        assert category == FailureCategory.RESOURCE_ERROR
    
    def test_analyze_all_error_statuses(self, analyzer):
        """Test analyzing results with all possible statuses."""
        results = [
            TestResult("test_pass", TestStatus.PASSED, 100, 0, "OK", ""),
            TestResult("test_fail", TestStatus.FAILED, 200, 1, "AssertionError", ""),
            TestResult("test_timeout", TestStatus.TIMEOUT, 5000, -1, "", ""),
            TestResult("test_error", TestStatus.ERROR, 150, 1, "Error", "")
        ]
        
        analysis = analyzer.analyze(results)
        
        assert analysis.total_tests == 4
        assert analysis.passed == 1
        assert analysis.failed == 1
        assert analysis.timeout == 1
        assert analysis.error == 1
        assert analysis.status == "red"
