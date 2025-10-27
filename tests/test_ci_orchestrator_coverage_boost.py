"""
Additional tests for ci_orchestrator.py to boost coverage to >90%.

These tests target specific uncovered lines identified in coverage analysis.
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch
from sologit.workflows.ci_orchestrator import (
    CIOrchestrator, CIResult, CIStatus
)
from sologit.engines.test_orchestrator import TestConfig, TestResult, TestStatus
from sologit.core.repository import Repository
from sologit.core.workpad import Workpad


@pytest.fixture
def mock_git_engine():
    """Create a mock git engine."""
    engine = Mock()
    engine.get_repo = Mock()
    engine.create_workpad = Mock()
    engine.delete_workpad = Mock()
    return engine


@pytest.fixture
def mock_test_orchestrator():
    """Create a mock test orchestrator."""
    orchestrator = Mock()
    orchestrator.run_tests_sync = Mock()
    return orchestrator


@pytest.fixture
def ci_orchestrator(mock_git_engine, mock_test_orchestrator):
    """Create CI orchestrator with mocks."""
    return CIOrchestrator(mock_git_engine, mock_test_orchestrator)


@pytest.fixture
def sample_smoke_tests():
    """Sample smoke test configs."""
    return [
        TestConfig(
            name="smoke_test_1",
            cmd="pytest tests/smoke1.py",
            timeout=30
        ),
        TestConfig(
            name="smoke_test_2",
            cmd="pytest tests/smoke2.py",
            timeout=30
        )
    ]


class TestCIOrchestratorCoverageMissing:
    """Tests targeting specific uncovered lines."""
    
    def test_run_smoke_tests_with_progress_callback(
        self, 
        ci_orchestrator, 
        mock_git_engine, 
        mock_test_orchestrator,
        sample_smoke_tests
    ):
        """Test smoke tests with progress callback (lines 100, 122, 153)."""
        # Mock repository
        repo = Repository("repo1", "/path/to/repo", "test-repo")
        mock_git_engine.get_repo.return_value = repo
        
        # Mock workpad
        temp_pad = Workpad("repo1", "pad1", "ci-smoke-abc", "pads/pad1", "main")
        mock_git_engine.create_workpad.return_value = temp_pad
        
        # Mock successful test results
        mock_test_orchestrator.run_tests_sync.return_value = [
            TestResult("test1", TestStatus.PASSED, 100, 0, "OK", ""),
            TestResult("test2", TestStatus.PASSED, 150, 0, "OK", "")
        ]
        
        # Progress callback to capture messages
        progress_messages = []
        def progress_callback(msg):
            progress_messages.append(msg)
        
        result = ci_orchestrator.run_smoke_tests(
            "repo1",
            "abc1234567890",
            sample_smoke_tests,
            on_progress=progress_callback
        )
        
        # Verify result
        assert result.status == CIStatus.SUCCESS
        
        # Verify progress callback was called (lines 100, 122, 153)
        assert len(progress_messages) >= 3
        assert any("Starting smoke tests" in msg for msg in progress_messages)
        assert any("Running" in msg and "smoke tests" in msg for msg in progress_messages)
        assert any("Smoke tests complete" in msg for msg in progress_messages)
    
    def test_run_smoke_tests_cleanup_failure(
        self,
        ci_orchestrator,
        mock_git_engine,
        mock_test_orchestrator,
        sample_smoke_tests
    ):
        """Test cleanup failure handling (lines 168-169)."""
        # Mock repository
        repo = Repository("repo1", "/path/to/repo", "test-repo")
        mock_git_engine.get_repo.return_value = repo
        
        # Mock workpad
        temp_pad = Workpad("repo1", "pad1", "ci-smoke-abc", "pads/pad1", "main")
        mock_git_engine.create_workpad.return_value = temp_pad
        
        # Mock successful test results
        mock_test_orchestrator.run_tests_sync.return_value = [
            TestResult("test1", TestStatus.PASSED, 100, 0, "OK", "")
        ]
        
        # Make delete_workpad raise an exception
        mock_git_engine.delete_workpad.side_effect = Exception("Cleanup failed")
        
        # Should not raise exception due to try/except in finally block
        result = ci_orchestrator.run_smoke_tests(
            "repo1",
            "abc1234567890",
            sample_smoke_tests
        )
        
        # Should still succeed despite cleanup failure
        assert result.status == CIStatus.SUCCESS
    
    def test_run_smoke_tests_with_failure_and_progress(
        self,
        ci_orchestrator,
        mock_git_engine,
        mock_test_orchestrator,
        sample_smoke_tests
    ):
        """Test smoke tests exception with progress callback (lines 175-176)."""
        # Mock repository
        repo = Repository("repo1", "/path/to/repo", "test-repo")
        mock_git_engine.get_repo.return_value = repo
        
        # Make create_workpad raise an exception
        mock_git_engine.create_workpad.side_effect = Exception(
            "Sandbox provisioning is forbidden in this project"
        )
        
        # Progress callback
        progress_messages = []
        def progress_callback(msg):
            progress_messages.append(msg)
        
        result = ci_orchestrator.run_smoke_tests(
            "repo1",
            "abc1234567890",
            sample_smoke_tests,
            on_progress=progress_callback
        )
        
        # Should fail
        assert result.status == CIStatus.FAILURE
        assert "Sandbox provisioning is forbidden" in result.message
        
        # Should have failure progress message (line 176)
        assert any("failed" in msg.lower() for msg in progress_messages)
    
    @pytest.mark.asyncio
    async def test_run_smoke_tests_async(
        self,
        ci_orchestrator,
        mock_git_engine,
        mock_test_orchestrator,
        sample_smoke_tests
    ):
        """Test async smoke test execution (lines 207-216)."""
        # Mock repository
        repo = Repository("repo1", "/path/to/repo", "test-repo")
        mock_git_engine.get_repo.return_value = repo
        
        # Mock workpad
        temp_pad = Workpad("repo1", "pad1", "ci-smoke-abc", "pads/pad1", "main")
        mock_git_engine.create_workpad.return_value = temp_pad
        
        # Mock successful test results
        mock_test_orchestrator.run_tests_sync.return_value = [
            TestResult("test1", TestStatus.PASSED, 100, 0, "OK", "")
        ]
        
        # Run async
        result = await ci_orchestrator.run_smoke_tests_async(
            "repo1",
            "abc1234567890",
            sample_smoke_tests
        )
        
        # Verify result
        assert result.status == CIStatus.SUCCESS
        assert result.repo_id == "repo1"
    
    def test_format_result_unstable_status(self, ci_orchestrator):
        """Test formatting result with UNSTABLE status (lines 232-233)."""
        result = CIResult(
            repo_id="repo1",
            commit_hash="abc123",
            status=CIStatus.UNSTABLE,
            duration_ms=1500,
            test_results=[
                TestResult("test1", TestStatus.PASSED, 100, 0, "OK", ""),
                TestResult("test2", TestStatus.TIMEOUT, 1000, -1, "", "")
            ],
            message="Some tests timed out"
        )
        
        formatted = ci_orchestrator.format_result(result)
        
        # Should show unstable
        assert "UNSTABLE" in formatted
        assert "Some tests timed out" in formatted
    
    def test_format_result_other_status(self, ci_orchestrator):
        """Test formatting result with other status (lines 234-235)."""
        result = CIResult(
            repo_id="repo1",
            commit_hash="abc123",
            status=CIStatus.PENDING,  # Not SUCCESS, FAILURE, or UNSTABLE
            duration_ms=0,
            test_results=[],
            message="Waiting to run"
        )
        
        formatted = ci_orchestrator.format_result(result)
        
        # Should show the status name (line 235)
        assert "PENDING" in formatted
        assert "Waiting to run" in formatted
    
    def test_format_result_with_timeout_tests(self, ci_orchestrator):
        """Test formatting result with timeout tests (lines 256-257)."""
        result = CIResult(
            repo_id="repo1",
            commit_hash="abc123",
            status=CIStatus.UNSTABLE,
            duration_ms=2000,
            test_results=[
                TestResult("test1", TestStatus.PASSED, 100, 0, "OK", ""),
                TestResult("test2", TestStatus.TIMEOUT, 1000, -1, "", ""),
                TestResult("test3", TestStatus.TIMEOUT, 1000, -1, "", "")
            ],
            message="Some tests timed out"
        )
        
        formatted = ci_orchestrator.format_result(result)
        
        # Should show timeout count (lines 256-257)
        assert "Timeout: 2" in formatted or "⏱️" in formatted
    
    def test_run_smoke_tests_with_mixed_results(
        self,
        ci_orchestrator,
        mock_git_engine,
        mock_test_orchestrator,
        sample_smoke_tests
    ):
        """Test smoke tests with mixed results."""
        # Mock repository
        repo = Repository("repo1", "/path/to/repo", "test-repo")
        mock_git_engine.get_repo.return_value = repo
        
        # Mock workpad
        temp_pad = Workpad("repo1", "pad1", "ci-smoke-abc", "pads/pad1", "main")
        mock_git_engine.create_workpad.return_value = temp_pad
        
        # Mock mixed test results (some passed, some failed)
        mock_test_orchestrator.run_tests_sync.return_value = [
            TestResult("test1", TestStatus.PASSED, 100, 0, "OK", ""),
            TestResult("test2", TestStatus.FAILED, 150, 1, "Failed", ""),
            TestResult("test3", TestStatus.PASSED, 120, 0, "OK", "")
        ]
        
        result = ci_orchestrator.run_smoke_tests(
            "repo1",
            "abc1234567890",
            sample_smoke_tests
        )
        
        # Should be failure
        assert result.status == CIStatus.FAILURE
        assert "1 tests failed" in result.message
    
    def test_run_smoke_tests_with_timeout_results(
        self,
        ci_orchestrator,
        mock_git_engine,
        mock_test_orchestrator,
        sample_smoke_tests
    ):
        """Test smoke tests with timeout results."""
        # Mock repository
        repo = Repository("repo1", "/path/to/repo", "test-repo")
        mock_git_engine.get_repo.return_value = repo
        
        # Mock workpad
        temp_pad = Workpad("repo1", "pad1", "ci-smoke-abc", "pads/pad1", "main")
        mock_git_engine.create_workpad.return_value = temp_pad
        
        # Mock timeout test results
        mock_test_orchestrator.run_tests_sync.return_value = [
            TestResult("test1", TestStatus.PASSED, 100, 0, "OK", ""),
            TestResult("test2", TestStatus.TIMEOUT, 1000, -1, "", "")
        ]
        
        result = ci_orchestrator.run_smoke_tests(
            "repo1",
            "abc1234567890",
            sample_smoke_tests
        )
        
        # Should be unstable due to timeout
        assert result.status == CIStatus.UNSTABLE
        assert "timed out" in result.message.lower()
    
    def test_ci_result_properties(self):
        """Test CI result property methods."""
        # Test is_green
        success_result = CIResult(
            repo_id="repo1",
            commit_hash="abc123",
            status=CIStatus.SUCCESS,
            duration_ms=1000,
            test_results=[]
        )
        assert success_result.is_green is True
        assert success_result.is_red is False
        
        # Test is_red with FAILURE
        failure_result = CIResult(
            repo_id="repo1",
            commit_hash="abc123",
            status=CIStatus.FAILURE,
            duration_ms=1000,
            test_results=[]
        )
        assert failure_result.is_green is False
        assert failure_result.is_red is True
        
        # Test is_red with UNSTABLE
        unstable_result = CIResult(
            repo_id="repo1",
            commit_hash="abc123",
            status=CIStatus.UNSTABLE,
            duration_ms=1000,
            test_results=[]
        )
        assert unstable_result.is_green is False
        assert unstable_result.is_red is True
