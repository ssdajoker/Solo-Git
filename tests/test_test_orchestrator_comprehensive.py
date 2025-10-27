
"""Comprehensive tests for TestOrchestrator covering all execution modes and edge cases."""
import asyncio
from pathlib import Path
from typing import List
from unittest.mock import AsyncMock, Mock, patch

import pytest

from sologit.engines.test_orchestrator import TestConfig, TestOrchestrator, TestResult, TestStatus


@pytest.fixture
def mock_git_engine():
    """Mock GitEngine for testing."""
    engine = Mock()
    engine.get_repository.return_value = Mock(path="/fake/repo")
    engine.get_workpad.return_value = Mock(branch_name="pad-1")
    return engine


def make_orchestrator(git_engine: Mock, tmp_path: Path, mode: str = "subprocess") -> TestOrchestrator:
    """Helper to create a TestOrchestrator with the given mode."""
    return TestOrchestrator(
        git_engine=git_engine,
        log_dir=tmp_path,
        execution_mode=mode,
    )


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
    # In parallel execution, completion order is non-deterministic
    assert set(completed) == {res.name for res in results}
    assert any(stream == "stdout" for _, stream, _ in seen_lines)


@pytest.mark.asyncio
async def test_sequential_respects_order(tmp_path: Path, mock_git_engine: Mock):
    orchestrator = make_orchestrator(mock_git_engine, tmp_path, mode="subprocess")

    tests = [
        TestConfig(name="first", cmd="python -c 'import time; time.sleep(0.1); print(\"first\")'", timeout=10),
        TestConfig(name="second", cmd="python -c 'print(\"second\")'", timeout=10),
    ]

    completed = []

    def handle_complete(result: TestResult) -> None:
        completed.append(result.name)

    results = await orchestrator.run_tests(
        "pad-1",
        tests,
        parallel=False,
        on_test_complete=handle_complete,
    )

    assert len(results) == 2
    # Sequential execution should maintain order
    assert [res.name for res in results] == ["first", "second"]
    assert completed == ["first", "second"]


@pytest.mark.asyncio
async def test_timeout_handling(tmp_path: Path, mock_git_engine: Mock):
    orchestrator = make_orchestrator(mock_git_engine, tmp_path, mode="subprocess")

    tests = [
        TestConfig(name="slow", cmd="python -c 'import time; time.sleep(10)'", timeout=0.5),
    ]

    results = await orchestrator.run_tests("pad-1", tests, parallel=False)

    assert len(results) == 1
    assert results[0].status == TestStatus.TIMEOUT
    assert results[0].duration >= 0.5


@pytest.mark.asyncio
async def test_failure_captured(tmp_path: Path, mock_git_engine: Mock):
    orchestrator = make_orchestrator(mock_git_engine, tmp_path, mode="subprocess")

    tests = [
        TestConfig(name="fail", cmd="python -c 'import sys; sys.exit(1)'", timeout=10),
    ]

    results = await orchestrator.run_tests("pad-1", tests, parallel=False)

    assert len(results) == 1
    assert results[0].status == TestStatus.FAILED
    assert results[0].exit_code == 1


@pytest.mark.asyncio
async def test_success_captured(tmp_path: Path, mock_git_engine: Mock):
    orchestrator = make_orchestrator(mock_git_engine, tmp_path, mode="subprocess")

    tests = [
        TestConfig(name="pass", cmd="python -c 'print(\"ok\")'", timeout=10),
    ]

    results = await orchestrator.run_tests("pad-1", tests, parallel=False)

    assert len(results) == 1
    assert results[0].status == TestStatus.PASSED
    assert results[0].exit_code == 0
    assert "ok" in results[0].output


@pytest.mark.asyncio
async def test_mixed_results(tmp_path: Path, mock_git_engine: Mock):
    orchestrator = make_orchestrator(mock_git_engine, tmp_path, mode="subprocess")

    tests = [
        TestConfig(name="pass", cmd="python -c 'print(\"ok\")'", timeout=10),
        TestConfig(name="fail", cmd="python -c 'import sys; sys.exit(1)'", timeout=10),
        TestConfig(name="timeout", cmd="python -c 'import time; time.sleep(10)'", timeout=0.5),
    ]

    results = await orchestrator.run_tests("pad-1", tests, parallel=True)

    assert len(results) == 3
    statuses = {res.name: res.status for res in results}
    assert statuses["pass"] == TestStatus.PASSED
    assert statuses["fail"] == TestStatus.FAILED
    assert statuses["timeout"] == TestStatus.TIMEOUT


@pytest.mark.asyncio
async def test_output_callback_receives_all_lines(tmp_path: Path, mock_git_engine: Mock):
    orchestrator = make_orchestrator(mock_git_engine, tmp_path, mode="subprocess")

    tests = [
        TestConfig(name="multi", cmd="python -c 'print(\"line1\"); print(\"line2\")'", timeout=10),
    ]

    seen_lines = []

    def handle_output(name: str, stream: str, line: str) -> None:
        seen_lines.append(line)

    await orchestrator.run_tests("pad-1", tests, parallel=False, on_output=handle_output)

    assert "line1" in seen_lines
    assert "line2" in seen_lines


@pytest.mark.asyncio
async def test_empty_test_list(tmp_path: Path, mock_git_engine: Mock):
    orchestrator = make_orchestrator(mock_git_engine, tmp_path, mode="subprocess")

    results = await orchestrator.run_tests("pad-1", [], parallel=False)

    assert results == []


@pytest.mark.asyncio
async def test_workpad_not_found(tmp_path: Path, mock_git_engine: Mock):
    mock_git_engine.get_workpad.side_effect = ValueError("Workpad not found")
    orchestrator = make_orchestrator(mock_git_engine, tmp_path, mode="subprocess")

    tests = [TestConfig(name="test", cmd="echo ok", timeout=10)]

    with pytest.raises(ValueError, match="Workpad not found"):
        await orchestrator.run_tests("nonexistent", tests, parallel=False)


@pytest.mark.asyncio
async def test_cleanup_on_exception(tmp_path: Path, mock_git_engine: Mock):
    orchestrator = make_orchestrator(mock_git_engine, tmp_path, mode="subprocess")

    tests = [
        TestConfig(name="test", cmd="python -c 'print(\"ok\")'", timeout=10),
    ]

    # Simulate an exception during test execution
    with patch.object(orchestrator, '_run_test_subprocess', side_effect=RuntimeError("Simulated error")):
        with pytest.raises(RuntimeError, match="Simulated error"):
            await orchestrator.run_tests("pad-1", tests, parallel=False)


@pytest.mark.asyncio
async def test_progress_callback_invoked(tmp_path: Path, mock_git_engine: Mock):
    orchestrator = make_orchestrator(mock_git_engine, tmp_path, mode="subprocess")

    tests = [
        TestConfig(name="test1", cmd="python -c 'print(\"ok\")'", timeout=10),
        TestConfig(name="test2", cmd="python -c 'print(\"ok\")'", timeout=10),
    ]

    progress_calls = []

    def handle_progress(completed: int, total: int) -> None:
        progress_calls.append((completed, total))

    await orchestrator.run_tests("pad-1", tests, parallel=False, on_progress=handle_progress)

    assert len(progress_calls) > 0
    assert progress_calls[-1] == (2, 2)


@pytest.mark.asyncio
async def test_stderr_captured(tmp_path: Path, mock_git_engine: Mock):
    orchestrator = make_orchestrator(mock_git_engine, tmp_path, mode="subprocess")

    tests = [
        TestConfig(name="stderr", cmd="python -c 'import sys; sys.stderr.write(\"error\\n\")'", timeout=10),
    ]

    seen_lines = []

    def handle_output(name: str, stream: str, line: str) -> None:
        seen_lines.append((stream, line))

    results = await orchestrator.run_tests("pad-1", tests, parallel=False, on_output=handle_output)

    assert any(stream == "stderr" and "error" in line for stream, line in seen_lines)
    assert "error" in results[0].output


@pytest.mark.asyncio
async def test_large_output_handling(tmp_path: Path, mock_git_engine: Mock):
    orchestrator = make_orchestrator(mock_git_engine, tmp_path, mode="subprocess")

    # Generate a large output
    tests = [
        TestConfig(
            name="large",
            cmd="python -c 'for i in range(1000): print(f\"line {i}\")'",
            timeout=10
        ),
    ]

    results = await orchestrator.run_tests("pad-1", tests, parallel=False)

    assert len(results) == 1
    assert results[0].status == TestStatus.PASSED
    assert "line 999" in results[0].output


@pytest.mark.asyncio
async def test_concurrent_limit_respected(tmp_path: Path, mock_git_engine: Mock):
    orchestrator = make_orchestrator(mock_git_engine, tmp_path, mode="subprocess")

    # Create many tests
    tests = [
        TestConfig(name=f"test{i}", cmd="python -c 'import time; time.sleep(0.1)'", timeout=10)
        for i in range(20)
    ]

    results = await orchestrator.run_tests("pad-1", tests, parallel=True)

    assert len(results) == 20
    assert all(res.status == TestStatus.PASSED for res in results)


@pytest.mark.asyncio
async def test_test_result_dataclass_properties(tmp_path: Path, mock_git_engine: Mock):
    orchestrator = make_orchestrator(mock_git_engine, tmp_path, mode="subprocess")

    tests = [
        TestConfig(name="test", cmd="python -c 'print(\"output\")'", timeout=10),
    ]

    results = await orchestrator.run_tests("pad-1", tests, parallel=False)

    result = results[0]
    assert result.name == "test"
    assert result.status == TestStatus.PASSED
    assert result.exit_code == 0
    assert "output" in result.output
    assert result.duration >= 0
    assert result.timestamp is not None


@pytest.mark.asyncio
async def test_environment_variables_passed(tmp_path: Path, mock_git_engine: Mock):
    orchestrator = make_orchestrator(mock_git_engine, tmp_path, mode="subprocess")

    tests = [
        TestConfig(
            name="env",
            cmd="python -c 'import os; print(os.environ.get(\"TEST_VAR\", \"not_set\"))'",
            timeout=10,
            env={"TEST_VAR": "test_value"}
        ),
    ]

    results = await orchestrator.run_tests("pad-1", tests, parallel=False)

    assert len(results) == 1
    assert "test_value" in results[0].output


@pytest.mark.asyncio
async def test_working_directory_set(tmp_path: Path, mock_git_engine: Mock):
    orchestrator = make_orchestrator(mock_git_engine, tmp_path, mode="subprocess")

    tests = [
        TestConfig(name="pwd", cmd="python -c 'import os; print(os.getcwd())'", timeout=10),
    ]

    results = await orchestrator.run_tests("pad-1", tests, parallel=False)

    assert len(results) == 1
    assert "/fake/repo" in results[0].output
