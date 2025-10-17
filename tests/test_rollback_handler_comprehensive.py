"""
Comprehensive tests for rollback handler to achieve 80%+ coverage.

This test suite covers:
- RollbackHandler.handle_failed_ci with various scenarios
- RollbackHandler.format_result with different result types
- CIMonitor initialization and monitoring
- Edge cases and error conditions
"""

import pytest
from unittest.mock import Mock, MagicMock, patch

from sologit.workflows.rollback_handler import (
    RollbackHandler, 
    RollbackResult, 
    CIMonitor
)
from sologit.workflows.ci_orchestrator import CIResult, CIStatus
from sologit.engines.test_orchestrator import TestResult, TestStatus
from sologit.engines.git_engine import GitEngine, GitEngineError
from sologit.core.repository import Repository
from sologit.core.workpad import Workpad


class TestRollbackHandlerComprehensive:
    """Comprehensive tests for RollbackHandler."""
    
    @pytest.fixture
    def git_engine(self):
        """Mock git engine."""
        return Mock(spec=GitEngine)
    
    @pytest.fixture
    def handler(self, git_engine):
        """Create handler instance."""
        return RollbackHandler(git_engine)
    
    @pytest.fixture
    def failed_ci_result(self):
        """Create a failed CI result."""
        return CIResult(
            repo_id="test-repo",
            commit_hash="abc123def456",
            status=CIStatus.FAILURE,
            duration_ms=5000,
            test_results=[
                TestResult(
                    name="test_feature",
                    status=TestStatus.FAILED,
                    duration_ms=1000,
                    exit_code=1,
                    stdout="",
                    stderr="",
                    error="AssertionError: Expected True, got False"
                )
            ]
        )
    
    @pytest.fixture
    def passed_ci_result(self):
        """Create a passed CI result."""
        return CIResult(
            repo_id="test-repo",
            commit_hash="abc123def456",
            status=CIStatus.SUCCESS,
            duration_ms=2000,
            test_results=[
                TestResult(
                    name="test_feature",
                    status=TestStatus.PASSED,
                    duration_ms=1000,
                    exit_code=0,
                    stdout="",
                    stderr=""
                )
            ]
        )
    
    def test_handle_failed_ci_successful_rollback_no_workpad(self, handler, git_engine, failed_ci_result):
        """Test successful rollback without workpad recreation."""
        # Mock git engine methods
        git_engine.revert_last_commit = Mock()
        
        # Execute rollback without recreating workpad
        result = handler.handle_failed_ci(failed_ci_result, recreate_workpad=False)
        
        # Verify
        assert result.success
        assert result.repo_id == "test-repo"
        assert result.reverted_commit == "abc123def456"
        assert result.new_pad_id is None
        assert "Rolled back commit abc123de" in result.message
        
        # Verify git engine was called
        git_engine.revert_last_commit.assert_called_once_with("test-repo")
    
    def test_handle_failed_ci_successful_rollback_with_workpad(self, handler, git_engine, failed_ci_result):
        """Test successful rollback with workpad recreation."""
        # Mock git engine methods
        git_engine.revert_last_commit = Mock()
        
        mock_repo = Mock(spec=Repository)
        mock_repo.id = "test-repo"
        git_engine.get_repo = Mock(return_value=mock_repo)
        
        mock_workpad = Mock(spec=Workpad)
        mock_workpad.id = "fix-ci-abc123d"
        git_engine.create_workpad = Mock(return_value=mock_workpad)
        
        # Execute rollback with workpad recreation
        result = handler.handle_failed_ci(failed_ci_result, recreate_workpad=True)
        
        # Verify
        assert result.success
        assert result.repo_id == "test-repo"
        assert result.reverted_commit == "abc123def456"
        assert result.new_pad_id == "fix-ci-abc123d"
        assert "Created workpad fix-ci-abc123d" in result.message
        
        # Verify git engine was called correctly
        git_engine.revert_last_commit.assert_called_once_with("test-repo")
        git_engine.get_repo.assert_called_once_with("test-repo")
        git_engine.create_workpad.assert_called_once_with("test-repo", "fix-ci-abc123d")
    
    def test_handle_failed_ci_revert_fails(self, handler, git_engine, failed_ci_result):
        """Test rollback when revert operation fails."""
        # Mock git engine to fail on revert
        git_engine.revert_last_commit = Mock(side_effect=GitEngineError("Cannot revert commit"))
        
        # Execute rollback
        result = handler.handle_failed_ci(failed_ci_result)
        
        # Verify
        assert not result.success
        assert result.repo_id == "test-repo"
        assert result.reverted_commit == "abc123def456"
        assert result.new_pad_id is None
        assert "Rollback failed" in result.message
        assert "Cannot revert commit" in result.message
    
    def test_handle_failed_ci_workpad_creation_fails(self, handler, git_engine, failed_ci_result):
        """Test rollback when workpad creation fails."""
        # Mock git engine methods - revert succeeds but workpad creation fails
        git_engine.revert_last_commit = Mock()
        
        mock_repo = Mock(spec=Repository)
        mock_repo.id = "test-repo"
        git_engine.get_repo = Mock(return_value=mock_repo)
        
        # Make create_workpad fail
        git_engine.create_workpad = Mock(side_effect=Exception("Failed to create workpad"))
        
        # Execute rollback
        result = handler.handle_failed_ci(failed_ci_result, recreate_workpad=True)
        
        # Verify - rollback still succeeds even if workpad creation fails
        assert result.success
        assert result.repo_id == "test-repo"
        assert result.reverted_commit == "abc123def456"
        assert result.new_pad_id is None  # Workpad creation failed
        assert "Rolled back commit abc123de" in result.message
        
        # Verify revert was still called
        git_engine.revert_last_commit.assert_called_once_with("test-repo")
    
    def test_handle_passed_ci_no_rollback(self, handler, git_engine, passed_ci_result):
        """Test handling passed CI (no rollback needed)."""
        # Execute with passed CI
        result = handler.handle_failed_ci(passed_ci_result)
        
        # Verify
        assert result.success
        assert result.repo_id == "test-repo"
        assert result.reverted_commit == "abc123def456"
        assert result.new_pad_id is None
        assert "no rollback needed" in result.message.lower()
        
        # Verify git engine was NOT called
        git_engine.revert_last_commit.assert_not_called()
    
    def test_format_result_success_with_workpad(self, handler):
        """Test formatting successful rollback result with workpad."""
        result = RollbackResult(
            success=True,
            repo_id="test-repo",
            reverted_commit="abc123def456",
            new_pad_id="fix-ci-abc123d",
            message="Rolled back commit abc123de due to failed CI smoke tests. Created workpad fix-ci-abc123d for fixes."
        )
        
        formatted = handler.format_result(result)
        
        # Verify formatting
        assert "AUTOMATIC ROLLBACK" in formatted
        assert "✅ ROLLBACK SUCCESSFUL" in formatted
        assert "Repository: test-repo" in formatted
        assert "Reverted Commit: abc123def456" in formatted
        assert "New Workpad: fix-ci-abc123d" in formatted
        assert "To fix the issues:" in formatted
        assert "sologit test run <pad-id>" in formatted
    
    def test_format_result_success_without_workpad(self, handler):
        """Test formatting successful rollback result without workpad."""
        result = RollbackResult(
            success=True,
            repo_id="test-repo",
            reverted_commit="abc123def456",
            new_pad_id=None,
            message="Rolled back commit abc123de due to failed CI smoke tests."
        )
        
        formatted = handler.format_result(result)
        
        # Verify formatting
        assert "AUTOMATIC ROLLBACK" in formatted
        assert "✅ ROLLBACK SUCCESSFUL" in formatted
        assert "Repository: test-repo" in formatted
        assert "Reverted Commit: abc123def456" in formatted
        assert "New Workpad:" not in formatted  # No workpad created
    
    def test_format_result_failure(self, handler):
        """Test formatting failed rollback result."""
        result = RollbackResult(
            success=False,
            repo_id="test-repo",
            reverted_commit="abc123def456",
            new_pad_id=None,
            message="Rollback failed: Cannot revert commit"
        )
        
        formatted = handler.format_result(result)
        
        # Verify formatting
        assert "AUTOMATIC ROLLBACK" in formatted
        assert "❌ ROLLBACK FAILED" in formatted
        assert "Rollback failed: Cannot revert commit" in formatted
        assert "Repository: test-repo" in formatted
        assert "Reverted Commit: abc123def456" in formatted


class TestCIMonitor:
    """Tests for CIMonitor."""
    
    @pytest.fixture
    def git_engine(self):
        """Mock git engine."""
        return Mock(spec=GitEngine)
    
    @pytest.fixture
    def rollback_handler(self):
        """Mock rollback handler."""
        return Mock(spec=RollbackHandler)
    
    @pytest.fixture
    def monitor(self, git_engine, rollback_handler):
        """Create monitor instance."""
        return CIMonitor(git_engine, rollback_handler)
    
    @pytest.fixture
    def failed_ci_result(self):
        """Create a failed CI result."""
        return CIResult(
            repo_id="test-repo",
            commit_hash="abc123def456",
            status=CIStatus.FAILURE,
            duration_ms=5000,
            test_results=[
                TestResult(
                    name="test_feature",
                    status=TestStatus.FAILED,
                    duration_ms=1000,
                    exit_code=1,
                    stdout="",
                    stderr="",
                    error="AssertionError"
                )
            ]
        )
    
    @pytest.fixture
    def passed_ci_result(self):
        """Create a passed CI result."""
        return CIResult(
            repo_id="test-repo",
            commit_hash="abc123def456",
            status=CIStatus.SUCCESS,
            duration_ms=2000,
            test_results=[
                TestResult(
                    name="test_feature",
                    status=TestStatus.PASSED,
                    duration_ms=1000,
                    exit_code=0,
                    stdout="",
                    stderr=""
                )
            ]
        )
    
    def test_monitor_initialization(self, git_engine, rollback_handler):
        """Test CI monitor initialization."""
        monitor = CIMonitor(git_engine, rollback_handler)
        
        assert monitor.git_engine == git_engine
        assert monitor.rollback_handler == rollback_handler
    
    def test_monitor_and_rollback_failed_ci_with_auto_rollback(self, monitor, rollback_handler, failed_ci_result):
        """Test monitoring failed CI with auto-rollback enabled."""
        # Mock rollback handler
        mock_rollback_result = RollbackResult(
            success=True,
            repo_id="test-repo",
            reverted_commit="abc123def456",
            new_pad_id="fix-ci-abc123d",
            message="Rollback successful"
        )
        rollback_handler.handle_failed_ci = Mock(return_value=mock_rollback_result)
        
        # Execute monitoring
        result = monitor.monitor_and_rollback(failed_ci_result, auto_rollback=True)
        
        # Verify
        assert result is not None
        assert result.success
        assert result.repo_id == "test-repo"
        
        # Verify rollback handler was called
        rollback_handler.handle_failed_ci.assert_called_once_with(failed_ci_result)
    
    def test_monitor_and_rollback_failed_ci_without_auto_rollback(self, monitor, rollback_handler, failed_ci_result):
        """Test monitoring failed CI with auto-rollback disabled."""
        # Execute monitoring with auto_rollback=False
        result = monitor.monitor_and_rollback(failed_ci_result, auto_rollback=False)
        
        # Verify - no rollback performed
        assert result is None
        
        # Verify rollback handler was NOT called
        rollback_handler.handle_failed_ci.assert_not_called()
    
    def test_monitor_and_rollback_passed_ci(self, monitor, rollback_handler, passed_ci_result):
        """Test monitoring passed CI (no rollback needed)."""
        # Execute monitoring with passed CI
        result = monitor.monitor_and_rollback(passed_ci_result, auto_rollback=True)
        
        # Verify - no rollback performed
        assert result is None
        
        # Verify rollback handler was NOT called
        rollback_handler.handle_failed_ci.assert_not_called()
    
    def test_monitor_and_rollback_failed_rollback(self, monitor, rollback_handler, failed_ci_result):
        """Test monitoring when rollback itself fails."""
        # Mock rollback handler to fail
        mock_rollback_result = RollbackResult(
            success=False,
            repo_id="test-repo",
            reverted_commit="abc123def456",
            new_pad_id=None,
            message="Rollback failed: Cannot revert commit"
        )
        rollback_handler.handle_failed_ci = Mock(return_value=mock_rollback_result)
        
        # Execute monitoring
        result = monitor.monitor_and_rollback(failed_ci_result, auto_rollback=True)
        
        # Verify
        assert result is not None
        assert not result.success
        assert "Rollback failed" in result.message
        
        # Verify rollback handler was called
        rollback_handler.handle_failed_ci.assert_called_once_with(failed_ci_result)


class TestRollbackResultDataclass:
    """Tests for RollbackResult dataclass."""
    
    def test_rollback_result_creation(self):
        """Test creating RollbackResult."""
        result = RollbackResult(
            success=True,
            repo_id="test-repo",
            reverted_commit="abc123",
            new_pad_id="fix-pad",
            message="Test message"
        )
        
        assert result.success
        assert result.repo_id == "test-repo"
        assert result.reverted_commit == "abc123"
        assert result.new_pad_id == "fix-pad"
        assert result.message == "Test message"
    
    def test_rollback_result_defaults(self):
        """Test RollbackResult with default values."""
        result = RollbackResult(
            success=False,
            repo_id="test-repo",
            reverted_commit="abc123"
        )
        
        assert not result.success
        assert result.repo_id == "test-repo"
        assert result.reverted_commit == "abc123"
        assert result.new_pad_id is None
        assert result.message == ""


class TestRollbackHandlerEdgeCases:
    """Tests for edge cases and error conditions."""
    
    @pytest.fixture
    def git_engine(self):
        """Mock git engine."""
        return Mock(spec=GitEngine)
    
    @pytest.fixture
    def handler(self, git_engine):
        """Create handler instance."""
        return RollbackHandler(git_engine)
    
    def test_handle_failed_ci_with_get_repo_failure(self, handler, git_engine):
        """Test rollback when get_repo fails during workpad creation."""
        # Create failed CI result
        failed_ci_result = CIResult(
            repo_id="test-repo",
            commit_hash="abc123def456",
            status=CIStatus.FAILURE,
            duration_ms=5000,
            test_results=[]
        )
        
        # Mock git engine - revert succeeds but get_repo fails
        git_engine.revert_last_commit = Mock()
        git_engine.get_repo = Mock(side_effect=GitEngineError("Repository not found"))
        
        # Execute rollback
        result = handler.handle_failed_ci(failed_ci_result, recreate_workpad=True)
        
        # Verify - rollback still succeeds even though get_repo failed
        assert result.success
        assert result.repo_id == "test-repo"
        assert result.new_pad_id is None
        
        # Verify revert was called
        git_engine.revert_last_commit.assert_called_once_with("test-repo")
    
    def test_handle_failed_ci_short_commit_hash(self, handler, git_engine):
        """Test rollback with very short commit hash."""
        # Create failed CI result with short hash
        failed_ci_result = CIResult(
            repo_id="test-repo",
            commit_hash="abc",
            status=CIStatus.FAILURE,
            duration_ms=5000,
            test_results=[]
        )
        
        # Mock git engine
        git_engine.revert_last_commit = Mock()
        
        # Execute rollback
        result = handler.handle_failed_ci(failed_ci_result, recreate_workpad=False)
        
        # Verify - should handle short hash gracefully
        assert result.success
        assert result.repo_id == "test-repo"
        assert result.reverted_commit == "abc"
    
    def test_format_result_with_empty_message(self, handler):
        """Test formatting result with empty message."""
        result = RollbackResult(
            success=True,
            repo_id="test-repo",
            reverted_commit="abc123",
            message=""
        )
        
        formatted = handler.format_result(result)
        
        # Verify - should handle empty message
        assert "AUTOMATIC ROLLBACK" in formatted
        assert "Repository: test-repo" in formatted
    
    def test_format_result_with_very_long_commit_hash(self, handler):
        """Test formatting result with very long commit hash."""
        result = RollbackResult(
            success=True,
            repo_id="test-repo",
            reverted_commit="a" * 100,  # Very long hash
            message="Test"
        )
        
        formatted = handler.format_result(result)
        
        # Verify - should handle long hash
        assert "AUTOMATIC ROLLBACK" in formatted
        assert "a" * 100 in formatted
