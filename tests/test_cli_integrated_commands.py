"""Integration-style tests for the Rich CLI command groups.

These tests focus on the higher-level command groups defined in
``sologit.cli.integrated_commands``.  The commands orchestrate multiple
subsystems (Git synchronization, AI orchestrator, history tracking), so the
tests rely heavily on mocks to verify behaviour without touching the real
environment.
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from sologit.cli.integrated_commands import ai, edit, history, workpad


@pytest.fixture
def runner() -> CliRunner:
    """Return a ``CliRunner`` instance."""

    return CliRunner()


@pytest.fixture
def mock_git_sync():
    """Patch ``get_git_sync`` to provide a reusable mock instance."""

    with patch("sologit.cli.integrated_commands.get_git_sync") as mock_get:
        git_sync = MagicMock()
        git_sync.get_active_context.return_value = {
            "repo_id": "repo-1",
            "workpad_id": "pad-1",
        }
        mock_get.return_value = git_sync
        yield git_sync


@pytest.fixture
def config_manager():
    """Build a lightweight configuration object for the CLI context."""

    models = SimpleNamespace(planning_model="plan-model", coding_model="code-model")
    config = SimpleNamespace(models=models)
    return SimpleNamespace(config=config)


def test_workpad_create_auto_selects_single_repo(runner, mock_git_sync, config_manager):
    """The create command should auto-select when only one repo exists."""

    mock_git_sync.list_repos.return_value = [
        {"id": "repo-1", "name": "Solo Project"}
    ]
    mock_git_sync.create_workpad.return_value = {
        "workpad_id": "pad-9",
        "branch_name": "pad/solo-project",
        "status": "active",
    }

    with patch("sologit.ui.history.add_command") as mock_add_command:
        result = runner.invoke(workpad, ["create", "solo-project"], obj={"config": config_manager})

    assert result.exit_code == 0, result.output
    assert "Using repository: Solo Project" in result.output
    assert "Workpad created successfully" in result.output
    mock_git_sync.create_workpad.assert_called_once_with("repo-1", "solo-project")
    mock_add_command.assert_called_once()


def test_workpad_list_filters_by_status(runner, mock_git_sync, config_manager):
    """Filtering should only show workpads that match the requested status."""

    mock_git_sync.list_workpads.return_value = [
        {
            "id": "pad-1",
            "title": "active-feature",
            "status": "active",
            "test_status": "green",
            "created_at": "2024-01-01T10:00:00Z",
        },
        {
            "id": "pad-2",
            "title": "old-feature",
            "status": "promoted",
            "test_status": "red",
            "created_at": "2024-01-01T09:00:00Z",
        },
    ]

    result = runner.invoke(
        workpad,
        ["list", "--status", "active"],
        obj={"config": config_manager},
    )

    assert result.exit_code == 0, result.output
    assert "active-feature" in result.output
    assert "old-feature" not in result.output
    assert "Total: 1 workpad" in result.output


def test_workpad_status_uses_active_context(runner, mock_git_sync, config_manager):
    """Status command should pull the active workpad when none is provided."""

    mock_git_sync.get_active_context.return_value = {
        "repo_id": "repo-1",
        "workpad_id": "pad-9",
    }
    mock_git_sync.get_workpad.return_value = {
        "id": "pad-9",
        "title": "api-updates",
        "repo_id": "repo-1",
        "branch_name": "pad/api-updates",
        "status": "active",
        "created_at": "2024-01-01T12:34:56Z",
        "test_status": "green",
        "last_commit": "abcdef1234567890",
    }
    mock_git_sync.get_status.return_value = {
        "current_branch": "pad/api-updates",
        "modified_files": ["app.py"],
        "untracked_files": ["notes.md"],
    }
    mock_git_sync.get_test_runs.return_value = [
        {
            "status": "passed",
            "target": "full",
            "started_at": "2024-01-01T12:30:00Z",
        }
    ]

    result = runner.invoke(workpad, ["status"], obj={"config": config_manager})

    assert result.exit_code == 0, result.output
    assert "Workpad Status: api-updates" in result.output
    assert "pad-9" in result.output
    assert "Last Test     ✓ green" in result.output
    assert "Modified    app.py" in result.output
    assert "Recent Test Runs (1 shown)" in result.output


def test_workpad_diff_reports_when_empty(runner, mock_git_sync, config_manager):
    """If there are no changes the diff command should explain that."""

    mock_git_sync.get_active_context.return_value = {"workpad_id": "pad-3"}
    mock_git_sync.get_workpad.return_value = {"title": "test-pad"}
    mock_git_sync.get_diff.return_value = ""

    result = runner.invoke(workpad, ["diff"], obj={"config": config_manager})

    assert result.exit_code == 0
    assert "No changes between the workpad and base branch." in result.output


def test_workpad_promote_requires_green_tests(runner, mock_git_sync, config_manager):
    """Promotion should abort when tests are not green."""

    mock_git_sync.get_active_context.return_value = {"workpad_id": "pad-5"}
    mock_git_sync.get_workpad.return_value = {
        "title": "feature-x",
        "test_status": "yellow",
    }

    result = runner.invoke(workpad, ["promote"], obj={"config": config_manager})

    assert result.exit_code == 1
    assert "Cannot promote" in result.output
    mock_git_sync.promote_workpad.assert_not_called()


def test_workpad_delete_force_skips_confirmation(runner, mock_git_sync, config_manager):
    """Force deletion should bypass the interactive confirmation."""

    mock_git_sync.get_workpad.return_value = {
        "title": "stale-pad",
        "status": "active",
    }

    result = runner.invoke(
        workpad,
        ["delete", "pad-8", "--force"],
        obj={"config": config_manager},
    )

    assert result.exit_code == 0, result.output
    assert "Workpad deleted" in result.output
    mock_git_sync.delete_workpad.assert_called_once_with("pad-8", True)


def test_ai_commit_message_generates_summary(runner, mock_git_sync, config_manager):
    """A commit message should be suggested when diff content exists."""

    mock_git_sync.get_active_context.return_value = {"workpad_id": "pad-1"}
    mock_git_sync.get_diff.return_value = "diff\n+++ b/app.py\n+++ b/utils.py"
    mock_git_sync.create_ai_operation.return_value = {"operation_id": "op-1"}

    with patch("sologit.cli.integrated_commands.get_ai_orchestrator") as mock_get_orch:
        mock_get_orch.return_value = MagicMock()
        result = runner.invoke(
            ai,
            ["commit-message"],
            obj={"config": config_manager},
        )

    assert result.exit_code == 0, result.output
    assert "Suggested commit message" in result.output
    mock_git_sync.update_ai_operation.assert_called_once()


def test_ai_commit_message_no_changes_aborts(runner, mock_git_sync, config_manager):
    """If there is no diff the command should abort early."""

    mock_git_sync.get_active_context.return_value = {"workpad_id": "pad-2"}
    mock_git_sync.get_diff.return_value = ""

    with patch("sologit.cli.integrated_commands.get_ai_orchestrator"):
        result = runner.invoke(ai, ["commit-message"], obj={"config": config_manager})

    assert result.exit_code == 1
    assert "No changes to commit" in result.output


def test_ai_status_reports_budget(runner, mock_git_sync, config_manager):
    """Status output should include budget and model information."""

    status_payload = {
        "budget": {
            "daily_usd_cap": 25.0,
            "total_cost_usd": 2.5,
            "remaining_budget": 22.5,
        },
        "models": {
            "fast": ["fast-a"],
            "coding": ["code-a"],
            "planning": ["plan-a"],
        },
        "api_configured": True,
    }

    with patch("sologit.cli.integrated_commands.get_ai_orchestrator") as mock_get_orch:
        orchestrator = MagicMock()
        orchestrator.get_status.return_value = status_payload
        mock_get_orch.return_value = orchestrator

        result = runner.invoke(ai, ["status"], obj={"config": config_manager})

    assert result.exit_code == 0, result.output
    assert "Daily Cap" in result.output
    assert "fast-a" in result.output
    assert "Abacus.ai API configured" in result.output


def test_history_log_shows_commits(runner, mock_git_sync, config_manager):
    """Commit history should render the provided commits."""

    mock_git_sync.get_active_context.return_value = {"repo_id": "repo-1"}
    mock_git_sync.get_history.return_value = [
        {
            "sha": "abcdef123456",
            "message": "Initial commit\n\nFull body",
            "author": "Solo Dev <solo@example.com>",
            "timestamp": datetime(2024, 1, 1, 10, 0, 0).isoformat(),
        }
    ]

    result = runner.invoke(history, ["log"], obj={"config": config_manager})

    assert result.exit_code == 0, result.output
    assert "Initial commit" in result.output
    assert "Solo Dev" in result.output


def test_history_revert_with_confirmation(runner, mock_git_sync, config_manager):
    """Reverting should succeed when confirmation is provided."""

    mock_git_sync.get_active_context.return_value = {"repo_id": "repo-1"}
    mock_git_sync.get_history.return_value = [
        {
            "sha": "deadbeef",
            "message": "Fix bug",
            "author": "Solo Dev",
        }
    ]

    result = runner.invoke(
        history,
        ["revert", "--confirm"],
        obj={"config": config_manager},
    )

    assert result.exit_code == 0, result.output
    assert "reverted" in result.output.lower()
    mock_git_sync.revert_last_commit.assert_called_once_with("repo-1")


def test_edit_undo_when_nothing_to_undo(runner, config_manager):
    """The undo command should abort when there is no history."""

    with patch("sologit.ui.history.can_undo", return_value=False), patch(
        "sologit.ui.history.undo"
    ):
        result = runner.invoke(edit, ["undo"], obj={"config": config_manager})

    assert result.exit_code == 1
    assert "Nothing to undo" in result.output


def test_edit_history_search_results(runner, config_manager):
    """The history search view should render matching entries."""

    entry = SimpleNamespace(
        timestamp=datetime(2024, 1, 2, 15, 30, 0),
        description="Created workpad",
        type=SimpleNamespace(value="workpad_create"),
        undoable=True,
    )

    history_obj = SimpleNamespace(
        search=lambda query: [entry],
        get_history=lambda limit: [],
    )

    with patch("sologit.ui.history.get_command_history", return_value=history_obj):
        result = runner.invoke(
            edit,
            ["history", "--search", "workpad"],
            obj={"config": config_manager},
        )

    assert result.exit_code == 0, result.output
    assert "Search results" in result.output
    assert "Created workpad" in result.output

