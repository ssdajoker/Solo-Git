"""Test orchestration using direct subprocess execution."""

from __future__ import annotations

import asyncio
import re
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

try:  # pragma: no cover - platform-specific dependency
    import resource  # type: ignore
except ImportError:  # pragma: no cover - Windows compatibility
    resource = None

from sologit.engines.git_engine import GitEngine, WorkpadNotFoundError
from sologit.utils.logger import get_logger
from sologit.ui.formatter import RichFormatter

logger = get_logger(__name__)


class TestStatus(Enum):
    """Test execution status."""
    __test__ = False
    PASSED = "passed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class TestConfig:
    """Test configuration."""
    __test__ = False
    name: str
    cmd: str
    timeout: int = 300
    depends_on: List[str] = None

    def __post_init__(self) -> None:
        if self.depends_on is None:
            self.depends_on = []


@dataclass
class TestResult:
    """Test execution result."""
    __test__ = False
    name: str
    status: TestStatus
    duration_ms: int
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    error: Optional[str] = None
    log_path: Optional[Path] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    mode: str = "subprocess"


class TestOrchestratorError(Exception):
    """Base exception for Test Orchestrator errors."""
    __test__ = False


class TestOrchestrator:
    """Coordinate test execution using subprocesses."""

    def __init__(
        self,
        git_engine: GitEngine,
        log_dir: Optional[Path] = None,
        formatter: Optional[RichFormatter] = None,
    ) -> None:
        """Initialize Test Orchestrator."""

        self.git_engine = git_engine
        self.log_dir = Path(log_dir or (Path.home() / ".sologit" / "data" / "test_runs"))
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.formatter = formatter or RichFormatter()
        self.mode = "subprocess"
        logger.info("TestOrchestrator initialized in subprocess mode")

    @contextmanager
    def _progress(
        self, description: str, total: Optional[int] = None
    ) -> Iterator[Optional[Tuple[Any, int]]]:
        """Create a scoped progress context if a formatter is available."""
        if not self.formatter:
            yield None
            return

        with self.formatter.progress(description) as progress:
            task_id = progress.add_task(f"{description} progress", total=total)
            try:
                yield (progress, task_id)
            finally:
                progress.stop_task(task_id)

    @contextmanager
    def _progress_stage(
        self,
        progress,
        task_id: Optional[int],
        description: str,
        advance: int = 1,
    ) -> Iterator[None]:
        """Show a spinner for a single orchestration stage."""
        if not progress or task_id is None:
            yield
            return

        stage_task = progress.add_task(description, total=None)
        progress.update(task_id, description=description)
        success = False
        start = time.perf_counter()
        try:
            yield
            success = True
        finally:
            progress.remove_task(stage_task)
            if success and advance:
                progress.advance(task_id, advance)
            if success:
                duration = time.perf_counter() - start
                logger.debug("Stage '%s' completed in %.2fs", description, duration)

    def _start_test_progress(
        self,
        progress,
        active_tasks: Dict[str, int],
        test_name: str,
    ) -> None:
        """Start an indeterminate progress spinner for an active test."""
        if not progress:
            return
        if test_name in active_tasks:
            return
        active_tasks[test_name] = progress.add_task(f"{test_name}", total=None)

    def _complete_test_progress(
        self,
        progress,
        active_tasks: Dict[str, int],
        test_name: str,
        execution_task: Optional[int],
        overall_task: Optional[int],
    ) -> None:
        """Close test spinner and advance aggregate progress bars."""
        if not progress:
            return

        task_id = active_tasks.pop(test_name, None)
        if task_id is not None:
            progress.remove_task(task_id)

        if execution_task is not None:
            progress.advance(execution_task, 1)

        if overall_task is not None:
            progress.advance(overall_task, 1)

    async def run_tests(
        self,
        pad_id: str,
        tests: List[TestConfig],
        parallel: bool = True,
        on_output: Optional[Callable[[str, str, str], None]] = None,
        on_test_complete: Optional[Callable[[TestResult], None]] = None,
    ) -> List[TestResult]:
        """Run tests with optional streaming callbacks."""

        logger.info(
            "Running %s test(s) for pad %s (parallel=%s, mode=%s)",
            len(tests),
            pad_id,
            parallel,
            self.mode,
        )

        workpad = self.git_engine.get_workpad(pad_id)
        if not workpad:
            raise WorkpadNotFoundError(f"Workpad {pad_id} not found")

        total_tests = len(tests)
        overall_total = max(total_tests + 2, 2)

        with self._progress(
            f"Running test suite ({'parallel' if parallel else 'sequential'})",
            total=overall_total,
        ) as progress_ctx:
            progress, overall_task = progress_ctx or (None, None)
            execution_task = None
            active_tasks: Dict[str, int] = {}

            repository = None
            with self._progress_stage(progress, overall_task, "Preparing test workspace", 1):
                repository = self.git_engine.get_repo(workpad.repo_id)

            if progress and total_tests:
                progress.update(overall_task, description="Executing tests")
                execution_task = progress.add_task("Executing tests", total=total_tests)

            if parallel:
                results = await self._run_parallel(
                    repository.path,
                    tests,
                    on_output=on_output,
                    on_test_complete=on_test_complete,
                    progress=progress,
                    execution_task=execution_task,
                    overall_task=overall_task,
                    active_tasks=active_tasks,
                )
            else:
                results = await self._run_sequential(
                    repository.path,
                    tests,
                    on_output=on_output,
                    on_test_complete=on_test_complete,
                    progress=progress,
                    execution_task=execution_task,
                    overall_task=overall_task,
                    active_tasks=active_tasks,
                )

            with self._progress_stage(progress, overall_task, "Aggregating results", 1):
                passed = sum(1 for r in results if r.status == TestStatus.PASSED)
                failed = len(results) - passed

            if progress and overall_task is not None:
                progress.update(
                    overall_task,
                    description="Test suite complete",
                    completed=overall_total,
                )

        logger.info("Tests complete: %s passed, %s failed", passed, failed)

        return results

    def run_tests_sync(
        self,
        pad_id: str,
        tests: List[TestConfig],
        parallel: bool = True,
        on_output: Optional[Callable[[str, str, str], None]] = None,
        on_test_complete: Optional[Callable[[TestResult], None]] = None,
    ) -> List[TestResult]:
        """Synchronous wrapper for :meth:`run_tests`."""

        return asyncio.run(
            self.run_tests(
                pad_id,
                tests,
                parallel,
                on_output=on_output,
                on_test_complete=on_test_complete,
            )
        )

    async def _run_sequential(
        self,
        repo_path: Path,
        tests: List[TestConfig],
        *,
        on_output: Optional[Callable[[str, str, str], None]] = None,
        on_test_complete: Optional[Callable[[TestResult], None]] = None,
        progress=None,
        execution_task: Optional[int] = None,
        overall_task: Optional[int] = None,
        active_tasks: Optional[Dict[str, int]] = None,
    ) -> List[TestResult]:
        """Run tests sequentially while respecting dependencies."""

        with self._progress_stage(progress, overall_task, "Resolving execution order", 0):
            ordered_tests = self._resolve_execution_order(tests)
        results: List[TestResult] = []
        result_map: Dict[str, TestResult] = {}
        active = active_tasks if active_tasks is not None else {}

        for test in ordered_tests:
            blocked = self._blocked_dependencies(test, result_map)
            if blocked:
                result = self._create_skipped_result(test, blocked)
                self._complete_test_progress(
                    progress,
                    active,
                    test.name,
                    execution_task,
                    overall_task,
                )
            else:
                logger.debug("Running test sequentially: %s", test.name)
                self._start_test_progress(progress, active, test.name)
                result = await self._run_single_test(
                    repo_path,
                    test,
                    on_output=on_output,
                )
                self._complete_test_progress(
                    progress,
                    active,
                    test.name,
                    execution_task,
                    overall_task,
                )

            results.append(result)
            result_map[test.name] = result

            if on_test_complete:
                on_test_complete(result)

        return results

    async def _run_parallel(
        self,
        repo_path: Path,
        tests: List[TestConfig],
        *,
        on_output: Optional[Callable[[str, str, str], None]] = None,
        on_test_complete: Optional[Callable[[TestResult], None]] = None,
        progress=None,
        execution_task: Optional[int] = None,
        overall_task: Optional[int] = None,
        active_tasks: Optional[Dict[str, int]] = None,
    ) -> List[TestResult]:
        """Run tests in parallel with dependency awareness."""

        with self._progress_stage(progress, overall_task, "Analyzing test dependencies", 0):
            graph = self._build_dependency_graph(tests)
        results: List[TestResult] = []
        result_map: Dict[str, TestResult] = {}
        completed = set()
        running: Dict[str, asyncio.Task[TestResult]] = {}
        active = active_tasks if active_tasks is not None else {}

        while len(completed) < len(tests):
            for test in tests:
                if test.name in completed or test.name in running:
                    continue

                blocked = self._blocked_dependencies(test, result_map)
                if blocked:
                    result = self._create_skipped_result(test, blocked)
                    results.append(result)
                    result_map[test.name] = result
                    completed.add(test.name)
                    self._complete_test_progress(
                        progress,
                        active,
                        test.name,
                        execution_task,
                        overall_task,
                    )
                    if on_test_complete:
                        on_test_complete(result)

            ready = [
                test
                for test in tests
                if test.name not in completed
                and test.name not in running
                and all(dep in completed for dep in graph.get(test.name, []))
            ]

            if not ready and not running:
                logger.error("Dependency deadlock detected")
                break

            for test in ready:
                logger.debug("Starting test: %s", test.name)
                self._start_test_progress(progress, active, test.name)
                running[test.name] = asyncio.create_task(
                    self._run_single_test(
                        repo_path,
                        test,
                        on_output=on_output,
                    )
                )

            if running:
                done, _ = await asyncio.wait(
                    list(running.values()),
                    return_when=asyncio.FIRST_COMPLETED,
                )

                for task in done:
                    result = task.result()
                    results.append(result)
                    result_map[result.name] = result
                    completed.add(result.name)
                    running.pop(result.name, None)
                    self._complete_test_progress(
                        progress,
                        active,
                        result.name,
                        execution_task,
                        overall_task,
                    )

                    if on_test_complete:
                        on_test_complete(result)

        order = {test.name: idx for idx, test in enumerate(tests)}
        results.sort(key=lambda res: order.get(res.name, len(order)))
        return results

    async def _run_single_test(
        self,
        repo_path: Path,
        test: TestConfig,
        *,
        on_output: Optional[Callable[[str, str, str], None]] = None,
    ) -> TestResult:
        """Run a single test using the configured execution mode."""

        return await self._run_test_subprocess(repo_path, test, on_output=on_output)

    async def _run_test_subprocess(
        self,
        repo_path: Path,
        test: TestConfig,
        *,
        on_output: Optional[Callable[[str, str, str], None]] = None,
    ) -> TestResult:
        start_time = time.time()
        stdout_lines: List[str] = []
        stderr_lines: List[str] = []
        metrics: Dict[str, Any] = {"mode": self.mode}

        usage_start = self._get_resource_usage()

        try:
            process = await asyncio.create_subprocess_exec(
                "/bin/sh",
                "-c",
                test.cmd,
                cwd=str(repo_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            async def _stream(stream, buffer: List[str], stream_name: str) -> None:
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    text = line.decode("utf-8", errors="replace").rstrip()
                    buffer.append(text)
                    if on_output:
                        on_output(test.name, stream_name, text)

            stdout_task = asyncio.create_task(
                _stream(process.stdout, stdout_lines, "stdout")
            )
            stderr_task = asyncio.create_task(
                _stream(process.stderr, stderr_lines, "stderr")
            )

            try:
                exit_code = await asyncio.wait_for(process.wait(), timeout=test.timeout)
                status = TestStatus.PASSED if exit_code == 0 else TestStatus.FAILED
            except asyncio.TimeoutError:
                logger.warning("Subprocess test timeout: %s", test.name)
                process.kill()
                exit_code = -1
                status = TestStatus.TIMEOUT
            finally:
                await asyncio.gather(stdout_task, stderr_task)
                if process.returncode is None:
                    await process.wait()

            usage_end = self._get_resource_usage()

            duration_ms = int((time.time() - start_time) * 1000)
            metrics.update(self._compute_usage_delta(usage_start, usage_end))
            metrics["duration_ms"] = duration_ms
            metrics["exit_code"] = exit_code

            stdout = "\n".join(stdout_lines)
            stderr = "\n".join(stderr_lines)
            log_path = self._persist_logs(test.name, stdout, stderr, metrics)

            return TestResult(
                name=test.name,
                status=status,
                duration_ms=duration_ms,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                log_path=log_path,
                metrics=metrics,
                mode=self.mode,
            )

        except Exception as exc:
            logger.error("Error running subprocess test %s: %s", test.name, exc)
            duration_ms = int((time.time() - start_time) * 1000)
            metrics["duration_ms"] = duration_ms
            metrics["exit_code"] = -1

            stdout = "\n".join(stdout_lines)
            stderr = "\n".join(stderr_lines)
            log_path = self._persist_logs(test.name, stdout, stderr, metrics)

            return TestResult(
                name=test.name,
                status=TestStatus.ERROR,
                duration_ms=duration_ms,
                exit_code=-1,
                stdout=stdout,
                stderr=stderr,
                error=str(exc),
                log_path=log_path,
                metrics=metrics,
                mode=self.mode,
            )

    def _build_dependency_graph(self, tests: List[TestConfig]) -> Dict[str, List[str]]:
        """Build dependency graph from test configurations."""

        return {test.name: list(test.depends_on) for test in tests}

    def _resolve_execution_order(self, tests: List[TestConfig]) -> List[TestConfig]:
        """Topologically sort tests based on dependencies."""

        graph = self._build_dependency_graph(tests)
        lookup = {test.name: test for test in tests}
        ordered: List[TestConfig] = []
        temporary = set()
        permanent = set()

        def visit(name: str) -> None:
            if name in permanent:
                return
            if name in temporary:
                raise TestOrchestratorError(f"Circular dependency detected: {name}")

            temporary.add(name)
            for dep in graph.get(name, []):
                if dep not in lookup:
                    raise TestOrchestratorError(
                        f"Test '{name}' depends on unknown test '{dep}'"
                    )
                visit(dep)
            temporary.remove(name)
            permanent.add(name)
            ordered.append(lookup[name])

        for test in tests:
            if test.name not in permanent:
                visit(test.name)

        seen = set()
        deduped: List[TestConfig] = []
        for test in ordered:
            if test.name not in seen:
                deduped.append(test)
                seen.add(test.name)
        return deduped

    def _blocked_dependencies(
        self,
        test: TestConfig,
        result_map: Dict[str, TestResult],
    ) -> List[TestResult]:
        blocked: List[TestResult] = []
        for dep in test.depends_on:
            dep_result = result_map.get(dep)
            if dep_result and dep_result.status != TestStatus.PASSED:
                blocked.append(dep_result)
        return blocked

    def _create_skipped_result(
        self,
        test: TestConfig,
        blocked_results: List[TestResult],
    ) -> TestResult:
        reason = ", ".join(
            f"{res.name} ({res.status.value})" for res in blocked_results
        )
        message = f"Skipped due to dependency failure: {reason}"
        metrics = {"mode": self.mode, "duration_ms": 0, "exit_code": -1}
        log_path = self._persist_logs(test.name, "", message, metrics)
        logger.info("Skipping test %s due to failed dependencies", test.name)
        return TestResult(
            name=test.name,
            status=TestStatus.SKIPPED,
            duration_ms=0,
            exit_code=-1,
            stdout="",
            stderr=message,
            error=message,
            log_path=log_path,
            metrics=metrics,
            mode=self.mode,
        )

    def _persist_logs(
        self,
        test_name: str,
        stdout: str,
        stderr: str,
        metrics: Dict[str, Any],
    ) -> Path:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        safe_name = re.sub(r"[^a-zA-Z0-9_.-]+", "-", test_name).strip("-") or "test"
        log_path = self.log_dir / f"{timestamp}_{safe_name}.log"
        try:
            with open(log_path, "w", encoding="utf-8") as handle:
                handle.write("# Solo Git Test Run\n")
                handle.write(f"name: {test_name}\n")
                handle.write(f"mode: {self.mode}\n")
                handle.write(f"metrics: {metrics}\n")
                handle.write("\n[stdout]\n")
                handle.write(stdout)
                handle.write("\n\n[stderr]\n")
                handle.write(stderr)
        except Exception as exc:  # pragma: no cover - filesystem best effort
            logger.warning("Failed to persist logs for %s: %s", test_name, exc)
        return log_path

    def _get_resource_usage(self) -> Optional[Any]:
        if resource is None:  # pragma: no cover - platform dependent
            return None
        return resource.getrusage(resource.RUSAGE_CHILDREN)

    def _compute_usage_delta(
        self,
        start_usage: Optional[Any],
        end_usage: Optional[Any],
    ) -> Dict[str, Any]:
        if not start_usage or not end_usage:
            return {}

        return {
            "user_cpu_seconds": max(0.0, end_usage.ru_utime - start_usage.ru_utime),
            "system_cpu_seconds": max(0.0, end_usage.ru_stime - start_usage.ru_stime),
            "max_rss_kb": end_usage.ru_maxrss,
            "io_read_ops": max(0, end_usage.ru_inblock - start_usage.ru_inblock),
            "io_write_ops": max(0, end_usage.ru_oublock - start_usage.ru_oublock),
        }

    def all_tests_passed(self, results: List[TestResult]) -> bool:
        """Check if all tests passed."""

        return all(result.status == TestStatus.PASSED for result in results)

    def get_summary(self, results: List[TestResult]) -> dict:
        """Get test results summary."""

        return {
            "total": len(results),
            "passed": sum(1 for r in results if r.status == TestStatus.PASSED),
            "failed": sum(1 for r in results if r.status == TestStatus.FAILED),
            "timeout": sum(1 for r in results if r.status == TestStatus.TIMEOUT),
            "error": sum(1 for r in results if r.status == TestStatus.ERROR),
            "skipped": sum(1 for r in results if r.status == TestStatus.SKIPPED),
            "status": "green" if self.all_tests_passed(results) else "red",
        }
