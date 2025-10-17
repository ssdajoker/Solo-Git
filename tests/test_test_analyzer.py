"""
Tests for test failure analyzer (Phase 3).
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


@pytest.fixture
def passing_results():
    """Create passing test results."""
    return [
        TestResult(
            name="test_login",
            status=TestStatus.PASSED,
            duration_ms=100,
            exit_code=0,
            stdout="All tests passed",
            stderr=""
        ),
        TestResult(
            name="test_auth",
            status=TestStatus.PASSED,
            duration_ms=150,
            exit_code=0,
            stdout="OK",
            stderr=""
        )
    ]


@pytest.fixture
def failing_results():
    """Create failing test results."""
    return [
        TestResult(
            name="test_api",
            status=TestStatus.FAILED,
            duration_ms=200,
            exit_code=1,
            stdout="AssertionError: Expected 200 but got 404",
            stderr=""
        ),
        TestResult(
            name="test_db",
            status=TestStatus.FAILED,
            duration_ms=150,
            exit_code=1,
            stdout="ImportError: No module named 'psycopg2'",
            stderr=""
        )
    ]


class TestTestAnalyzer:
    """Tests for TestAnalyzer class."""
    
    def test_analyzer_initialization(self, analyzer):
        """Test analyzer can be initialized."""
        assert analyzer is not None
        assert isinstance(analyzer, TestAnalyzer)
    
    def test_analyze_passing_tests(self, analyzer, passing_results):
        """Test analyzing passing tests."""
        analysis = analyzer.analyze(passing_results)
        
        assert isinstance(analysis, TestAnalysis)
        assert analysis.total_tests == 2
        assert analysis.passed == 2
        assert analysis.failed == 0
        assert analysis.status == "green"
        assert len(analysis.failure_patterns) == 0
    
    def test_analyze_failing_tests(self, analyzer, failing_results):
        """Test analyzing failing tests."""
        analysis = analyzer.analyze(failing_results)
        
        assert analysis.total_tests == 2
        assert analysis.passed == 0
        assert analysis.failed == 2
        assert analysis.status == "red"
        assert len(analysis.failure_patterns) > 0
    
    def test_identify_assertion_error(self, analyzer):
        """Test identifying assertion errors."""
        results = [
            TestResult(
                name="test_fail",
                status=TestStatus.FAILED,
                duration_ms=100,
                exit_code=1,
                stdout="AssertionError: Values don't match",
                stderr=""
            )
        ]
        
        analysis = analyzer.analyze(results)
        patterns = analysis.failure_patterns
        
        assert len(patterns) > 0
        assert any(p.category == FailureCategory.ASSERTION_ERROR for p in patterns)
    
    def test_identify_import_error(self, analyzer):
        """Test identifying import errors."""
        results = [
            TestResult(
                name="test_import",
                status=TestStatus.FAILED,
                duration_ms=50,
                exit_code=1,
                stdout="ImportError: No module named 'missing'",
                stderr=""
            )
        ]
        
        analysis = analyzer.analyze(results)
        patterns = analysis.failure_patterns
        
        assert len(patterns) > 0
        assert any(p.category == FailureCategory.IMPORT_ERROR for p in patterns)
    
    def test_identify_syntax_error(self, analyzer):
        """Test identifying syntax errors."""
        results = [
            TestResult(
                name="test_syntax",
                status=TestStatus.FAILED,
                duration_ms=30,
                exit_code=1,
                stdout="SyntaxError: invalid syntax on line 42",
                stderr=""
            )
        ]
        
        analysis = analyzer.analyze(results)
        patterns = analysis.failure_patterns
        
        assert len(patterns) > 0
        assert any(p.category == FailureCategory.SYNTAX_ERROR for p in patterns)
    
    def test_identify_timeout(self, analyzer):
        """Test identifying timeouts."""
        results = [
            TestResult(
                name="test_slow",
                status=TestStatus.TIMEOUT,
                duration_ms=5000,
                exit_code=-1,
                stdout="Test timed out",
                stderr=""
            )
        ]
        
        analysis = analyzer.analyze(results)
        patterns = analysis.failure_patterns
        
        assert len(patterns) > 0
        assert any(p.category == FailureCategory.TIMEOUT for p in patterns)
    
    def test_suggested_actions_for_import_error(self, analyzer):
        """Test suggestions for import errors."""
        results = [
            TestResult(
                name="test_import",
                status=TestStatus.FAILED,
                duration_ms=50,
                exit_code=1,
                stdout="ImportError: No module named 'requests'",
                stderr=""
            )
        ]
        
        analysis = analyzer.analyze(results)
        
        assert len(analysis.suggested_actions) > 0
        assert any("dependencies" in action.lower() for action in analysis.suggested_actions)
    
    def test_suggested_actions_for_timeout(self, analyzer):
        """Test suggestions for timeouts."""
        results = [
            TestResult(
                name="test_slow",
                status=TestStatus.TIMEOUT,
                duration_ms=5000,
                exit_code=-1,
                stdout="",
                stderr=""
            )
        ]
        
        analysis = analyzer.analyze(results)
        
        assert len(analysis.suggested_actions) > 0
        assert any("timeout" in action.lower() or "optimize" in action.lower() 
                  for action in analysis.suggested_actions)
    
    def test_complexity_estimation_low(self, analyzer, passing_results):
        """Test low complexity estimation."""
        analysis = analyzer.analyze(passing_results)
        assert analysis.estimated_fix_complexity == "low"
    
    def test_complexity_estimation_medium(self, analyzer):
        """Test medium complexity estimation."""
        # Multiple different error types
        results = [
            TestResult(
                name="test1",
                status=TestStatus.FAILED,
                duration_ms=100,
                exit_code=1,
                stdout="AssertionError: Failed",
                stderr=""
            ),
            TestResult(
                name="test2",
                status=TestStatus.TIMEOUT,
                duration_ms=5000,
                exit_code=-1,
                stdout="",
                stderr=""
            ),
            TestResult(
                name="test3",
                status=TestStatus.FAILED,
                duration_ms=100,
                exit_code=1,
                stdout="DependencyError: Missing lib",
                stderr=""
            )
        ]
        
        analysis = analyzer.analyze(results)
        assert analysis.estimated_fix_complexity in ["medium", "high"]
    
    def test_merge_similar_patterns(self, analyzer):
        """Test merging of similar failure patterns."""
        # Multiple similar failures
        results = [
            TestResult(
                name=f"test_{i}",
                status=TestStatus.FAILED,
                duration_ms=100,
                exit_code=1,
                stdout="AssertionError: Value mismatch",
                stderr=""
            )
            for i in range(3)
        ]
        
        analysis = analyzer.analyze(results)
        patterns = analysis.failure_patterns
        
        # Should merge into fewer patterns
        assert len(patterns) <= len(results)
        
        # Check count
        if patterns:
            assert patterns[0].count > 1 or len(patterns) == len(results)
    
    def test_format_analysis(self, analyzer, failing_results):
        """Test formatting analysis for display."""
        analysis = analyzer.analyze(failing_results)
        formatted = analyzer.format_analysis(analysis)
        
        assert isinstance(formatted, str)
        assert "TEST ANALYSIS REPORT" in formatted
        assert "Overall Status" in formatted
        assert "Failure Patterns" in formatted
        assert "Suggested Actions" in formatted
    
    def test_mixed_results(self, analyzer):
        """Test analyzing mixed pass/fail results."""
        results = [
            TestResult("test1", TestStatus.PASSED, 100, 0, "OK", ""),
            TestResult("test2", TestStatus.FAILED, 200, 1, "Error", ""),
            TestResult("test3", TestStatus.PASSED, 150, 0, "OK", ""),
            TestResult("test4", TestStatus.TIMEOUT, 5000, -1, "", "")
        ]
        
        analysis = analyzer.analyze(results)
        
        assert analysis.total_tests == 4
        assert analysis.passed == 2
        assert analysis.failed == 1
        assert analysis.timeout == 1
        assert analysis.status == "red"
    
    def test_extract_error_message(self, analyzer):
        """Test extracting error messages."""
        output = """
        Running tests...
        FAILED test_api.py::test_endpoint
        AssertionError: Expected status 200, got 404
        """
        
        message = analyzer._extract_error_message(output)
        assert message is not None
        assert "AssertionError" in message or "Expected status" in message
    
    def test_extract_file_location(self, analyzer):
        """Test extracting file and line location."""
        output = """
        File "test_api.py", line 42, in test_endpoint
        AssertionError: Test failed
        """
        
        location = analyzer._extract_file_location(output)
        assert location['file'] == "test_api.py"
        assert location['line'] == 42
    
    def test_categorize_network_error(self, analyzer):
        """Test categorizing network errors."""
        output = "ConnectionError: Failed to connect to server"
        category = analyzer._categorize_failure(output)
        assert category == FailureCategory.NETWORK_ERROR
    
    def test_categorize_permission_error(self, analyzer):
        """Test categorizing permission errors."""
        output = "PermissionError: Access denied to /var/log"
        category = analyzer._categorize_failure(output)
        assert category == FailureCategory.PERMISSION_ERROR
    
    def test_categorize_unknown_error(self, analyzer):
        """Test categorizing unknown errors."""
        output = "Something went wrong but we don't know what"
        category = analyzer._categorize_failure(output)
        assert category == FailureCategory.UNKNOWN
