"""End-to-end tests for auto-merge workflow CI integration."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from sologit.config.manager import CISmokeConfig
from sologit.engines.test_orchestrator import TestConfig, TestResult, TestStatus
from sologit.state.manager import StateManager
from sologit.workflows.auto_merge import AutoMergeWorkflow
from sologit.workflows.ci_orchestrator import CIResult, CIStatus
from sologit.workflows.promotion_gate import PromotionRules
from sologit.workflows.rollback_handler import RollbackResult


@pytest.fixture
def state_manager(tmp_path: Path) -> StateManager:
    """Create a state manager backed by a temporary directory."""
    return StateManager(state_dir=tmp_path)


def _create_workpad(repo_id: str = "repo-1") -> SimpleNamespace:
    return SimpleNamespace(title="Add feature", repo_id=repo_id)


def _make_test_result(name: str = "unit") -> TestResult:
    return TestResult(
        name=name,
        status=TestStatus.PASSED,
        duration_ms=50,
        exit_code=0,
        stdout="",
        stderr="",
    )


def _build_ci_result(status: CIStatus, repo_id: str, commit_hash: str, message: str) -> CIResult:
    return CIResult(
        repo_id=repo_id,
        commit_hash=commit_hash,
        status=status,
        duration_ms=120,
        test_results=[],
        message=message,
    )


def _configure_git_engine(commit_hash: str = "abc1234567890") -> Mock:
    git_engine = Mock()
    git_engine.get_workpad.return_value = _create_workpad()
    git_engine.get_diff.return_value = "diff --git a/file.py b/file.py\n--- a/file.py\n+++ b/file.py\n"
    git_engine.can_promote.return_value = True
    git_engine.promote_workpad.return_value = commit_hash
    return git_engine


def test_auto_merge_success_records_state_and_ci(state_manager: StateManager):
    """Successful auto-merge should record history and skip rollback."""
    git_engine = _configure_git_engine()
    test_orchestrator = Mock()
    test_orchestrator.run_tests_sync.return_value = [_make_test_result()]

    ci_orchestrator = Mock()
    ci_result = _build_ci_result(CIStatus.SUCCESS, "repo-1", "abc1234567890", "all good")
    ci_orchestrator.run_smoke_tests.return_value = ci_result

    rollback_handler = Mock()

    workflow = AutoMergeWorkflow(
        git_engine,
        test_orchestrator,
        PromotionRules(),
        state_manager=state_manager,
        ci_orchestrator=ci_orchestrator,
        rollback_handler=rollback_handler,
        ci_smoke_tests=[TestConfig(name="smoke", cmd="pytest -k smoke", timeout=30)],
        ci_config=CISmokeConfig(auto_run=True, command="echo ok"),
    )

    with patch.object(workflow, "_run_ci_command", return_value=(True, "ok")) as command_mock:
        result = workflow.execute(
            "pad-1",
            [TestConfig(name="unit", cmd="pytest", timeout=60)],
            auto_promote=True,
            target="fast",
        )

    assert result.success is True
    assert result.commit_hash == "abc1234567890"
    assert result.ci_result is not None and result.ci_result.status == CIStatus.SUCCESS
    command_mock.assert_called_once()
    rollback_handler.handle_failed_ci.assert_not_called()

    runs = state_manager.list_test_runs("pad-1")
    assert runs and runs[0].status == "passed"

    promotions = state_manager.list_promotion_records(workpad_id="pad-1")
    assert promotions and promotions[0].promoted is True
    assert promotions[0].ci_status == CIStatus.SUCCESS.value


def test_auto_merge_ci_failure_triggers_rollback(state_manager: StateManager):
    """Failing CI smoke test should trigger rollback and record outcome."""
    git_engine = _configure_git_engine("def9876543210")
    test_orchestrator = Mock()
    test_orchestrator.run_tests_sync.return_value = [_make_test_result()]

    ci_orchestrator = Mock()
    failing_ci = _build_ci_result(
        CIStatus.FAILURE,
        "repo-1",
        "def9876543210",
        "smoke failure",
    )
    ci_orchestrator.run_smoke_tests.return_value = failing_ci

    rollback_handler = Mock()
    rollback_handler.handle_failed_ci.return_value = RollbackResult(
        success=True,
        repo_id="repo-1",
        reverted_commit="def9876543210",
        new_pad_id=None,
        message="rolled back",
    )

    workflow = AutoMergeWorkflow(
        git_engine,
        test_orchestrator,
        PromotionRules(),
        state_manager=state_manager,
        ci_orchestrator=ci_orchestrator,
        rollback_handler=rollback_handler,
        ci_smoke_tests=[TestConfig(name="smoke", cmd="pytest -k smoke", timeout=30)],
        ci_config=CISmokeConfig(auto_run=True),
    )

    result = workflow.execute(
        "pad-2",
        [TestConfig(name="unit", cmd="pytest", timeout=60)],
        auto_promote=True,
        target="fast",
    )

    assert result.success is False
    assert result.ci_result is not None and result.ci_result.status == CIStatus.FAILURE
    assert "failed ci" in result.message.lower()
    rollback_handler.handle_failed_ci.assert_called_once_with(failing_ci)

    promotions = state_manager.list_promotion_records(workpad_id="pad-2")
    assert promotions and promotions[0].promoted is False
    assert promotions[0].ci_status == CIStatus.FAILURE.value
