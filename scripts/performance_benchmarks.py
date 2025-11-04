#!/usr/bin/env python3
"""Solo Git performance benchmarking utilities.

This script exercises several parts of the Solo Git stack using
synthetic repositories and lightweight simulated workloads.  The
results are written to both a temporary directory (for ad-hoc
inspection) and to ``docs/performance_results.json`` inside the
repository so they can be committed or compared over time.

The benchmark intentionally avoids calling any external AI services so
that it can run in disconnected development environments.  When the
full AI orchestration stack is configured locally the real
:class:`~sologit.orchestration.ai_orchestrator.AIOrchestrator` can be
used instead by passing ``--use-real-ai``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import platform
import random
import shutil
import statistics
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from git import Repo

CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parent

if str(REPO_ROOT) not in os.sys.path:
    os.sys.path.insert(0, str(REPO_ROOT))

from sologit.engines.git_engine import GitEngine  # noqa: E402
from sologit.engines.test_orchestrator import (  # noqa: E402
    TestConfig,
    TestOrchestrator,
    TestExecutionMode,
)
from sologit.orchestration.ai_orchestrator import (  # noqa: E402
    AIOrchestrator,
    PlanResponse,
    PatchResponse,
    ReviewResponse,
)
from sologit.orchestration.model_router import ComplexityMetrics  # noqa: E402
from sologit.orchestration.planning_engine import CodePlan, FileChange  # noqa: E402
from sologit.orchestration.code_generator import GeneratedPatch  # noqa: E402
from sologit.state.manager import JSONStateBackend, StateManager  # noqa: E402

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


@dataclass(frozen=True)
class RepoSpec:
    """Specification for synthetic repositories."""

    name: str
    files: int
    commits: int


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def create_synthetic_repo(base_dir: Path, spec: RepoSpec) -> Path:
    """Create a synthetic git repository with the requested size."""

    repo_dir = base_dir / spec.name
    repo_dir.mkdir(parents=True, exist_ok=True)
    repo = Repo.init(repo_dir)

    # Seed files
    for i in range(spec.files):
        file_path = repo_dir / f"src/file_{i:04d}.txt"
        _write_file(file_path, f"Synthetic content for file {i}\n")

    files_to_add = [
        str(p.relative_to(repo_dir))
        for p in repo_dir.rglob("*")
        if p.is_file() and ".git" not in p.parts
    ]
    repo.index.add(files_to_add)
    repo.index.commit("Initial commit")

    # Generate additional commits (mostly empty for performance)
    remaining_commits = max(spec.commits - 1, 0)
    if remaining_commits > 0:
        parent_commit = repo.head.commit.hexsha
        timestamp = int(time.time())
        process = subprocess.Popen(
            ["git", "fast-import"],
            cwd=str(repo_dir),
            stdin=subprocess.PIPE,
            text=True,
        )
        assert process.stdin is not None

        for commit_index in range(remaining_commits):
            message = f"Synthetic commit {commit_index}"
            process.stdin.write("commit refs/heads/main\n")
            process.stdin.write(f"mark :{commit_index + 1}\n")
            process.stdin.write(
                "committer Benchmark <bench@solo.git> "
                f"{timestamp + commit_index} +0000\n"
            )
            process.stdin.write(f"data {len(message)}\n{message}\n")

            if commit_index == 0:
                process.stdin.write(f"from {parent_commit}\n")
            else:
                process.stdin.write(f"from :{commit_index}\n")

            process.stdin.write("M 100644 inline src/file_0000.txt\n")
            content = f"Synthetic content version {commit_index}\n"
            process.stdin.write(f"data {len(content)}\n{content}\n")

        process.stdin.write("done\n")
        process.stdin.flush()
        process.stdin.close()
        return_code = process.wait()
        if return_code != 0:
            raise RuntimeError(f"git fast-import exited with {return_code}")

    return repo_dir


def benchmark_repo_initialization(base_dir: Path, specs: Iterable[RepoSpec]) -> Tuple[GitEngine, Dict[str, Any]]:
    """Benchmark repository initialization times."""

    engine_dir = base_dir / "engine"
    engine = GitEngine(data_dir=engine_dir)

    results: List[Dict[str, Any]] = []
    repo_ids: Dict[str, str] = {}

    for spec in specs:
        source_repo = create_synthetic_repo(base_dir / "sources", spec)
        start = time.perf_counter()
        repo_id = engine.init_from_git(str(source_repo), name=f"bench-{spec.name}")
        duration = time.perf_counter() - start
        repo_ids[spec.name] = repo_id
        results.append(
            {
                "label": spec.name,
                "files": spec.files,
                "commits": spec.commits,
                "init_time_seconds": duration,
            }
        )

    return engine, {"measurements": results, "repo_ids": repo_ids}


def benchmark_workpads(engine: GitEngine, repo_id: str, count: int = 60) -> Dict[str, Any]:
    """Benchmark workpad creation performance."""

    if count <= 0:
        return {"count": 0, "average_seconds": 0.0, "p95_seconds": 0.0, "max_seconds": 0.0, "workpad_ids": []}

    durations: List[float] = []
    workpad_ids: List[str] = []

    for index in range(count):
        title = f"Benchmark Pad {index:02d}"
        start = time.perf_counter()
        pad_id = engine.create_workpad(repo_id, title)
        durations.append(time.perf_counter() - start)
        workpad_ids.append(pad_id)

    sorted_durations = sorted(durations)
    p95_index = min(len(sorted_durations) - 1, int(0.95 * len(sorted_durations)))

    return {
        "count": count,
        "average_seconds": statistics.mean(durations),
        "p95_seconds": sorted_durations[p95_index],
        "max_seconds": max(durations),
        "workpad_ids": workpad_ids,
    }


def _build_test_configs(count: int, sleep: float = 0.02) -> List[TestConfig]:
    return [
        TestConfig(
            name=f"noop_{i}",
            cmd=f"python -c \"import time; time.sleep({sleep})\"",
            timeout=30,
        )
        for i in range(count)
    ]


def benchmark_test_execution(engine: GitEngine, repo_id: str) -> Dict[str, Any]:
    """Benchmark test execution in sandboxed vs non-sandboxed modes."""

    orchestrator = TestOrchestrator(
        git_engine=engine,
        execution_mode=TestExecutionMode.SUBPROCESS.value,
    )

    pad_id = engine.create_workpad(repo_id, "Test Runner Pad")

    tests_fast = _build_test_configs(10, sleep=0.01)
    tests_heavy = _build_test_configs(20, sleep=0.02)

    # Non-sandboxed (direct subprocess)
    start = time.perf_counter()
    orchestrator.run_tests_sync(pad_id, tests_fast, parallel=False)
    fast_duration = time.perf_counter() - start

    start = time.perf_counter()
    orchestrator.run_tests_sync(pad_id, tests_heavy, parallel=True)
    parallel_duration = time.perf_counter() - start

    repo_path = engine.get_repo(repo_id).path
    sandbox_duration = _simulate_sandboxed_tests(repo_path, tests_heavy)

    return {
        "non_sandboxed_serial_seconds": fast_duration,
        "non_sandboxed_parallel_seconds": parallel_duration,
        "simulated_sandbox_seconds": sandbox_duration,
        "test_counts": {
            "serial": len(tests_fast),
            "parallel": len(tests_heavy),
        },
    }


def _simulate_sandboxed_tests(repo_path: Path, tests: Iterable[TestConfig]) -> float:
    with tempfile.TemporaryDirectory() as tmpdir:
        sandbox_repo = Path(tmpdir) / "repo"
        shutil.copytree(repo_path, sandbox_repo)
        start = time.perf_counter()
        for test in tests:
            completed = subprocess.run(
                ["/bin/sh", "-c", test.cmd],
                cwd=str(sandbox_repo),
                check=True,
                capture_output=True,
            )
            if completed.returncode != 0:
                raise RuntimeError(f"Sandboxed test {test.name} failed with exit code {completed.returncode}")
        return time.perf_counter() - start


def _generate_mock_plan(prompt: str) -> CodePlan:
    return CodePlan(
        title=f"Plan for {prompt[:20]}",
        description="Mock plan for benchmarking",
        file_changes=[
            FileChange(path="sologit/core/module.py", action="modify", reason="benchmark"),
        ],
        test_strategy="Run unit tests",
        risks=["Benchmark risk"],
    )


def _generate_mock_patch(plan: CodePlan) -> GeneratedPatch:
    diff = """--- a/sologit/core/module.py
+++ b/sologit/core/module.py
@@
-# benchmark
+# benchmark update
""".strip()
    return GeneratedPatch(
        diff=diff,
        files_changed=["sologit/core/module.py"],
        additions=1,
        deletions=1,
        model="benchmark",
    )


class _MockAIOrchestrator:
    """Offline-friendly stand-in for :class:`AIOrchestrator`."""

    def __init__(self) -> None:
        self.random = random.Random(42)

    def _simulate_latency(self, base: float = 0.05, jitter: float = 0.02) -> float:
        duration = base + self.random.random() * jitter
        time.sleep(duration)
        return duration

    def plan(self, prompt: str, force_model: Optional[str] = None, **_: Any) -> PlanResponse:
        self._simulate_latency(0.06, 0.04)
        return PlanResponse(
            plan=_generate_mock_plan(prompt),
            model_used=force_model or "mock-planner",
            tokens_used=0,
            cost_usd=0.0,
            complexity=ComplexityMetrics(
                score=0.25,
                security_sensitive=False,
                estimated_patch_size=10,
                file_count=1,
                has_tests=True,
                requires_architecture=False,
            ),
        )

    def generate_patch(self, plan: CodePlan, force_model: Optional[str] = None, **_: Any) -> PatchResponse:
        self._simulate_latency(0.08, 0.05)
        return PatchResponse(
            patch=_generate_mock_patch(plan),
            model_used=force_model or "mock-coder",
            cost_usd=0.0,
        )

    def review_patch(self, patch: GeneratedPatch, **_: Any) -> ReviewResponse:
        self._simulate_latency(0.04, 0.03)
        return ReviewResponse(
            approved=True,
            issues=[],
            suggestions=["Looks good"],
            model_used="mock-reviewer",
            cost_usd=0.0,
        )


def _create_ai_orchestrator(use_real: bool) -> Tuple[Any, str]:
    if not use_real:
        return _MockAIOrchestrator(), "mock"

    try:
        orchestrator = AIOrchestrator()
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.warning("Falling back to mock AI orchestrator: %s", exc)
        return _MockAIOrchestrator(), "mock"

    api_key = getattr(getattr(orchestrator, "client", None), "api_key", None)
    if not api_key:
        logger.info("AI API key not configured; using offline mock orchestrator")
        return _MockAIOrchestrator(), "mock"

    return orchestrator, "real"


def benchmark_ai_operations(concurrency: int = 12, use_real_orchestrator: bool = False) -> Dict[str, Any]:
    orchestrator, mode = _create_ai_orchestrator(use_real_orchestrator)

    prompts = [
        "Fix typos in documentation",
        "Add API endpoint for batch commits",
        "Implement distributed caching layer with metrics",
        "Refactor UI rendering pipeline",
    ]

    sequential_timings: Dict[str, float] = {}
    model_prompts = [
        ("llama-3.1-8b-instruct", prompts[0]),
        ("gpt-4o", prompts[2]),
        ("deepseek-coder-33b", prompts[1]),
        ("codellama-70b-instruct", prompts[3]),
    ]

    for model_name, prompt in model_prompts:
        start = time.perf_counter()
        orchestrator.plan(prompt, force_model=model_name)
        sequential_timings[f"plan_{model_name}"] = time.perf_counter() - start

    plan = _generate_mock_plan(prompts[1])
    for model_name in ["deepseek-coder-33b", "codellama-70b-instruct"]:
        start = time.perf_counter()
        orchestrator.generate_patch(plan, force_model=model_name)
        sequential_timings[f"patch_{model_name}"] = time.perf_counter() - start

    patch = _generate_mock_patch(plan)
    start = time.perf_counter()
    orchestrator.review_patch(patch)
    sequential_timings["review_planning-tier"] = time.perf_counter() - start

    durations: List[float] = []

    def run_parallel(prompt: str) -> float:
        local_orchestrator, _ = _create_ai_orchestrator(use_real_orchestrator)
        start_time = time.perf_counter()
        local_orchestrator.plan(prompt)
        return time.perf_counter() - start_time

    worker_count = max(1, concurrency)
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = [executor.submit(run_parallel, random.choice(prompts)) for _ in range(worker_count)]
        for future in as_completed(futures):
            durations.append(future.result())

    return {
        "mode": mode,
        "sequential_seconds": sequential_timings,
        "concurrency": worker_count,
        "concurrent_average_seconds": statistics.mean(durations) if durations else 0.0,
        "concurrent_max_seconds": max(durations) if durations else 0.0,
    }


def benchmark_state_io(state_dir: Path, count: int = 500) -> Dict[str, Any]:
    backend = JSONStateBackend(state_dir)
    manager = StateManager(backend=backend)

    repo_id = "repo-benchmark"
    manager.create_repository(repo_id, "Benchmark Repo", str(state_dir / "repo"))

    start_write = time.perf_counter()
    for index in range(count):
        workpad_id = f"pad-{index:05d}"
        manager.create_workpad(
            workpad_id=workpad_id,
            repo_id=repo_id,
            title=f"Pad {index}",
            branch_name=f"pads/pad-{index:05d}",
            base_commit="main",
        )
        manager.create_test_run(workpad_id, "fast")
        manager.create_ai_operation(workpad_id, "plan", "gpt-4o", "benchmark")

    write_duration = time.perf_counter() - start_write

    start_read = time.perf_counter()
    workpads = manager.list_workpads(repo_id)
    tests = manager.list_test_runs()
    ai_ops = manager.list_ai_operations()
    read_duration = time.perf_counter() - start_read

    events = manager.get_events(limit=count * 3)

    return {
        "records": {
            "workpads": len(workpads),
            "test_runs": len(tests),
            "ai_operations": len(ai_ops),
            "events": len(events),
        },
        "write_seconds": write_duration,
        "read_seconds": read_duration,
        "state_dir": str(state_dir),
    }


async def _measure_gui_render(state_dir: Path, engine_dir: Path) -> float:
    from sologit.ui.enhanced_tui import HeavenTUI
    from sologit.ui.enhanced_tui import (
        CommitGraphWidget,
        WorkpadStatusWidget,
        AIActivityWidget,
        TestOutputWidget,
    )
    from textual.widgets import Header, Footer, Log

    class BenchmarkCommitGraphWidget(CommitGraphWidget):
        def __init__(self, git_sync, widget_id: Optional[str] = None):
            super().__init__(git_sync)
            if widget_id:
                self.id = widget_id

    class BenchmarkWorkpadStatusWidget(WorkpadStatusWidget):
        def __init__(self, git_sync, widget_id: Optional[str] = None):
            super().__init__(git_sync)
            if widget_id:
                self.id = widget_id

    class BenchmarkAIActivityWidget(AIActivityWidget):
        def __init__(self, git_sync, widget_id: Optional[str] = None):
            super().__init__(git_sync)
            if widget_id:
                self.id = widget_id

    class BenchmarkTestOutputWidget(TestOutputWidget):
        def __init__(self, widget_id: Optional[str] = None):
            Log.__init__(self, highlight=True)
            self.test_run_id = None
            if widget_id:
                self.id = widget_id

    class BenchmarkHeavenTUI(HeavenTUI):
        def __init__(self) -> None:
            super().__init__()
            from sologit.state.git_sync import GitStateSync

            self.git_sync = GitStateSync(
                state_dir=state_dir,
                data_dir=engine_dir,
            )

        def compose(self):  # type: ignore[override]
            yield Header()
            yield BenchmarkCommitGraphWidget(self.git_sync, widget_id="commit-graph")
            yield BenchmarkWorkpadStatusWidget(self.git_sync, widget_id="workpad-status")
            yield BenchmarkAIActivityWidget(self.git_sync, widget_id="ai-activity")
            yield BenchmarkTestOutputWidget(widget_id="test-output")
            yield Footer()

    app = BenchmarkHeavenTUI()
    start = time.perf_counter()
    async with app.run_test() as pilot:
        await pilot.pause()
    return time.perf_counter() - start


def benchmark_gui(state_dir: Path, engine_dir: Path) -> Dict[str, Any]:
    try:
        duration = asyncio.run(_measure_gui_render(state_dir, engine_dir))
    except Exception as exc:  # pragma: no cover - depends on terminal capabilities
        logger.warning("GUI benchmark unavailable: %s", exc)
        return {"initial_render_seconds": None, "error": str(exc)}

    return {"initial_render_seconds": duration}


def gather_environment() -> Dict[str, Any]:
    return {
        "python": platform.python_version(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor(),
    }


def run_benchmarks(use_real_ai: bool) -> Dict[str, Any]:
    base_dir = Path(tempfile.mkdtemp(prefix="sologit-bench-"))
    logger.info("Created temporary benchmark directory: %s", base_dir)
    try:
        specs = [
            RepoSpec("small", files=120, commits=200),
            RepoSpec("medium", files=600, commits=2000),
            RepoSpec("large", files=1200, commits=10000),
        ]

        engine, repo_info = benchmark_repo_initialization(base_dir, specs)
        repo_ids = repo_info.pop("repo_ids")

        large_repo_id = repo_ids["large"]

        workpad_metrics = benchmark_workpads(engine, large_repo_id, count=60)
        test_metrics = benchmark_test_execution(engine, large_repo_id)
        ai_metrics = benchmark_ai_operations(use_real_orchestrator=use_real_ai)
        state_metrics = benchmark_state_io(base_dir / "state", count=300)
        gui_metrics = benchmark_gui(base_dir / "state", base_dir / "engine")
        results = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "environment": gather_environment(),
            "repo_initialization": repo_info,
            "workpads": workpad_metrics,
            "tests": test_metrics,
            "ai": ai_metrics,
            "state": state_metrics,
            "gui": gui_metrics,
        }

        output_path = base_dir / "performance_results.json"
        output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

        repo_output = REPO_ROOT / "docs" / "performance_results.json"
        repo_output.parent.mkdir(parents=True, exist_ok=True)
        repo_output.write_text(json.dumps(results, indent=2), encoding="utf-8")

        print(json.dumps(results, indent=2))
        print(f"\nResults written to {output_path} and {repo_output}")

        return results

    finally:
        shutil.rmtree(base_dir, ignore_errors=True)
        logger.info("Cleaned up temporary benchmark directory")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Solo Git performance benchmarks")
    parser.add_argument(
        "--use-real-ai",
        action="store_true",
        help="Use the configured AI orchestrator instead of the offline mock",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)
    run_benchmarks(use_real_ai=args.use_real_ai)


if __name__ == "__main__":
    main()
