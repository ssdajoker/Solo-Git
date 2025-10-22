"""Comprehensive end-to-end workflow tests using real git operations."""

from __future__ import annotations

import difflib
import json
from io import BytesIO
from pathlib import Path
from typing import Callable, Iterable
from zipfile import ZipFile

import pytest

from git import Repo

from sologit.state.git_sync import GitStateSync
from sologit.state.manager import JSONStateBackend
from sologit.engines.patch_engine import PatchEngine
from sologit.engines.test_orchestrator import (
    TestConfig,
    TestOrchestrator,
    TestStatus,
    TestResult,
)
from sologit.analysis.test_analyzer import TestAnalyzer, TestAnalysis
from sologit.orchestration.ai_orchestrator import AIOrchestrator
from sologit.orchestration.planning_engine import FileChange
from sologit.config.manager import ConfigManager
from sologit.workflows.ci_orchestrator import CIOrchestrator, CIStatus
from sologit.workflows.rollback_handler import RollbackHandler
from sologit.workflows.promotion_gate import (
    PromotionDecisionType,
    PromotionGate,
    PromotionRules,
)
from sologit.engines.git_engine import CannotPromoteError


@pytest.fixture
def sample_project_zip() -> bytes:
    """Create a small Python project archive used by the workflows."""
    buffer = BytesIO()
    with ZipFile(buffer, "w") as zf:
        zf.writestr(
            "hello.py",
            """def greet(name):
    \"\"\"Say hello to someone.\"\"\"
    return f\"Hello, {name}!\"


if __name__ == \"__main__\":
    print(greet(\"World\"))
""",
        )
        zf.writestr(
            "tests/__init__.py",
            "",
        )
        zf.writestr(
            "tests/test_hello.py",
            """from hello import greet


def test_greet_known_names():
    assert greet(\"Alice\") == \"Hello, Alice!\"
    assert greet(\"Bob\") == \"Hello, Bob!\"
""",
        )
        zf.writestr(
            "README.md",
            """# Sample Project

This repository is used for Solo Git E2E workflow tests.
""",
        )
    buffer.seek(0)
    return buffer.read()


@pytest.fixture
def git_sync(tmp_path_factory) -> GitStateSync:
    """Provide a GitStateSync instance backed by temporary directories."""
    base = tmp_path_factory.mktemp("solo_git_data")
    data_dir = base / "git"
    state_dir = base / "state"
    return GitStateSync(state_dir=state_dir, data_dir=data_dir)


@pytest.fixture
def patch_engine(git_sync: GitStateSync) -> PatchEngine:
    return PatchEngine(git_sync.git_engine)


@pytest.fixture
def test_runner(git_sync: GitStateSync, tmp_path_factory) -> TestOrchestrator:
    log_dir = tmp_path_factory.mktemp("logs")
    return TestOrchestrator(
        git_sync.git_engine,
        execution_mode="subprocess",
        log_dir=log_dir,
    )


@pytest.fixture
def ai_config_manager(tmp_path) -> ConfigManager:
    """Create a minimal configuration file for AI orchestrator tests."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
abacus:
  endpoint: "https://api.abacus.ai/api/v0"
  api_key: "test_key"

ai:
  models:
    fast:
      primary: "llama-3.1-8b-instruct"
      max_tokens: 1024
      temperature: 0.1
    coding:
      primary: "deepseek-coder-33b"
      max_tokens: 2048
      temperature: 0.1
    planning:
      primary: "gpt-4o"
      max_tokens: 4096
      temperature: 0.2

escalation:
  triggers: []

budget:
  daily_usd_cap: 5.0
  alert_threshold: 0.8
  track_by_model: true

promote_on_green: true
rollback_on_ci_red: true
"""
    )
    return ConfigManager(config_path=config_file)


@pytest.fixture
def ai_orchestrator(ai_config_manager: ConfigManager, tmp_path) -> AIOrchestrator:
    orchestrator = AIOrchestrator(ai_config_manager)
    # Ensure isolated budget tracking between tests
    from sologit.orchestration.cost_guard import CostTracker

    orchestrator.cost_guard.tracker = CostTracker(tmp_path / "usage.json")
    return orchestrator


def _generate_modify_patch(
    repo_path: Path, rel_path: str, transform: Callable[[str], str]
) -> str:
    original = (repo_path / rel_path).read_text()
    updated = transform(original)
    if not updated.endswith("\n"):
        updated += "\n"
    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        updated.splitlines(keepends=True),
        fromfile=f"a/{rel_path}",
        tofile=f"b/{rel_path}",
    )
    return "".join(diff)


def _generate_create_patch(rel_path: str, content: str) -> str:
    if not content.endswith("\n"):
        content += "\n"
    lines = content.splitlines(keepends=True)
    header = [
        "--- /dev/null\n",
        f"+++ b/{rel_path}\n",
        f"@@ -0,0 +{len(lines)} @@\n",
    ]
    body = [f"+{line}" for line in lines]
    return "".join(header + body)


def _diff_from_strings(original: str, updated: str, rel_path: str) -> str:
    if not original.endswith("\n"):
        original += "\n"
    if not updated.endswith("\n"):
        updated += "\n"
    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        updated.splitlines(keepends=True),
        fromfile=f"a/{rel_path}",
        tofile=f"b/{rel_path}",
    )
    return "".join(diff)


def _run_pytest_and_record(
    git_sync: GitStateSync,
    orchestrator: TestOrchestrator,
    pad_id: str,
    command: str = "pytest",
) -> tuple[dict, list[TestResult]]:
    run = git_sync.create_test_run(pad_id, target=command)
    results = orchestrator.run_tests_sync(
        pad_id,
        [TestConfig(name=command, cmd=command, timeout=60)],
        parallel=False,
    )
    all_green = all(result.status == TestStatus.PASSED for result in results)
    status = "passed" if all_green else "failed"
    exit_code = 0 if all_green else 1
    combined_output = "\n".join(result.stdout for result in results if result.stdout)
    git_sync.update_test_run(run["run_id"], status=status, output=combined_output, exit_code=exit_code)
    return run, results

def _analysis_from_results(results: Iterable[TestResult]) -> TestAnalysis:
    analyzer = TestAnalyzer()
    return analyzer.analyze(list(results))

def test_full_ai_pipeline_end_to_end(
    git_sync: GitStateSync,
    sample_project_zip: bytes,
    ai_orchestrator: AIOrchestrator,
    test_runner: TestOrchestrator,
):
    """Run the full AI-driven workflow from prompt to auto-merge."""
    repo_info = git_sync.init_repo_from_zip(sample_project_zip, "Sample App")
    repo_id = repo_info["repo_id"]
    pad_info = git_sync.create_workpad(repo_id, "AI generated documentation")
    pad_id = pad_info["workpad_id"]

    plan = ai_orchestrator.plan("Document Solo Git workflows for developers")
    # Focus plan on creating a documentation file inside the repo
    plan.plan.file_changes = [
        FileChange(
            path="docs/DEVELOPER_NOTES.md",
            action="create",
            reason="Document the tested workflow",
            estimated_lines=8,
        )
    ]
    patch_response = ai_orchestrator.generate_patch(plan.plan)
    assert patch_response.patch.diff

    doc_content = (
        "# Developer Notes\n\n"
        f"Generated plan: {plan.plan.title}\n"
        "This file captures the AI-assisted workflow.\n"
    )
    diff = _generate_create_patch("docs/DEVELOPER_NOTES.md", doc_content)
    git_sync.apply_patch(pad_id, diff, "Add developer notes")

    _, results = _run_pytest_and_record(git_sync, test_runner, pad_id)
    analysis = _analysis_from_results(results)
    assert analysis.status == "green"

    gate = PromotionGate(git_sync.git_engine)
    decision = gate.evaluate(pad_id, analysis)
    assert decision.decision == PromotionDecisionType.APPROVE

    merge_commit = git_sync.promote_workpad(pad_id)
    assert len(merge_commit) == 40

    repo_path = Path(repo_info["path"])
    doc_path = repo_path / "docs" / "DEVELOPER_NOTES.md"
    assert doc_path.exists()

    state_workpad = git_sync.state_manager.get_workpad(pad_id)
    assert state_workpad is not None
    assert state_workpad.status == "promoted"


def test_failure_workflow_analyze_and_fix(
    git_sync: GitStateSync,
    sample_project_zip: bytes,
    test_runner: TestOrchestrator,
):
    """Verify failure analysis and retest loop for a broken change."""
    repo_info = git_sync.init_repo_from_zip(sample_project_zip, "Sample App")
    repo_id = repo_info["repo_id"]
    pad = git_sync.create_workpad(repo_id, "Introduce greeting regression")
    pad_id = pad["workpad_id"]
    repo_path = Path(repo_info["path"])

    regression_patch = _generate_modify_patch(
        repo_path,
        "hello.py",
        lambda original: original.replace(
            "    return f\"Hello, {name}!\"\n",
            "    return f\"Hi, {name}!\"\n",
        ),
    )
    git_sync.apply_patch(pad_id, regression_patch, "Introduce regression")

    _, failed_results = _run_pytest_and_record(git_sync, test_runner, pad_id)
    assert any(result.status == TestStatus.FAILED for result in failed_results)
    analysis = _analysis_from_results(failed_results)
    assert analysis.status == "red"

    workpad = git_sync.git_engine.get_workpad(pad_id)
    assert workpad is not None
    assert workpad.test_status == "red"

    fix_patch = _generate_modify_patch(
        repo_path,
        "hello.py",
        lambda original: original.replace(
            "    return f\"Hi, {name}!\"\n",
            "    return f\"Hello, {name}!\"\n",
        ),
    )
    git_sync.apply_patch(pad_id, fix_patch, "Restore greeting")

    _, passed_results = _run_pytest_and_record(git_sync, test_runner, pad_id)
    assert all(result.status == TestStatus.PASSED for result in passed_results)
    analysis = _analysis_from_results(passed_results)
    assert analysis.status == "green"
    updated_workpad = git_sync.git_engine.get_workpad(pad_id)
    assert updated_workpad is not None
    assert updated_workpad.test_status == "green"


def test_ci_failure_triggers_rollback(
    git_sync: GitStateSync,
    sample_project_zip: bytes,
    test_runner: TestOrchestrator,
):
    """Ensure CI failure causes rollback and creates a fix workpad."""
    repo_info = git_sync.init_repo_from_zip(sample_project_zip, "Sample App")
    repo_id = repo_info["repo_id"]
    repo_path = Path(repo_info["path"])

    pad = git_sync.create_workpad(repo_id, "Add farewell")
    pad_id = pad["workpad_id"]

    def add_farewell(original: str) -> str:
        lines = original.splitlines()
        insertion = [
            "",
            "def farewell(name):",
            "    \"\"\"Say goodbye to someone.\"\"\"",
            "    return f\"Goodbye, {name}!\"",
            "",
        ]
        target = lines.index("if __name__ == \"__main__\":")
        new_lines = lines[:target] + insertion + lines[target:]
        return "\n".join(new_lines) + "\n"

    def update_tests(original: str) -> str:
        lines = original.splitlines()
        lines[0] = "from hello import greet, farewell"
        updated = lines + [
            "",
            "def test_farewell_says_goodbye():",
            "    assert farewell(\"Alice\") == \"Goodbye, Alice!\"",
        ]
        return "\n".join(updated) + "\n"

    farewell_patch = _generate_modify_patch(repo_path, "hello.py", add_farewell)
    test_patch = _generate_modify_patch(repo_path, "tests/test_hello.py", update_tests)
    combined_patch = f"{farewell_patch}\n{test_patch}"
    git_sync.apply_patch(pad_id, combined_patch, "Add farewell support")

    _, results = _run_pytest_and_record(git_sync, test_runner, pad_id)
    assert all(result.status == TestStatus.PASSED for result in results)

    merge_commit = git_sync.promote_workpad(pad_id)
    repo_after_merge = Repo(repo_path)
    promoted_head = repo_after_merge.head.commit.hexsha
    assert promoted_head == merge_commit

    ci_orchestrator = CIOrchestrator(git_sync.git_engine, test_runner)
    smoke_tests = [
        TestConfig(name="smoke", cmd="python -c 'import sys; sys.exit(1)'", timeout=10)
    ]
    ci_result = ci_orchestrator.run_smoke_tests(repo_id, merge_commit, smoke_tests)
    assert ci_result.status == CIStatus.FAILURE

    rollback = RollbackHandler(git_sync.git_engine)
    rollback_result = rollback.handle_failed_ci(ci_result)
    assert rollback_result.success is True
    assert rollback_result.new_pad_id is not None

    repo_after_rollback = Repo(repo_path)
    assert repo_after_rollback.head.commit.hexsha != merge_commit


def test_parallel_workpads_merge_order(
    git_sync: GitStateSync,
    sample_project_zip: bytes,
    test_runner: TestOrchestrator,
):
    """Merge multiple workpads sequentially without conflicts."""
    repo_info = git_sync.init_repo_from_zip(sample_project_zip, "Sample App")
    repo_id = repo_info["repo_id"]
    repo_path = Path(repo_info["path"])

    changes = [
        ("Add feature A", lambda: _generate_create_patch("feature_a.py", """def feature_a():
    return "A"
""")),
        ("Add feature B", lambda: _generate_create_patch("feature_b.py", """def feature_b():
    return "B"
""")),
        (
            "Improve docs",
            lambda: _generate_modify_patch(
                repo_path,
                "README.md",
                lambda original: original + "\nAutomated workflow coverage.\n",
            ),
        ),
    ]

    promoted_ids = []
    for title, patch_factory in changes:
        pad_info = git_sync.create_workpad(repo_id, title)
        pad_id = pad_info["workpad_id"]
        git_sync.apply_patch(pad_id, patch_factory(), title)
        _run_pytest_and_record(git_sync, test_runner, pad_id)
        assert git_sync.git_engine.can_promote(pad_id), f"Workpad {pad_id} not fast-forwardable"
        git_sync.promote_workpad(pad_id)
        promoted_ids.append(pad_id)

    repo = Repo(repo_path)
    files = {path.path for path in repo.head.commit.tree.traverse() if path.type == "blob"}
    assert "feature_a.py" in files
    assert "feature_b.py" in files
    assert "Automated workflow" in (repo_path / "README.md").read_text()
    assert len(promoted_ids) == 3



def test_budget_exceeded_blocks_ai_operation(
    ai_config_manager: ConfigManager,
    tmp_path,
):
    """Ensure the cost guard prevents AI work when budget is depleted."""
    config = ai_config_manager
    config.config.budget.daily_usd_cap = 0.1
    orchestrator = AIOrchestrator(config)

    from sologit.orchestration.cost_guard import CostTracker

    orchestrator.cost_guard.tracker = CostTracker(tmp_path / "budget.json")
    orchestrator.cost_guard.record_usage(
        model="gpt-4o",
        prompt_tokens=1000,
        completion_tokens=1000,
        cost_per_1k=0.06,
        task_type="planning",
    )

    assert orchestrator.cost_guard.get_remaining_budget() <= 0
    with pytest.raises(Exception, match="Budget exceeded"):
        orchestrator.plan("Plan with depleted budget")


def test_promotion_gate_rejects_on_failed_tests(
    git_sync: GitStateSync,
    sample_project_zip: bytes,
    test_runner: TestOrchestrator,
):
    """Promotion gate should reject workpads when tests fail."""
    repo_info = git_sync.init_repo_from_zip(sample_project_zip, "Sample App")
    repo_id = repo_info["repo_id"]
    pad = git_sync.create_workpad(repo_id, "Break tests")
    pad_id = pad["workpad_id"]
    repo_path = Path(repo_info["path"])

    failure_patch = _generate_modify_patch(
        repo_path,
        "hello.py",
        lambda original: original.replace(
            "    return f\"Hello, {name}!\"\n",
            "    raise RuntimeError(\"Boom\")\n",
        ),
    )
    git_sync.apply_patch(pad_id, failure_patch, "Break greeting")

    _, results = _run_pytest_and_record(git_sync, test_runner, pad_id)
    analysis = _analysis_from_results(results)

    gate = PromotionGate(git_sync.git_engine)
    decision = gate.evaluate(pad_id, analysis)
    assert decision.decision == PromotionDecisionType.REJECT
    assert any("Tests failed" in reason for reason in decision.reasons)


def test_promotion_gate_warns_on_coverage_requirement(
    git_sync: GitStateSync,
    sample_project_zip: bytes,
    test_runner: TestOrchestrator,
):
    """Coverage requirement should surface warnings when not implemented."""
    repo_info = git_sync.init_repo_from_zip(sample_project_zip, "Sample App")
    repo_id = repo_info["repo_id"]
    pad = git_sync.create_workpad(repo_id, "Docs change")
    pad_id = pad["workpad_id"]

    git_sync.apply_patch(
        pad_id,
        _generate_create_patch("CHANGELOG.md", "Initial entry\n"),
        "Add changelog",
    )
    _, results = _run_pytest_and_record(git_sync, test_runner, pad_id)
    analysis = _analysis_from_results(results)

    rules = PromotionRules(min_coverage_percent=80)
    gate = PromotionGate(git_sync.git_engine, rules)
    decision = gate.evaluate(pad_id, analysis)
    assert decision.decision == PromotionDecisionType.APPROVE
    assert any("Coverage" in warning for warning in decision.warnings)


def test_conflicting_workpads_block_second_promotion(
    git_sync: GitStateSync,
    sample_project_zip: bytes,
    test_runner: TestOrchestrator,
):
    """Verify second workpad is blocked when trunk has diverged."""
    repo_info = git_sync.init_repo_from_zip(sample_project_zip, "Sample App")
    repo_id = repo_info["repo_id"]
    repo_path = Path(repo_info["path"])

    pad_one = git_sync.create_workpad(repo_id, "First change")
    pad_two = git_sync.create_workpad(repo_id, "Second change")

    update_patch = _generate_modify_patch(
        repo_path,
        "hello.py",
        lambda original: original.replace(
            "    return f\"Hello, {name}!\"\n",
            "    return f\"Hello there, {name}!\"\n",
        ),
    )

    git_sync.apply_patch(pad_one["workpad_id"], update_patch, "Friendly greeting")
    _run_pytest_and_record(git_sync, test_runner, pad_one["workpad_id"])
    git_sync.promote_workpad(pad_one["workpad_id"])

    git_sync.apply_patch(pad_two["workpad_id"], update_patch, "Conflicting greeting")
    _run_pytest_and_record(git_sync, test_runner, pad_two["workpad_id"])

    with pytest.raises(CannotPromoteError):
        git_sync.git_engine.promote_workpad(pad_two["workpad_id"])


def test_fast_forward_requirement_enforced(
    git_sync: GitStateSync,
    sample_project_zip: bytes,
    test_runner: TestOrchestrator,
):
    """Promotion gate enforces fast-forward requirement when trunk diverges."""
    repo_info = git_sync.init_repo_from_zip(sample_project_zip, "Sample App")
    repo_id = repo_info["repo_id"]
    repo_path = Path(repo_info["path"])

    pad_primary = git_sync.create_workpad(repo_id, "Primary change")
    pad_secondary = git_sync.create_workpad(repo_id, "Secondary change")

    baseline_readme = (repo_path / "README.md").read_text()
    primary_patch = _diff_from_strings(
        baseline_readme,
        baseline_readme + "\nPrimary change applied.\n",
        "README.md",
    )

    git_sync.apply_patch(pad_primary["workpad_id"], primary_patch, "Primary update")
    _run_pytest_and_record(git_sync, test_runner, pad_primary["workpad_id"])
    git_sync.promote_workpad(pad_primary["workpad_id"])

    secondary_patch = _diff_from_strings(
        baseline_readme,
        baseline_readme + "\nSecondary change pending.\n",
        "README.md",
    )
    git_sync.apply_patch(pad_secondary["workpad_id"], secondary_patch, "Secondary update")
    _, results = _run_pytest_and_record(git_sync, test_runner, pad_secondary["workpad_id"])
    analysis = _analysis_from_results(results)

    gate = PromotionGate(git_sync.git_engine)
    decision = gate.evaluate(pad_secondary["workpad_id"], analysis)
    assert decision.decision == PromotionDecisionType.REJECT
    assert any("fast-forward" in reason.lower() for reason in decision.reasons)


def test_state_manager_records_cli_operations(
    git_sync: GitStateSync,
    sample_project_zip: bytes,
    test_runner: TestOrchestrator,
):
    """State Manager should persist repository, workpad, and test metadata."""
    repo_info = git_sync.init_repo_from_zip(sample_project_zip, "Sample App")
    repo_id = repo_info["repo_id"]
    pad = git_sync.create_workpad(repo_id, "Record state")
    pad_id = pad["workpad_id"]

    git_sync.apply_patch(
        pad_id,
        _generate_create_patch("NOTES.md", "State tracking\n"),
        "Add notes",
    )
    _run_pytest_and_record(git_sync, test_runner, pad_id)

    backend = git_sync.state_manager.backend
    assert isinstance(backend, JSONStateBackend)
    repo_state_path = backend.repos_dir / f"{repo_id}.json"
    workpad_state_path = backend.workpads_dir / f"{pad_id}.json"
    assert repo_state_path.exists()
    assert workpad_state_path.exists()

    repo_state = json.loads(repo_state_path.read_text())
    workpad_state = json.loads(workpad_state_path.read_text())
    assert repo_state["repo_id"] == repo_id
    assert pad_id in repo_state["workpads"]
    assert workpad_state["workpad_id"] == pad_id
    assert workpad_state["status"] == "active"

    test_runs = list(git_sync.get_test_runs(pad_id))
    assert len(test_runs) == 1
    assert test_runs[0]["status"] in {"passed", "failed"}
