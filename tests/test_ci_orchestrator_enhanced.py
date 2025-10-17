
"""
Enhanced tests for CI orchestrator to achieve >90% coverage.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from sologit.workflows.ci_orchestrator import CIOrchestrator, CIResult, CIStatus
from sologit.engines.git_engine import GitEngine, GitEngineError
from sologit.engines.test_orchestrator import TestOrchestrator, TestConfig, TestResult, TestStatus
from sologit.core.repository import Repository


class TestCIOrchestratorEnhanced:
    """Enhanced tests for CIOrchestrator."""
    
    @pytest.fixture
    def git_engine(self):
        """Mock git engine."""
        return Mock(spec=GitEngine)
    
    @pytest.fixture
    def test_orchestrator(self):
        """Mock test orchestrator."""
        return Mock(spec=TestOrchestrator)
    
    @pytest.fixture
    def orchestrator(self, git_engine, test_orchestrator):
        """Create orchestrator instance."""
        return CIOrchestrator(git_engine, test_orchestrator)
    
    @pytest.fixture
    def smoke_tests(self):
        """Create smoke test configurations."""
        return [
            TestConfig(name="smoke_test_1", cmd="pytest tests/smoke/test_1.py", timeout=30),
            TestConfig(name="smoke_test_2", cmd="pytest tests/smoke/test_2.py", timeout=30)
        ]
    
    def test_run_smoke_tests_repo_not_found(self, orchestrator, git_engine, smoke_tests):
        """Test running smoke tests when repository doesn't exist."""
        # Mock git engine to return None (repo not found)
        git_engine.get_repo = Mock(return_value=None)
        
        # Run smoke tests
        result = orchestrator.run_smoke_tests("nonexistent-repo", "abc123", smoke_tests)
        
        # Verify
        assert result.status == CIStatus.FAILURE
        assert "not found" in result.message.lower()
        assert len(result.test_results) == 0
    
    def test_run_smoke_tests_get_history_fails(self, orchestrator, git_engine, test_orchestrator, smoke_tests):
        """Test running smoke tests when get_history fails."""
        # Mock git engine
        mock_repo = Mock(spec=Repository)
        mock_repo.id = "test-repo"
        git_engine.get_repo = Mock(return_value=mock_repo)
        git_engine.get_history = Mock(side_effect=GitEngineError("History unavailable"))
        
        # Run smoke tests
        result = orchestrator.run_smoke_tests("test-repo", "abc123", smoke_tests)
        
        # Verify
        assert result.status == CIStatus.FAILURE
        assert "History unavailable" in result.message
    
    def test_run_smoke_tests_no_commits(self, orchestrator, git_engine, test_orchestrator, smoke_tests):
        """Test running smoke tests when repo has no commits."""
        # Mock git engine
        mock_repo = Mock(spec=Repository)
        mock_repo.id = "test-repo"
        git_engine.get_repo = Mock(return_value=mock_repo)
        git_engine.get_history = Mock(return_value=[])  # No commits
        
        # Run smoke tests
        result = orchestrator.run_smoke_tests("test-repo", "abc123", smoke_tests)
        
        # Verify
        assert result.status == CIStatus.FAILURE
        assert "no commits" in result.message.lower()
    
    def test_run_smoke_tests_orchestrator_exception(self, orchestrator, git_engine, test_orchestrator, smoke_tests):
        """Test running smoke tests when test orchestrator raises exception."""
        # Mock git engine
        mock_repo = Mock(spec=Repository)
        mock_repo.id = "test-repo"
        git_engine.get_repo = Mock(return_value=mock_repo)
        git_engine.get_history = Mock(return_value=[{"hash": "abc123", "message": "Test"}])
        
        # Mock test orchestrator to raise exception
        test_orchestrator.run_tests_sync = Mock(side_effect=Exception("Test orchestrator crashed"))
        
        # Run smoke tests
        result = orchestrator.run_smoke_tests("test-repo", "abc123", smoke_tests)
        
        # Verify
        assert result.status == CIStatus.FAILURE
        assert "Test orchestrator crashed" in result.message
    
    def test_run_smoke_tests_with_failures(self, orchestrator, git_engine, test_orchestrator, smoke_tests):
        """Test running smoke tests with some failures."""
        # Mock git engine
        mock_repo = Mock(spec=Repository)
        mock_repo.id = "test-repo"
        git_engine.get_repo = Mock(return_value=mock_repo)
        git_engine.get_history = Mock(return_value=[{"hash": "abc123", "message": "Test"}])
        
        # Mock test orchestrator with mixed results
        test_results = [
            TestResult(
                name="smoke_test_1",
                status=TestStatus.PASSED,
                duration_ms=100,
                exit_code=0,
                stdout="",
                stderr=""
            ),
            TestResult(
                name="smoke_test_2",
                status=TestStatus.FAILED,
                duration_ms=200,
                exit_code=1,
                stdout="",
                stderr="Test failed",
                error="AssertionError"
            )
        ]
        test_orchestrator.run_tests_sync = Mock(return_value=test_results)
        
        # Run smoke tests
        result = orchestrator.run_smoke_tests("test-repo", "abc123", smoke_tests)
        
        # Verify
        assert result.status == CIStatus.FAILURE
        assert len(result.test_results) == 2
        assert "1/2 passed" in result.message or "failed" in result.message.lower()
    
    def test_format_ci_result_with_empty_tests(self, orchestrator):
        """Test formatting CI result with no test results."""
        result = CIResult(
            repo_id="test-repo",
            commit_hash="abc123",
            status=CIStatus.SUCCESS,
            duration_ms=1000,
            test_results=[],
            message="No tests to run"
        )
        
        formatted = orchestrator.format_result(result)
        
        # Verify
        assert "CI SMOKE TESTS" in formatted
        assert "test-repo" in formatted
        assert "abc123" in formatted
    
    def test_format_ci_result_with_long_commit_hash(self, orchestrator):
        """Test formatting CI result with very long commit hash."""
        result = CIResult(
            repo_id="test-repo",
            commit_hash="a" * 100,
            status=CIStatus.SUCCESS,
            duration_ms=1000,
            test_results=[]
        )
        
        formatted = orchestrator.format_result(result)
        
        # Verify formatting handles long hash
        assert "CI SMOKE TESTS" in formatted
    
    def test_ci_status_enum_values(self):
        """Test CIStatus enum has expected values."""
        assert CIStatus.PENDING.value == "pending"
        assert CIStatus.RUNNING.value == "running"
        assert CIStatus.SUCCESS.value == "success"
        assert CIStatus.FAILURE.value == "failure"
        assert CIStatus.UNSTABLE.value == "unstable"
        assert CIStatus.ABORTED.value == "aborted"


class TestCIResultProperties:
    """Tests for CIResult properties."""
    
    def test_is_green_with_success(self):
        """Test is_green property with successful status."""
        result = CIResult(
            repo_id="test",
            commit_hash="abc",
            status=CIStatus.SUCCESS,
            duration_ms=1000,
            test_results=[]
        )
        
        assert result.is_green
        assert not result.is_red
    
    def test_is_red_with_failure(self):
        """Test is_red property with failure status."""
        result = CIResult(
            repo_id="test",
            commit_hash="abc",
            status=CIStatus.FAILURE,
            duration_ms=1000,
            test_results=[]
        )
        
        assert result.is_red
        assert not result.is_green
    
    def test_is_red_with_unstable(self):
        """Test is_red property with unstable status."""
        result = CIResult(
            repo_id="test",
            commit_hash="abc",
            status=CIStatus.UNSTABLE,
            duration_ms=1000,
            test_results=[]
        )
        
        assert result.is_red
        assert not result.is_green
    
    def test_neither_green_nor_red_with_pending(self):
        """Test that PENDING is neither green nor red."""
        result = CIResult(
            repo_id="test",
            commit_hash="abc",
            status=CIStatus.PENDING,
            duration_ms=0,
            test_results=[]
        )
        
        assert not result.is_green
        assert not result.is_red
