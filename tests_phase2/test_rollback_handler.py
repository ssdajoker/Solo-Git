from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from sologit.engines.git_engine import GitEngineError
from sologit.workflows.ci_orchestrator import CIResult, CIStatus
from sologit.workflows.rollback_handler import RollbackHandler


@pytest.fixture
def git_engine():
    engine = Mock()
    engine.revert_last_commit = Mock()
    engine.get_repo.return_value = SimpleNamespace(id="repo-1")
    engine.create_workpad.return_value = SimpleNamespace(id="pad-123")
    return engine


@pytest.fixture
def ci_failure():
    return CIResult(
        repo_id="repo-1",
        commit_hash="abcdef123456",
        status=CIStatus.FAILURE,
        duration_ms=500,
        test_results=[],
        message="Tests failed",
    )


def test_handle_failed_ci_creates_workpad(git_engine, ci_failure):
    handler = RollbackHandler(git_engine)
    result = handler.handle_failed_ci(ci_failure)

    git_engine.revert_last_commit.assert_called_once_with("repo-1")
    git_engine.create_workpad.assert_called_once()
    assert result.success is True
    assert result.new_pad_id == "pad-123"
    assert "Rolled back" in result.message


def test_handle_failed_ci_without_recreation(git_engine, ci_failure):
    handler = RollbackHandler(git_engine)
    result = handler.handle_failed_ci(ci_failure, recreate_workpad=False)

    git_engine.create_workpad.assert_not_called()
    assert result.success is True
    assert result.new_pad_id is None


def test_handle_failed_ci_handles_git_errors(git_engine, ci_failure):
    git_engine.revert_last_commit.side_effect = GitEngineError("boom")
    handler = RollbackHandler(git_engine)
    result = handler.handle_failed_ci(ci_failure)

    assert result.success is False
    assert "boom" in result.message


def test_handle_failed_ci_skips_when_status_green(git_engine):
    handler = RollbackHandler(git_engine)
    ci_result = CIResult(
        repo_id="repo-1",
        commit_hash="abcdef",
        status=CIStatus.SUCCESS,
        duration_ms=10,
        test_results=[],
        message="ok",
    )

    result = handler.handle_failed_ci(ci_result)
    assert result.success is True
    assert "no rollback" in result.message.lower()


def test_handle_failed_ci_tolerates_workpad_errors(git_engine, ci_failure):
    git_engine.create_workpad.side_effect = RuntimeError("pad boom")
    handler = RollbackHandler(git_engine)
    result = handler.handle_failed_ci(ci_failure)

    assert result.success is True
    assert result.new_pad_id is None


def test_format_result_includes_key_fields(git_engine, ci_failure):
    handler = RollbackHandler(git_engine)
    outcome = handler.handle_failed_ci(ci_failure)
    formatted = handler.format_result(outcome)

    assert "AUTOMATIC ROLLBACK" in formatted
    assert "Repository: repo-1" in formatted
    assert "pad-123" in formatted


def test_format_result_success_with_workpad():
    """Test formatting successful rollback with workpad creation."""
    from sologit.workflows.rollback_handler import RollbackResult
    handler = RollbackHandler(Mock())
    
    result = RollbackResult(
        success=True,
        repo_id="test-repo",
        reverted_commit="abc123",
        new_pad_id="fix-pad-1",
        message="Rolled back successfully"
    )
    
    formatted = handler.format_result(result)
    
    assert "✅ ROLLBACK SUCCESSFUL" in formatted
    assert "Rolled back successfully" in formatted
    assert "test-repo" in formatted
    assert "abc123" in formatted
    assert "fix-pad-1" in formatted
    assert "To fix the issues:" in formatted
    assert "sologit test run" in formatted
    assert "sologit pad auto-merge" in formatted


def test_format_result_success_without_workpad():
    """Test formatting successful rollback without workpad."""
    from sologit.workflows.rollback_handler import RollbackResult
    handler = RollbackHandler(Mock())
    
    result = RollbackResult(
        success=True,
        repo_id="test-repo",
        reverted_commit="abc123",
        new_pad_id=None,
        message="Reverted commit"
    )
    
    formatted = handler.format_result(result)
    
    assert "✅ ROLLBACK SUCCESSFUL" in formatted
    assert "Reverted commit" in formatted
    # Should not have workpad instructions
    assert "New Workpad:" not in formatted


def test_format_result_failure():
    """Test formatting failed rollback."""
    from sologit.workflows.rollback_handler import RollbackResult
    handler = RollbackHandler(Mock())
    
    result = RollbackResult(
        success=False,
        repo_id="test-repo",
        reverted_commit="abc123",
        message="Failed to revert"
    )
    
    formatted = handler.format_result(result)
    
    assert "❌ ROLLBACK FAILED" in formatted
    assert "Failed to revert" in formatted


def test_handle_failed_ci_workpad_creation_with_proper_title(git_engine, ci_failure):
    """Test that workpad is created with proper naming."""
    handler = RollbackHandler(git_engine)
    result = handler.handle_failed_ci(ci_failure)
    
    # Check that create_workpad was called with proper title
    call_args = git_engine.create_workpad.call_args
    assert call_args[0][0] == "repo-1"
    assert call_args[0][1].startswith("fix-ci-")
    assert result.success is True


def test_handle_failed_ci_includes_new_pad_in_message(git_engine, ci_failure):
    """Test that success message includes workpad ID."""
    handler = RollbackHandler(git_engine)
    result = handler.handle_failed_ci(ci_failure)
    
    assert "pad-123" in result.message
    assert "Created workpad" in result.message


def test_handle_failed_ci_message_without_pad_when_not_recreated(git_engine, ci_failure):
    """Test message doesn't mention workpad when recreation disabled."""
    handler = RollbackHandler(git_engine)
    result = handler.handle_failed_ci(ci_failure, recreate_workpad=False)
    
    assert "Created workpad" not in result.message


# CIMonitor tests
def test_ci_monitor_initialization():
    """Test CIMonitor initialization."""
    from sologit.workflows.rollback_handler import CIMonitor
    git_engine = Mock()
    handler = RollbackHandler(git_engine)
    monitor = CIMonitor(git_engine, handler)
    
    assert monitor.git_engine is git_engine
    assert monitor.rollback_handler is handler


def test_monitor_and_rollback_triggers_on_failure(git_engine, ci_failure):
    """Test that monitor triggers rollback on CI failure."""
    from sologit.workflows.rollback_handler import CIMonitor
    handler = RollbackHandler(git_engine)
    monitor = CIMonitor(git_engine, handler)
    
    result = monitor.monitor_and_rollback(ci_failure, auto_rollback=True)
    
    assert result is not None
    assert result.success is True
    git_engine.revert_last_commit.assert_called_once()


def test_monitor_and_rollback_no_action_on_success(git_engine):
    """Test that monitor does nothing when CI passes."""
    from sologit.workflows.rollback_handler import CIMonitor
    handler = RollbackHandler(git_engine)
    monitor = CIMonitor(git_engine, handler)
    
    ci_success = CIResult(
        repo_id="repo-1",
        commit_hash="abc123",
        status=CIStatus.SUCCESS,
        duration_ms=100,
        test_results=[],
        message="All passed"
    )
    
    result = monitor.monitor_and_rollback(ci_success, auto_rollback=True)
    
    assert result is None
    git_engine.revert_last_commit.assert_not_called()


def test_monitor_and_rollback_disabled_returns_none(git_engine, ci_failure):
    """Test that monitor returns None when auto_rollback is disabled."""
    from sologit.workflows.rollback_handler import CIMonitor
    handler = RollbackHandler(git_engine)
    monitor = CIMonitor(git_engine, handler)
    
    result = monitor.monitor_and_rollback(ci_failure, auto_rollback=False)
    
    assert result is None
    git_engine.revert_last_commit.assert_not_called()


def test_monitor_and_rollback_propagates_rollback_failures(git_engine, ci_failure):
    """Test that monitor captures rollback failures."""
    from sologit.workflows.rollback_handler import CIMonitor
    git_engine.revert_last_commit.side_effect = GitEngineError("revert failed")
    handler = RollbackHandler(git_engine)
    monitor = CIMonitor(git_engine, handler)
    
    result = monitor.monitor_and_rollback(ci_failure, auto_rollback=True)
    
    assert result is not None
    assert result.success is False
    assert "revert failed" in result.message
