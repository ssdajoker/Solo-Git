import difflib
import json
import os
import shutil
from io import BytesIO
from pathlib import Path
from typing import Callable, Iterable
from zipfile import ZipFile

import pytest
from click.testing import CliRunner
from git import Repo

from sologit.analysis.test_analyzer import TestAnalysis, TestAnalyzer
from sologit.cli.main import cli
from sologit.config.manager import ConfigManager
from sologit.engines.git_engine import CannotPromoteError
from sologit.engines.patch_engine import PatchEngine
from sologit.engines.test_orchestrator import (
    TestConfig,
    TestOrchestrator,
    TestResult,
    TestStatus,
)
from sologit.orchestration.ai_orchestrator import AIOrchestrator
from sologit.orchestration.planning_engine import FileChange
from sologit.state.git_sync import GitStateSync
from sologit.state.manager import StateManager
from sologit.workflows.ci_orchestrator import CIOrchestrator, CIResult, CIStatus
from sologit.workflows.promotion_gate import (
    PromotionDecisionType,
    PromotionGate,
    PromotionRules,
)
from sologit.workflows.rollback_handler import RollbackHandler

@pytest.fixture
def runner(tmp_path_factory):
    state_path = tmp_path_factory.mktemp("sologit_state")
    data_path = tmp_path_factory.mktemp("sologit_data")
    runner = CliRunner(
        env={
            "SOLOGIT_STATE_PATH": str(state_path),
            "SOLOGIT_DATA_PATH": str(data_path),
        }
    )
    runner.state_path = state_path  # type: ignore[attr-defined]
    runner.data_path = data_path  # type: ignore[attr-defined]
    return runner

@pytest.fixture
def test_repo_path(tmp_path):
    return tmp_path / "test_repo"

@pytest.fixture
def setup_repo(runner, test_repo_path):
    """Initialize an empty repository via the CLI and clean it up afterwards."""

    os.makedirs(test_repo_path, exist_ok=True)
    state_path = Path(getattr(runner, "state_path"))
    data_path = Path(getattr(runner, "data_path"))
    baseline_state = StateManager(state_dir=state_path)
    existing_ids = {repo.repo_id for repo in baseline_state.list_repositories()}
    result = runner.invoke(
        cli,
        [
            "repo",
            "init",
            "--path",
            str(test_repo_path),
            "--name",
            "test-repo",
            "--empty",
        ],
    )
    assert result.exit_code == 0, f"Failed to init repo: {result.output}"

    current_state = StateManager(state_dir=state_path)
    repos = current_state.list_repositories()
    new_repos = [repo for repo in repos if repo.repo_id not in existing_ids]
    repo_id = new_repos[0].repo_id if new_repos else None

    try:
        yield test_repo_path, state_path, repo_id
    finally:
        shutil.rmtree(test_repo_path)
        if data_path.exists():
            shutil.rmtree(data_path, ignore_errors=True)
        if state_path.exists():
            shutil.rmtree(state_path, ignore_errors=True)


@pytest.fixture
def ai_orchestrator(
    ai_config_manager: ConfigManager, tmp_path
) -> AIOrchestrator:
    orchestrator = AIOrchestrator(ai_config_manager)
    # Ensure isolated budget tracking between tests
    from sologit.orchestration.cost_guard import CostTracker

    orchestrator.cost_guard.tracker = CostTracker(tmp_path / "usage.json")
    return orchestrator


@pytest.fixture
def ai_config_manager(tmp_path) -> ConfigManager:
    """Provide a configured ConfigManager using a temporary config file."""

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
abacus:
  endpoint: "https://api.abacus.ai/v1"
  api_key: "test-key"

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

budget:
  daily_usd_cap: 25.0
  alert_threshold: 0.8
  track_by_model: true

promote_on_green: true
rollback_on_ci_red: true
"""
    )
    return ConfigManager(config_path=config_path)


@pytest.fixture
def workspace_paths(tmp_path_factory):
    """Create isolated state and data directories for GitStateSync."""

    state_dir = tmp_path_factory.mktemp("sologit_state")
    data_dir = tmp_path_factory.mktemp("sologit_data")
    return state_dir, data_dir


@pytest.fixture
def git_sync(workspace_paths) -> GitStateSync:
    state_dir, data_dir = workspace_paths
    return GitStateSync(state_dir=state_dir, data_dir=data_dir)


@pytest.fixture
def patch_engine(git_sync: GitStateSync) -> PatchEngine:
    return PatchEngine(git_sync.git_engine)


@pytest.fixture
def test_runner(git_sync: GitStateSync) -> TestOrchestrator:
    return TestOrchestrator(git_sync.git_engine)


@pytest.fixture
def sample_project_zip() -> bytes:
    """Return a zipped sample project with a simple test suite."""

    buffer = BytesIO()
    with ZipFile(buffer, "w") as zf:
        zf.writestr(
            "hello.py",
            '''def greet(name):
    """Say hello to someone."""
    return f"Hello, {name}!"


if __name__ == "__main__":
    print(greet("World"))
''',
        )
        zf.writestr(
            "tests/test_hello.py",
            '''from hello import greet


def test_greet():
    assert greet("Alice") == "Hello, Alice!"
    assert greet("Bob") == "Hello, Bob!"
''',
        )
        zf.writestr("README.md", "# Sample Project\n\nUsed for end-to-end tests.\n")
    buffer.seek(0)
    return buffer.read()


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
    """Create a unified diff for introducing a brand new file."""

    if not content.endswith("\n"):
        content += "\n"

    lines = content.splitlines(keepends=True)

    # Provide minimal diff headers so git apply recognizes the new file.
    header = [
        f"diff --git a/{rel_path} b/{rel_path}\n",
        "new file mode 100644\n",
        "index 0000000..1111111\n",
        "--- /dev/null\n",
        f"+++ b/{rel_path}\n",
        f"@@ -0,0 +1,{len(lines)} @@\n",
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
    patch_engine: PatchEngine,
    test_runner: TestOrchestrator,
):
    """Run the full AI-driven workflow from prompt all the way to auto-merge."""
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
    checkpoint = patch_engine.apply_patch(
        pad_id,
        diff,
        "Add developer notes",
    )
    assert checkpoint

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
    assert "AI-assisted workflow" in doc_path.read_text()

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
    assert git_sync.git_engine.get_workpad(pad_id).test_status == "green"


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

    original_create_workpad = git_sync.git_engine.create_workpad

    def _create_workpad_object(repo_id: str, title: str):
        pad_identifier = original_create_workpad(repo_id, title)
        return git_sync.git_engine.get_workpad(pad_identifier)

    git_sync.git_engine.create_workpad = _create_workpad_object
    try:
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
    finally:
        git_sync.git_engine.create_workpad = original_create_workpad

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

    repo_state_path = git_sync.state_manager.backend.repos_dir / f"{repo_id}.json"
    workpad_state_path = git_sync.state_manager.backend.workpads_dir / f"{pad_id}.json"
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


@pytest.mark.smoke
def test_happy_path_create_file_and_promote(
    git_sync: GitStateSync,
    sample_project_zip: bytes,
    test_runner: TestOrchestrator,
):
    """A simple happy path: create a file, test, and promote."""
    repo_info = git_sync.init_repo_from_zip(sample_project_zip, "Happy Path Repo")
    repo_id = repo_info["repo_id"]
    pad_info = git_sync.create_workpad(repo_id, "Add new file")
    pad_id = pad_info["workpad_id"]
    repo_path = Path(repo_info["path"])

    new_file_patch = _generate_create_patch("new_file.txt", "This is a new file.")
    git_sync.apply_patch(pad_id, new_file_patch, "Add new_file.txt")

    _, results = _run_pytest_and_record(git_sync, test_runner, pad_id)
    assert all(result.status == TestStatus.PASSED for result in results)

    git_sync.promote_workpad(pad_id)

    new_file_path = repo_path / "new_file.txt"
    assert new_file_path.exists()
    assert new_file_path.read_text() == "This is a new file.\n"


def test_failure_workflow_prevents_promotion(
    git_sync: GitStateSync,
    sample_project_zip: bytes,
    test_runner: TestOrchestrator,
):
    """Verify that a workpad with failing tests cannot be promoted."""
    repo_info = git_sync.init_repo_from_zip(sample_project_zip, "Failure Workflow Repo")
    repo_id = repo_info["repo_id"]
    pad_info = git_sync.create_workpad(repo_id, "Introduce breaking change")
    pad_id = pad_info["workpad_id"]
    repo_path = Path(repo_info["path"])

    # Introduce a change that will cause tests to fail
    breaking_patch = _generate_modify_patch(
        repo_path,
        "hello.py",
        lambda original: original.replace(
            'return f"Hello, {name}!"',
            'raise ValueError("This is a deliberate failure")'
        ),
    )
    git_sync.apply_patch(pad_id, breaking_patch, "Break the greeting")

    _, results = _run_pytest_and_record(git_sync, test_runner, pad_id)
    assert any(result.status == TestStatus.FAILED for result in results)

    # Verify that the workpad cannot be promoted
    gate = PromotionGate(git_sync.git_engine)
    analysis = _analysis_from_results(results)
    decision = gate.evaluate(pad_id, analysis)
    assert decision.decision == PromotionDecisionType.REJECT

    workpad_state = git_sync.state_manager.get_workpad(pad_id)
    assert workpad_state.status == "active"  # Should not be promoted


def test_rollback_e2e(
    git_sync: GitStateSync,
    sample_project_zip: bytes,
    test_runner: TestOrchestrator,
):
    """Verify that a rollback successfully reverts a promoted change."""
    repo_info = git_sync.init_repo_from_zip(sample_project_zip, "Rollback Repo")
    repo_id = repo_info["repo_id"]
    repo_path = Path(repo_info["path"])
    initial_commit = Repo(repo_path).head.commit.hexsha

    pad_info = git_sync.create_workpad(repo_id, "Add a temporary file")
    pad_id = pad_info["workpad_id"]

    temp_file_patch = _generate_create_patch("temp_file.txt", "This will be rolled back.")
    git_sync.apply_patch(pad_id, temp_file_patch, "Add temp_file.txt")

    _, results = _run_pytest_and_record(git_sync, test_runner, pad_id)
    assert all(result.status == TestStatus.PASSED for result in results)

    promotion_commit = git_sync.promote_workpad(pad_id)
    assert Repo(repo_path).head.commit.hexsha == promotion_commit

    # Simulate a CI failure
    ci_result = CIResult(
        repo_id=repo_id,
        commit_hash=promotion_commit,
        status=CIStatus.FAILURE,
        duration_ms=1000,
        test_results=[],
        message="Simulated CI test failure",
    )

    # Perform the rollback
    rollback_handler = RollbackHandler(git_sync.git_engine)
    rollback_result = rollback_handler.handle_failed_ci(ci_result)
    assert rollback_result.success

    # Verify that the repo has been rolled back
    assert Repo(repo_path).head.commit.hexsha == initial_commit
    assert not (repo_path / "temp_file.txt").exists()


def test_parallel_workpads_rebase_and_promote(
    git_sync: GitStateSync,
    sample_project_zip: bytes,
    test_runner: TestOrchestrator,
):
    """Verify multiple workpads can be promoted sequentially without conflicts."""

    repo_info = git_sync.init_repo_from_zip(sample_project_zip, "Parallel Repo")
    repo_id = repo_info["repo_id"]
    repo_path = Path(repo_info["path"])

    # First workpad adds feature_x.py and promotes successfully.
    pad1_id = git_sync.create_workpad(repo_id, "Add feature X")["workpad_id"]
    feature_x_patch = _generate_create_patch(
        "feature_x.py",
        "def feature_x():\n    return \"X\"\n",
    )
    git_sync.apply_patch(pad1_id, feature_x_patch, "Add feature X")
    _run_pytest_and_record(git_sync, test_runner, pad1_id)
    assert git_sync.git_engine.can_promote(pad1_id)
    git_sync.promote_workpad(pad1_id)

    # Create a second workpad after the first promotion to ensure it tracks trunk.
    pad2_id = git_sync.create_workpad(repo_id, "Add feature Y")["workpad_id"]
    feature_y_patch = _generate_create_patch(
        "feature_y.py",
        "def feature_y():\n    return \"Y\"\n",
    )
    git_sync.apply_patch(pad2_id, feature_y_patch, "Add feature Y")
    _, results = _run_pytest_and_record(git_sync, test_runner, pad2_id)
    analysis = _analysis_from_results(results)

    gate = PromotionGate(git_sync.git_engine)
    decision = gate.evaluate(pad2_id, analysis)
    assert decision.decision == PromotionDecisionType.APPROVE
    git_sync.promote_workpad(pad2_id)

    repo = Repo(repo_path)
    files = {path.path for path in repo.head.commit.tree.traverse() if path.type == "blob"}
    assert "feature_x.py" in files
    assert "feature_y.py" in files

def test_happy_path_workflow(runner, setup_repo):
    repo_path, state_path, repo_id = setup_repo
    state_manager = StateManager(state_dir=state_path)

    # 1. Find the created repository in the state
    repos = state_manager.list_repositories()
    repo_state = next((repo for repo in repos if repo.repo_id == repo_id), None)
    assert repo_state is not None, "CLI did not register the new repository"
    repo_id = repo_state.repo_id

    # 2. Create a workpad
    result = runner.invoke(cli, ["pad", "create", "My first workpad", "--repo", repo_id])
    assert result.exit_code == 0, f"Failed to create workpad: {result.output}"

    # 3. Verify state
    state_manager = StateManager(state_dir=state_path)
    repo_state_after_create = state_manager.get_repository(repo_id)
    assert repo_state_after_create is not None, "Repository state not found"

    pads = state_manager.list_workpads(repo_id)
    assert len(pads) == 1, "Workpad was not created"

    workpad = pads[0]
    assert workpad.title == "My first workpad", "Workpad title is incorrect"
    assert workpad.status == "active", "Workpad status should reflect an active workpad"
def test_promote_empty_workpad_fails(
    git_sync: GitStateSync,
    sample_project_zip: bytes,
):
    """Verify that an empty workpad is rejected by the promotion gate."""
    repo_info = git_sync.init_repo_from_zip(sample_project_zip, "Empty Workpad Repo")
    repo_id = repo_info["repo_id"]
    pad_info = git_sync.create_workpad(repo_id, "Empty Workpad")
    pad_id = pad_info["workpad_id"]

    ahead_behind = git_sync.git_engine.get_commits_ahead_behind(pad_id)
    assert ahead_behind["ahead"] == 0
    assert ahead_behind["behind"] == 0

    gate = PromotionGate(git_sync.git_engine)
    decision = gate.evaluate(pad_id)
    assert decision.decision == PromotionDecisionType.REJECT
    assert any("Tests required" in reason for reason in decision.reasons)

    # The state manager should still list the workpad as active (not promoted)
    workpad_state = git_sync.state_manager.get_workpad(pad_id)
    assert workpad_state.status == "active"
