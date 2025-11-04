from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from sologit.workflows.ci_orchestrator import CIOrchestrator, CIStatus
from sologit.engines.test_orchestrator import TestResult, TestStatus, TestConfig


@pytest.fixture
def orchestrator(monkeypatch):
    git_engine = Mock()
    git_engine.get_repo.return_value = SimpleNamespace(id="repo-1")
    git_engine.get_history.return_value = [SimpleNamespace(commit="abc")]
    git_engine.create_workpad.return_value = SimpleNamespace(id="pad-1")

    test_orchestrator = Mock()
    orchestrator = CIOrchestrator(git_engine, test_orchestrator)
    return orchestrator, git_engine, test_orchestrator


def make_test_result(name, status):
    return TestResult(name=name, status=status, duration_ms=100)


def test_run_smoke_tests_success(orchestrator, monkeypatch):
    orchestrator_obj, git_engine, test_orchestrator = orchestrator
    test_orchestrator.run_tests_sync.return_value = [
        make_test_result("lint", TestStatus.PASSED),
        make_test_result("unit", TestStatus.PASSED),
    ]

    result = orchestrator_obj.run_smoke_tests("repo-1", "abc123", [TestConfig(name="lint", cmd="lint")])

    assert result.status == CIStatus.SUCCESS
    assert "All smoke tests passed" in result.message
    git_engine.delete_workpad.assert_called_once_with("pad-1")


def test_run_smoke_tests_handles_timeouts(orchestrator):
    orchestrator_obj, _, test_orchestrator = orchestrator
    test_orchestrator.run_tests_sync.return_value = [
        make_test_result("lint", TestStatus.TIMEOUT),
    ]

    result = orchestrator_obj.run_smoke_tests("repo-1", "abc123", [TestConfig(name="lint", cmd="lint")])

    assert result.status == CIStatus.UNSTABLE
    assert "timed out" in result.message


def test_run_smoke_tests_handles_failures(orchestrator):
    orchestrator_obj, _, test_orchestrator = orchestrator
    test_orchestrator.run_tests_sync.return_value = [
        make_test_result("lint", TestStatus.FAILED),
    ]

    result = orchestrator_obj.run_smoke_tests("repo-1", "abc123", [TestConfig(name="lint", cmd="lint")])

    assert result.status == CIStatus.FAILURE
    assert "1 tests failed" in result.message


def test_run_smoke_tests_returns_failure_when_repo_missing(monkeypatch):
    git_engine = Mock()
    git_engine.get_repo.return_value = None
    test_orchestrator = Mock()
    orchestrator = CIOrchestrator(git_engine, test_orchestrator)

    result = orchestrator.run_smoke_tests("missing", "abc", [])

    assert result.status == CIStatus.FAILURE
    assert result.test_results == []


def test_run_smoke_tests_captures_exceptions(orchestrator):
    orchestrator_obj, git_engine, _ = orchestrator
    git_engine.get_history.side_effect = RuntimeError("history missing")

    result = orchestrator_obj.run_smoke_tests("repo-1", "abc123", [])

    assert result.status == CIStatus.FAILURE
    assert "history missing" in result.message


@pytest.mark.asyncio
async def test_run_smoke_tests_async(orchestrator):
    orchestrator_obj, _, test_orchestrator = orchestrator
    test_orchestrator.run_tests_sync.return_value = [
        make_test_result("lint", TestStatus.PASSED),
    ]

    result = await orchestrator_obj.run_smoke_tests_async("repo-1", "abc123", [])
    assert result.status == CIStatus.SUCCESS


def test_format_result_lists_failures(orchestrator):
    orchestrator_obj, _, test_orchestrator = orchestrator
    test_orchestrator.run_tests_sync.return_value = [
        make_test_result("lint", TestStatus.FAILED),
    ]

    result = orchestrator_obj.run_smoke_tests("repo-1", "abc123", [TestConfig(name="lint", cmd="lint")])
    formatted = orchestrator_obj.format_result(result)

    assert "CI SMOKE TESTS" in formatted
    assert "Failed Tests" in formatted
    assert "lint" in formatted


def test_ci_result_is_green():
    """Test CIResult.is_green property."""
    from sologit.workflows.ci_orchestrator import CIResult
    result = CIResult(
        repo_id="test",
        commit_hash="abc123",
        status=CIStatus.SUCCESS,
        duration_ms=100,
        test_results=[]
    )
    assert result.is_green is True
    
    result.status = CIStatus.FAILURE
    assert result.is_green is False


def test_ci_result_is_red():
    """Test CIResult.is_red property."""
    from sologit.workflows.ci_orchestrator import CIResult
    result = CIResult(
        repo_id="test",
        commit_hash="abc123",
        status=CIStatus.FAILURE,
        duration_ms=100,
        test_results=[]
    )
    assert result.is_red is True
    
    result.status = CIStatus.UNSTABLE
    assert result.is_red is True
    
    result.status = CIStatus.SUCCESS
    assert result.is_red is False


def test_run_smoke_tests_with_progress_callback(orchestrator):
    """Test that on_progress callback is called at various stages."""
    orchestrator_obj, _, test_orchestrator = orchestrator
    test_orchestrator.run_tests_sync.return_value = [
        make_test_result("lint", TestStatus.PASSED),
    ]
    
    progress_messages = []
    def on_progress(msg):
        progress_messages.append(msg)
    
    result = orchestrator_obj.run_smoke_tests(
        "repo-1", 
        "abc123", 
        [TestConfig(name="lint", cmd="lint")],
        on_progress=on_progress
    )
    
    assert result.status == CIStatus.SUCCESS
    assert len(progress_messages) >= 3  # Start, Running, Complete
    assert any("Starting smoke tests" in msg for msg in progress_messages)
    assert any("Running" in msg for msg in progress_messages)
    assert any("complete" in msg for msg in progress_messages)


def test_run_smoke_tests_no_commits_in_history(orchestrator):
    """Test handling when get_history returns empty list."""
    orchestrator_obj, git_engine, _ = orchestrator
    git_engine.get_history.return_value = []
    
    result = orchestrator_obj.run_smoke_tests("repo-1", "abc123", [])
    
    assert result.status == CIStatus.FAILURE
    assert "No commits found" in result.message


def test_run_smoke_tests_cleanup_failure_is_tolerated(orchestrator):
    """Test that cleanup failures don't crash the orchestrator."""
    orchestrator_obj, git_engine, test_orchestrator = orchestrator
    test_orchestrator.run_tests_sync.return_value = [
        make_test_result("lint", TestStatus.PASSED),
    ]
    git_engine.delete_workpad.side_effect = RuntimeError("cleanup failed")
    
    # Should not raise, just log
    result = orchestrator_obj.run_smoke_tests("repo-1", "abc123", [TestConfig(name="lint", cmd="lint")])
    
    assert result.status == CIStatus.SUCCESS


def test_run_smoke_tests_with_progress_on_failure(orchestrator):
    """Test on_progress is called even when tests fail."""
    orchestrator_obj, git_engine, _ = orchestrator
    git_engine.get_history.side_effect = RuntimeError("boom")
    
    progress_messages = []
    def on_progress(msg):
        progress_messages.append(msg)
    
    result = orchestrator_obj.run_smoke_tests(
        "repo-1", 
        "abc123", 
        [],
        on_progress=on_progress
    )
    
    assert result.status == CIStatus.FAILURE
    assert any("failed" in msg.lower() or "❌" in msg for msg in progress_messages)


def test_format_result_success_status():
    """Test formatting for successful CI result."""
    from sologit.workflows.ci_orchestrator import CIResult
    
    orchestrator_obj = CIOrchestrator(Mock(), Mock())
    result = CIResult(
        repo_id="test-repo",
        commit_hash="abc123def",
        status=CIStatus.SUCCESS,
        duration_ms=5000,
        test_results=[
            make_test_result("test1", TestStatus.PASSED),
            make_test_result("test2", TestStatus.PASSED),
        ],
        message="All tests passed"
    )
    
    formatted = orchestrator_obj.format_result(result)
    
    assert "✅ SUCCESS" in formatted
    assert "All tests passed" in formatted
    assert "test-repo" in formatted
    assert "abc123def" in formatted
    assert "5.0s" in formatted
    assert "✅ Passed: 2" in formatted


def test_format_result_unstable_status():
    """Test formatting for unstable CI result."""
    from sologit.workflows.ci_orchestrator import CIResult
    
    orchestrator_obj = CIOrchestrator(Mock(), Mock())
    result = CIResult(
        repo_id="test-repo",
        commit_hash="abc123",
        status=CIStatus.UNSTABLE,
        duration_ms=3000,
        test_results=[
            make_test_result("test1", TestStatus.TIMEOUT),
        ],
        message="Some tests timed out"
    )
    
    formatted = orchestrator_obj.format_result(result)
    
    assert "⚠️ UNSTABLE" in formatted
    assert "Some tests timed out" in formatted
    assert "⏱️ Timeout: 1" in formatted


def test_format_result_pending_status():
    """Test formatting for other status types."""
    from sologit.workflows.ci_orchestrator import CIResult
    
    orchestrator_obj = CIOrchestrator(Mock(), Mock())
    result = CIResult(
        repo_id="test-repo",
        commit_hash="abc123",
        status=CIStatus.PENDING,
        duration_ms=0,
        test_results=[],
        message="Waiting"
    )
    
    formatted = orchestrator_obj.format_result(result)
    
    assert "📊 PENDING" in formatted or "pending" in formatted.lower()


def test_format_result_with_timeout_counts():
    """Test formatting includes timeout counts."""
    from sologit.workflows.ci_orchestrator import CIResult
    
    orchestrator_obj = CIOrchestrator(Mock(), Mock())
    result = CIResult(
        repo_id="test-repo",
        commit_hash="abc123",
        status=CIStatus.FAILURE,
        duration_ms=2000,
        test_results=[
            make_test_result("test1", TestStatus.PASSED),
            make_test_result("test2", TestStatus.FAILED),
            make_test_result("test3", TestStatus.TIMEOUT),
        ],
        message="Mixed results"
    )
    
    formatted = orchestrator_obj.format_result(result)
    
    assert "❌ FAILURE" in formatted
    assert "✅ Passed: 1" in formatted
    assert "❌ Failed: 1" in formatted
    assert "⏱️ Timeout: 1" in formatted
    assert "test2" in formatted
    assert "test3" in formatted
