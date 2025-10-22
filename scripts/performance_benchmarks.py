#!/usr/bin/env python3
"""Solo Git performance benchmarking utilities."""

from __future__ import annotations

import asyncio
import json
import os
import platform
import random
import shutil
import shlex
import statistics
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from git import Repo

CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parent
if str(REPO_ROOT) not in os.sys.path:
    os.sys.path.insert(0, str(REPO_ROOT))

from sologit.engines.git_engine import GitEngine
from sologit.engines.test_orchestrator import TestConfig, TestOrchestrator
from sologit.orchestration.ai_orchestrator import AIOrchestrator
from sologit.orchestration.planning_engine import CodePlan, FileChange
from sologit.orchestration.code_generator import GeneratedPatch
from sologit.state.manager import JSONStateBackend, StateManager
from sologit.ui.enhanced_tui import HeavenTUI


@dataclass
class RepoSpec:
    """Specification for synthetic repositories."""

    name: str
    files: int
    commits: int


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


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
        process.wait()

    return repo_dir


def benchmark_repo_initialization(base_dir: Path, specs: List[RepoSpec]) -> Tuple[GitEngine, Dict[str, Any]]:
    """Benchmark repository initialization times."""

    engine_dir = base_dir / "engine"
    engine = GitEngine(data_dir=engine_dir)

    results: List[Dict[str, Any]] = []
    repo_ids: Dict[str, str] = {}

    for spec in specs:
        source_repo = create_synthetic_repo(base_dir / "sources", spec)
        start = time.perf_counter()
        repo_id = engine.init_from_git(str(source_repo))
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


def _simulate_sandboxed_tests(repo_path: Path, tests: List[TestConfig]) -> float:
    with tempfile.TemporaryDirectory() as tmpdir:
        sandbox_repo = Path(tmpdir) / "repo"
        shutil.copytree(repo_path, sandbox_repo)
        start = time.perf_counter()
        for test in tests:
            try:
                cmd_args = shlex.split(test.cmd)
            except ValueError as exc:  # pragma: no cover - defensive programming
                raise ValueError(f"Invalid command for test '{test.name}': {exc}") from exc

            subprocess.run(
                cmd_args,
                cwd=str(sandbox_repo),
                check=True,
                capture_output=True,
            )
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


def benchmark_ai_operations(concurrency: int = 12) -> Dict[str, Any]:
    prompts = [
        "Fix typos in documentation",
        "Add API endpoint for batch commits",
        "Implement distributed caching layer with metrics",
        "Refactor UI rendering pipeline",
    ]

    sequential_timings: Dict[str, float] = {}
    orchestrator = AIOrchestrator()

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

    def run_parallel(prompt: str) -> float:
        local_orchestrator = AIOrchestrator()
        start_time = time.perf_counter()
        local_orchestrator.plan(prompt)
        return time.perf_counter() - start_time

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(run_parallel, random.choice(prompts)) for _ in range(concurrency)]
        durations = [future.result() for future in as_completed(futures)]

    return {
        "sequential_seconds": sequential_timings,
        "concurrency": concurrency,
        "concurrent_average_seconds": statistics.mean(durations),
        "concurrent_max_seconds": max(durations),
    }


def benchmark_state_io(state_dir: Path, count: int = 500) -> Dict[str, Any]:
    backend = JSONStateBackend(state_dir)
    manager = StateManager(backend=backend)

    repo_id = "repo-benchmark"
    manager.create_repository(repo_id, "Benchmark Repo", str(state_dir / "repo"))

    workpad_ids: List[str] = []
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
        workpad_ids.append(workpad_id)

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
    from sologit.ui.enhanced_tui import (
        CommitGraphWidget,
        WorkpadStatusWidget,
        AIActivityWidget,
        TestOutputWidget,
    )
    from textual.widgets import Header, Footer, Log

    class BenchmarkCommitGraphWidget(CommitGraphWidget):
        def __init__(self, git_sync, widget_id: str | None = None):
            super().__init__(git_sync)
            if widget_id:
                self.id = widget_id

    class BenchmarkWorkpadStatusWidget(WorkpadStatusWidget):
        def __init__(self, git_sync, widget_id: str | None = None):
            super().__init__(git_sync)
            if widget_id:
                self.id = widget_id

    class BenchmarkAIActivityWidget(AIActivityWidget):
        def __init__(self, git_sync, widget_id: str | None = None):
            super().__init__(git_sync)
            if widget_id:
                self.id = widget_id

    class BenchmarkTestOutputWidget(TestOutputWidget):
        def __init__(self, widget_id: str | None = None):
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

        def compose(self):
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
    return {"initial_render_seconds": asyncio.run(_measure_gui_render(state_dir, engine_dir))}


def gather_environment() -> Dict[str, Any]:
    return {
        "python": platform.python_version(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor(),
    }


def main() -> None:
    base_dir = Path(tempfile.mkdtemp(prefix="sologit-bench-"))
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
        ai_metrics = benchmark_ai_operations()
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
        output_path.write_text(json.dumps(results, indent=2))

        repo_output = REPO_ROOT / "docs" / "performance_results.json"
        repo_output.parent.mkdir(parents=True, exist_ok=True)
        repo_output.write_text(json.dumps(results, indent=2))

        print(json.dumps(results, indent=2))
        print(f"\nResults written to {output_path} and {repo_output}")

    finally:
        shutil.rmtree(base_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
