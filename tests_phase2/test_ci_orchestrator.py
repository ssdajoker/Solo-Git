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
