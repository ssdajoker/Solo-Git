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
