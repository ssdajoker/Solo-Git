"""Tests for the TestOrchestrator execution engine."""
from pathlib import Path
from types import SimpleNamespace
from typing import List
from unittest.mock import Mock

import pytest

from sologit.engines.test_orchestrator import (
    TestConfig,
    TestOrchestrator,
    TestResult,
    TestStatus,
)


@pytest.fixture
def repo_path(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    return repo


@pytest.fixture
def mock_git_engine(repo_path: Path) -> Mock:
    engine = Mock()
    workpad = SimpleNamespace(id="pad-1", repo_id="repo-1", title="Demo")
    repo = SimpleNamespace(path=repo_path)
    engine.get_workpad.return_value = workpad
    engine.get_repo.return_value = repo
    return engine




def make_orchestrator(mock_git_engine: Mock, tmp_path: Path) -> TestOrchestrator:
    return TestOrchestrator(
        mock_git_engine,
        log_dir=tmp_path / "logs",
    )


def test_initializes_in_subprocess_mode(tmp_path: Path, mock_git_engine: Mock):
    orchestrator = make_orchestrator(mock_git_engine, tmp_path)
    assert orchestrator.mode == "subprocess"


@pytest.mark.asyncio
async def test_sequential_respects_dependencies(tmp_path: Path, mock_git_engine: Mock):
    orchestrator = make_orchestrator(mock_git_engine, tmp_path)

    tests = [
        TestConfig(name="ok", cmd="python -c 'print(\"ok\")'", timeout=10),
        TestConfig(name="fail", cmd="python -c 'import sys; sys.exit(1)'", timeout=10),
        TestConfig(name="skipped", cmd="python -c 'print(\"skip\")'", timeout=10, depends_on=["fail"]),
    ]

    results = await orchestrator.run_tests("pad-1", tests, parallel=False)

    assert [r.status for r in results] == [TestStatus.PASSED, TestStatus.FAILED, TestStatus.SKIPPED]
    assert results[2].error and "dependency" in results[2].error.lower()
    assert results[0].log_path and results[0].log_path.exists()


@pytest.mark.asyncio
async def test_parallel_invokes_callbacks(tmp_path: Path, mock_git_engine: Mock):
    orchestrator = make_orchestrator(mock_git_engine, tmp_path)

    tests = [
        TestConfig(name="first", cmd="python -c 'print(\"first\")'", timeout=10),
        TestConfig(name="second", cmd="python -c 'print(\"second\")'", timeout=10),
    ]

    seen_lines = []
    completed = []

    def handle_output(name: str, stream: str, line: str) -> None:
        seen_lines.append((name, stream, line))

    def handle_complete(result: TestResult) -> None:
        completed.append(result.name)

    results = await orchestrator.run_tests(
        "pad-1",
        tests,
        parallel=True,
        on_output=handle_output,
        on_test_complete=handle_complete,
    )

    assert len(results) == 2
    assert {res.name for res in results} == {"first", "second"}
    assert completed == [res.name for res in results]
    assert any(stream == "stdout" for _, stream, _ in seen_lines)


@pytest.mark.asyncio
async def test_collects_metrics(tmp_path: Path, mock_git_engine: Mock):
    orchestrator = make_orchestrator(mock_git_engine, tmp_path)

    tests = [TestConfig(name="metrics", cmd="python -c 'print(123)'", timeout=10)]

    results = await orchestrator.run_tests("pad-1", tests, parallel=False)
    metrics = results[0].metrics

    assert metrics["mode"] == "subprocess"
    assert "duration_ms" in metrics
    assert "exit_code" in metrics


