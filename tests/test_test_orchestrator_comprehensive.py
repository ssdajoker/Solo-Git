"""Tests for the TestOrchestrator execution engine."""
from pathlib import Path
from types import SimpleNamespace
from typing import List
from unittest.mock import Mock, patch

import pytest
from docker.errors import DockerException

from sologit.engines.test_orchestrator import (
    TestConfig,
    TestExecutionMode,
    TestOrchestrator,
    TestOrchestratorError,
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


class FakeContainer:
    def __init__(self, stdout: List[bytes], stderr: List[bytes], status_code: int = 0):
        self._stdout = stdout
        self._stderr = stderr
        self._status = status_code
        self.id = "abc123"

    def start(self) -> None:
        return None

    def wait(self) -> dict:
        return {"StatusCode": self._status}

    def stop(self, timeout: int = 5) -> None:
        return None

    def remove(self, force: bool = True) -> None:
        return None

    def stats(self, stream: bool = False) -> dict:
        return {
            "cpu_stats": {
                "cpu_usage": {"total_usage": 200000000},
                "system_cpu_usage": 400000000,
            },
            "precpu_stats": {
                "cpu_usage": {"total_usage": 100000000},
                "system_cpu_usage": 300000000,
            },
            "memory_stats": {"usage": 1024, "limit": 2048},
        }

    def attach(self, stream: bool, stdout: bool, stderr: bool, demux: bool):
        for out, err in zip(self._stdout + [None] * max(0, len(self._stderr) - len(self._stdout)),
                             self._stderr + [None] * max(0, len(self._stdout) - len(self._stderr))):
            yield out, err


@pytest.fixture
def fake_docker_client() -> Mock:
    client = Mock()
    container = FakeContainer([b"docker stdout"], [b"docker stderr"], status_code=0)
    client.containers.create.return_value = container
    return client


def make_orchestrator(mock_git_engine: Mock, tmp_path: Path, mode: str = "auto") -> TestOrchestrator:
    return TestOrchestrator(
        mock_git_engine,
        sandbox_image="python:3.11-slim",
        execution_mode=mode,
        log_dir=tmp_path / "logs",
    )


def test_initializes_with_docker(tmp_path: Path, mock_git_engine: Mock, fake_docker_client: Mock):
    with patch("docker.from_env", return_value=fake_docker_client):
        orchestrator = make_orchestrator(mock_git_engine, tmp_path)

    assert orchestrator.mode == TestExecutionMode.DOCKER
    assert orchestrator.docker_client is fake_docker_client


def test_falls_back_to_subprocess_when_docker_missing(tmp_path: Path, mock_git_engine: Mock):
    with patch("docker.from_env", side_effect=DockerException("missing")):
        orchestrator = make_orchestrator(mock_git_engine, tmp_path)

    assert orchestrator.mode == TestExecutionMode.SUBPROCESS
    assert orchestrator.docker_client is None


def test_raises_when_docker_mode_requested(tmp_path: Path, mock_git_engine: Mock):
    with patch("docker.from_env", side_effect=DockerException("missing")):
        with pytest.raises(TestOrchestratorError):
            make_orchestrator(mock_git_engine, tmp_path, mode="docker")


@pytest.mark.asyncio
async def test_sequential_respects_dependencies(tmp_path: Path, mock_git_engine: Mock):
    orchestrator = make_orchestrator(mock_git_engine, tmp_path, mode="subprocess")

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
    orchestrator = make_orchestrator(mock_git_engine, tmp_path, mode="subprocess")

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
    orchestrator = make_orchestrator(mock_git_engine, tmp_path, mode="subprocess")

    tests = [TestConfig(name="metrics", cmd="python -c 'print(123)'", timeout=10)]

    results = await orchestrator.run_tests("pad-1", tests, parallel=False)
    metrics = results[0].metrics

    assert metrics["mode"] == "subprocess"
    assert "duration_ms" in metrics
    assert "exit_code" in metrics


@pytest.mark.asyncio
async def test_docker_execution_streams_logs(tmp_path: Path, mock_git_engine: Mock, fake_docker_client: Mock):
    with patch("docker.from_env", return_value=fake_docker_client):
        orchestrator = make_orchestrator(mock_git_engine, tmp_path)

    tests = [TestConfig(name="docker", cmd="echo 'ignored'", timeout=10)]

    seen_lines = []

    def handle_output(name: str, stream: str, line: str) -> None:
        seen_lines.append((name, stream, line))

    results = await orchestrator.run_tests(
        "pad-1",
        tests,
        parallel=False,
        on_output=handle_output,
    )

    assert results[0].status == TestStatus.PASSED
    assert ("docker", "stdout", "docker stdout") in seen_lines
    assert ("docker", "stderr", "docker stderr") in seen_lines
    assert results[0].metrics.get("cpu_percent") is not None
    assert results[0].log_path and results[0].log_path.exists()
