
"""Tests for the CLI commands."""
import pytest
from click.testing import CliRunner
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, AsyncMock
from sologit.cli.main import cli
from sologit.engines.git_engine import GitEngineError
from sologit.engines.test_orchestrator import TestStatus, TestResult
from datetime import datetime
from pathlib import Path


@pytest.fixture
def mock_git_engine():
    """Fixture for a mocked GitEngine."""
    with patch('sologit.cli.commands.get_git_engine') as mock_get:
        mock_engine = MagicMock()
        mock_get.return_value = mock_engine
        yield mock_engine
@pytest.fixture
def mock_git_sync():
    """Fixture for a mocked GitStateSync."""
    with patch('sologit.cli.commands.get_git_sync') as mock_get:
        mock_sync = MagicMock()
        mock_get.return_value = mock_sync
        yield mock_sync


@pytest.fixture
def mock_test_orchestrator():
    """Fixture for a mocked TestOrchestrator."""
    with patch('sologit.cli.commands.get_test_orchestrator') as mock_get:
        mock_orchestrator = MagicMock()
        mock_orchestrator.run_tests = AsyncMock()
        mock_orchestrator.mode = "subprocess"
        mock_get.return_value = mock_orchestrator
        yield mock_orchestrator


@pytest.fixture
def mock_state_manager():
    """Fixture for a mocked StateManager used by CLI commands."""
    with patch('sologit.cli.commands.StateManager') as mock_cls:
        instance = MagicMock()
        instance.create_test_run.return_value = SimpleNamespace(run_id='run-123')
        mock_cls.return_value = instance
        yield instance


def test_repo_list_no_repos(mock_git_engine):
    """Test `repo list` with no repositories."""
    mock_git_engine.list_repos.return_value = []
    runner = CliRunner()
    result = runner.invoke(cli, ['repo', 'list'])
    assert result.exit_code == 0
    assert "No repositories found" in result.output
    assert "evogitctl repo init" in result.output


def test_shortcuts_command():
    """Ensure the shortcuts reference renders without error."""

    runner = CliRunner()
    result = runner.invoke(cli, ['shortcuts'])

    assert result.exit_code == 0
    assert "Heaven Interface Keyboard Shortcuts" in result.output
    assert "Ctrl+P" in result.output


def test_repo_list_with_repos(mock_git_engine):
    """Test `repo list` with multiple repositories."""
    mock_repo1 = MagicMock()
    mock_repo1.id = "repo1"
    mock_repo1.name = "my-app"
    mock_repo1.trunk_branch = "main"
    mock_repo1.workpad_count = 2
    mock_repo1.created_at = datetime(2023, 1, 1, 10, 0)

    mock_repo2 = MagicMock()
    mock_repo2.id = "repo2"
    mock_repo2.name = "another-app"
    mock_repo2.trunk_branch = "develop"
    mock_repo2.workpad_count = 0
    mock_repo2.created_at = datetime(2023, 1, 2, 12, 30)

    mock_git_engine.list_repos.return_value = [mock_repo1, mock_repo2]
    runner = CliRunner()
    result = runner.invoke(cli, ['repo', 'list'])
    assert result.exit_code == 0
    # Check for Rich table headers
    assert "ID" in result.output
    assert "Name" in result.output
    assert "Trunk" in result.output
    assert "Workpads" in result.output
    assert "Created" in result.output
    # Check for content
    assert "repo1" in result.output
    assert "my-app" in result.output
    assert "2" in result.output
    assert "another-app" in result.output


def test_repo_info_found(mock_git_engine):
    """Test `repo info` for an existing repository."""
    mock_repo = MagicMock()
    mock_repo.id = "repo1"
    mock_repo.name = "my-app"
    mock_repo.path = "/path/to/repo"
    mock_repo.trunk_branch = "main"
    mock_repo.created_at = datetime(2023, 1, 1)
    mock_repo.workpad_count = 5
    mock_repo.source_type = "zip"
    mock_repo.source_url = None
    mock_git_engine.get_repo.return_value = mock_repo

    runner = CliRunner()
    result = runner.invoke(cli, ['repo', 'info', 'repo1'])

    assert result.exit_code == 0
    assert "Repository: my-app" in result.output
    assert "Name:" in result.output
    assert "my-app" in result.output
    assert "Path:" in result.output
    assert "/path/to/repo" in result.output
    assert "Workpads:" in result.output
    assert "5 active" in result.output
    assert "Source:" in result.output
    assert "zip" in result.output


def test_repo_info_not_found(mock_git_engine):
    """Test `repo info` for a non-existent repository."""
    mock_git_engine.get_repo.return_value = None
    runner = CliRunner()
    result = runner.invoke(cli, ['repo', 'info', 'nonexistent'])
    assert result.exit_code != 0
    assert "Repository 'nonexistent' is not registered with Solo Git." in result.output
    assert "Suggested Commands" in result.output


def test_repo_init_from_zip(mock_git_sync, tmp_path):
    """Test `repo init` from a zip file."""
    zip_file = tmp_path / "test.zip"
    zip_file.write_text("dummy content")

    mock_repo_info = {
        'repo_id': 'new_repo',
        'name': 'test',
        'path': '/path/to/new_repo',
        'trunk_branch': 'main',
    }
    mock_git_sync.init_repo_from_zip.return_value = mock_repo_info

    runner = CliRunner()
    result = runner.invoke(cli, ['repo', 'init', '--zip', str(zip_file)])

    assert result.exit_code == 0, result.output
    assert "Initializing from zip" in result.output
    assert "Repository initialized!" in result.output
    assert "ID" in result.output
    assert "new_repo" in result.output
    assert "Name" in result.output
    assert "test" in result.output
    mock_git_sync.init_repo_from_zip.assert_called_once()


def test_repo_init_from_git(mock_git_sync):
    """Test `repo init` from a git URL."""
    git_url = "https://github.com/example/repo.git"

    mock_repo_info = {
        'repo_id': 'git_repo',
        'name': 'repo',
        'path': '/path/to/git_repo',
        'trunk_branch': 'main',
    }
    mock_git_sync.init_repo_from_git.return_value = mock_repo_info

    runner = CliRunner()
    result = runner.invoke(cli, ['repo', 'init', '--git', git_url])

    assert result.exit_code == 0, result.output
    assert "Cloning from" in result.output
    assert "Repository initialized!" in result.output
    assert "ID" in result.output
    assert "git_repo" in result.output
    assert "Name" in result.output
    assert "repo" in result.output
    mock_git_sync.init_repo_from_git.assert_called_once_with(git_url, "repo")


def test_repo_init_no_source(mock_git_engine):
    """Test `repo init` with no source provided."""
    runner = CliRunner()
    result = runner.invoke(cli, ['repo', 'init'])
    assert result.exit_code != 0
    assert "Invalid Source Specification" in result.output
    assert "Please specify exactly one of --zip, --git, or --empty" in result.output


def test_repo_init_both_sources(mock_git_engine, tmp_path):
    """Test `repo init` with both zip and git sources."""
    zip_file = tmp_path / "test.zip"
    zip_file.write_text("dummy")
    git_url = "https://github.com/example/repo.git"
    runner = CliRunner()
    result = runner.invoke(cli, ['repo', 'init', '--zip', str(zip_file), '--git', git_url])
    assert result.exit_code != 0
    assert "Invalid Source Specification" in result.output
    assert "Please specify exactly one of --zip, --git, or --empty" in result.output


def test_repo_init_git_engine_error(mock_git_sync, tmp_path):
    """Test `repo init` handling a GitEngineError."""
    zip_file = tmp_path / "test.zip"
    zip_file.write_text("dummy")
    mock_git_sync.init_repo_from_zip.side_effect = GitEngineError("Failed to init")
    runner = CliRunner()
    result = runner.invoke(cli, ['repo', 'init', '--zip', str(zip_file)])
    assert result.exit_code != 0
    assert "Repository initialization failed" in result.output
    assert "Failed to init" in result.output


def test_pad_create_success(mock_git_engine):
    """Test `pad create` successfully."""
    mock_repo = MagicMock()
    mock_repo.id = "repo1"
    mock_repo.name = "my-app"
    mock_git_engine.list_repos.return_value = [mock_repo]

    mock_pad = MagicMock()
    mock_pad.id = "pad1"
    mock_pad.title = "new-feature"
    mock_pad.branch_name = "pad/new-feature"
    mock_git_engine.create_workpad.return_value = "pad1"
    mock_git_engine.get_workpad.return_value = mock_pad

    runner = CliRunner()
    result = runner.invoke(cli, ['pad', 'create', 'new-feature'])

    assert result.exit_code == 0, result.output
    assert "Using repository: my-app (repo1)" in result.output
    assert "Creating workpad: new-feature" in result.output
    assert "Workpad created!" in result.output
    assert "Pad ID: pad1" in result.output
    mock_git_engine.create_workpad.assert_called_once_with("repo1", "new-feature")


def test_pad_create_no_repo(mock_git_engine):
    """Test `pad create` with no repositories existing."""
    mock_git_engine.list_repos.return_value = []
    runner = CliRunner()
    result = runner.invoke(cli, ['pad', 'create', 'a-feature'])
    assert result.exit_code != 0
    assert "No repositories found" in result.output


def test_pad_create_multiple_repos_no_spec(mock_git_engine):
    """Test `pad create` with multiple repos but no --repo flag."""
    mock_git_engine.list_repos.return_value = [MagicMock(), MagicMock()]
    runner = CliRunner()
    result = runner.invoke(cli, ['pad', 'create', 'a-feature'])
    assert result.exit_code != 0
    assert "Multiple repositories found" in result.output


def test_pad_list_no_pads(mock_git_engine):
    """Test `pad list` with no workpads."""
    mock_git_engine.list_workpads.return_value = []
    runner = CliRunner()
    result = runner.invoke(cli, ['pad', 'list'])
    assert result.exit_code == 0
    assert "No workpads found" in result.output
    assert "evogitctl pad create" in result.output


def test_pad_list_with_pads(mock_git_engine):
    """Test `pad list` with multiple workpads."""
    mock_pad1 = MagicMock()
    mock_pad1.id = "pad1_id_long"
    mock_pad1.title = "feature-a"
    mock_pad1.status = "active"
    mock_pad1.checkpoints = ["cp1", "cp2"]
    mock_pad1.test_status = "passed"
    mock_pad1.created_at = datetime(2023, 1, 3, 11, 0)

    mock_pad2 = MagicMock()
    mock_pad2.id = "pad2_id_long"
    mock_pad2.title = "bug-fix"
    mock_pad2.status = "pending"
    mock_pad2.checkpoints = []
    mock_pad2.test_status = "failed"
    mock_pad2.created_at = datetime(2023, 1, 4, 14, 0)

    mock_git_engine.list_workpads.return_value = [mock_pad1, mock_pad2]
    runner = CliRunner()
    result = runner.invoke(cli, ['pad', 'list'])

    assert result.exit_code == 0
    assert "ID" in result.output
    assert "Title" in result.output
    assert "Status" in result.output
    assert "feature-a" in result.output
    assert "active" in result.output
    assert "✅ passed" in result.output
    assert "bug-fix" in result.output
    assert "pending" in result.output
    assert "❌ failed" in result.output

def test_pad_info_found(mock_git_engine):
    """Test `pad info` for an existing workpad."""
    mock_pad = MagicMock()
    mock_pad.id = "pad1"
    mock_pad.title = "test-pad"
    mock_pad.repo_id = "repo1"
    mock_pad.branch_name = "pad/test-pad"
    mock_pad.status = "active"
    mock_pad.created_at = datetime(2023, 1, 1)
    mock_pad.checkpoints = ["cp1", "cp2"]
    mock_pad.test_status = "passed"
    mock_git_engine.get_workpad.return_value = mock_pad

    runner = CliRunner()
    result = runner.invoke(cli, ['pad', 'info', 'pad1'])

    assert result.exit_code == 0
    assert "Workpad: pad1" in result.output
    assert "Title: test-pad" in result.output
    assert "Repo: repo1" in result.output
    assert "Branch: pad/test-pad" in result.output
    assert "Status: active" in result.output
    assert "Checkpoints: 2" in result.output
    assert "Last Test: passed" in result.output

def test_pad_diff_found(mock_git_engine):
    """Test `pad diff` for an existing workpad."""
    mock_pad = MagicMock()
    mock_git_engine.get_workpad.return_value = mock_pad
    mock_git_engine.get_diff.return_value = "diff --git a/file.txt b/file.txt\n--- a/file.txt\n+++ b/file.txt"

    runner = CliRunner()
    result = runner.invoke(cli, ['pad', 'diff', 'pad1'])

    assert result.exit_code == 0
    assert "diff --git" in result.output
    mock_git_engine.get_diff.assert_called_once_with('pad1')


def test_pad_diff_not_found(mock_git_engine):
    """Test `pad diff` for a non-existent workpad."""
    mock_git_engine.get_workpad.return_value = None
    runner = CliRunner()
    result = runner.invoke(cli, ['pad', 'diff', 'nonexistent'])
    assert result.exit_code != 0
    assert "Workpad nonexistent not found" in result.output


def test_pad_promote_success(mock_git_engine):
    """Test `pad promote` successfully."""
    mock_pad = MagicMock()
    mock_pad.title = "feature-to-promote"
    mock_pad.branch_name = "pad/feature"
    mock_git_engine.get_workpad.return_value = mock_pad
    mock_git_engine.can_promote.return_value = True
    mock_git_engine.promote_workpad.return_value = "abcdef123"

    runner = CliRunner()
    result = runner.invoke(cli, ['pad', 'promote', 'pad1'])

    assert result.exit_code == 0
    assert "Promoting workpad" in result.output
    assert "Workpad promoted to trunk!" in result.output
    assert "Commit: abcdef123" in result.output
    mock_git_engine.promote_workpad.assert_called_once_with('pad1')


def test_pad_promote_not_fast_forward(mock_git_engine):
    """Test `pad promote` when not fast-forwardable."""
    mock_pad = MagicMock()
    mock_git_engine.get_workpad.return_value = mock_pad
    mock_git_engine.can_promote.return_value = False

    runner = CliRunner()
    result = runner.invoke(cli, ['pad', 'promote', 'pad1'])

    assert result.exit_code != 0
    assert "Cannot promote: not fast-forward-able" in result.output
    assert "Trunk has diverged" in result.output


def test_test_run_success(mock_git_engine, mock_test_orchestrator, mock_state_manager):
    """Test `test run` with successful test execution."""
    mock_pad = MagicMock()
    mock_pad.title = "test-pad"
    mock_git_engine.get_workpad.return_value = mock_pad

    results = [
        TestResult(name='unit-tests', status=TestStatus.PASSED, duration_ms=1234, exit_code=0, stdout='', stderr='', mode='subprocess', log_path=Path('/log/unit.txt')),
        TestResult(name='integration', status=TestStatus.PASSED, duration_ms=5678, exit_code=0, stdout='', stderr='', mode='subprocess', log_path=Path('/log/int.txt')),
    ]
    mock_test_orchestrator.run_tests.return_value = results
    mock_test_orchestrator.get_summary.return_value = {
        'total': 2, 'passed': 2, 'failed': 0, 'timeout': 0, 'skipped': 0, 'status': 'green'
    }

    runner = CliRunner()
    result = runner.invoke(cli, ['test', 'run', 'pad1', '--target', 'full'])

    assert result.exit_code == 0, result.output
    assert "Test Execution" in result.output
    assert "Workpad: test-pad" in result.output
    assert "✅ passed" in result.output
    assert "Test Summary" in result.output
    assert "All tests passed!" in result.output
    mock_test_orchestrator.run_tests.assert_called_once()

    mock_state_manager.create_test_run.assert_called_once_with('pad1', 'full')
    assert mock_state_manager.update_test_run.call_count == 2
    first_call = mock_state_manager.update_test_run.call_args_list[0]
    assert first_call.args[0] == 'run-123'
    assert first_call.kwargs['status'] == 'running'

    final_call = mock_state_manager.update_test_run.call_args_list[-1]
    assert final_call.args[0] == 'run-123'
    final_kwargs = final_call.kwargs
    assert final_kwargs['status'] == 'passed'
    assert final_kwargs['total_tests'] == 2
    assert final_kwargs['passed'] == 2
    assert final_kwargs['failed'] == 0
    assert final_kwargs['skipped'] == 0
    assert final_kwargs['duration_ms'] == 1234 + 5678
    assert len(final_kwargs['tests']) == 2
    assert final_kwargs['tests'][0].name == 'unit-tests'
    assert final_kwargs['tests'][1].name == 'integration'


def test_test_run_failure(mock_git_engine, mock_test_orchestrator, mock_state_manager):
    """Test `test run` with failed tests."""
    mock_pad = MagicMock()
    mock_pad.title = "failing-pad"
    mock_git_engine.get_workpad.return_value = mock_pad

    results = [
        TestResult(name='unit-tests', status=TestStatus.PASSED, duration_ms=1000, exit_code=0, stdout='', stderr='', mode='subprocess', log_path=Path('log1.txt')),
        TestResult(name='integration', status=TestStatus.FAILED, duration_ms=2000, exit_code=1, stdout='', stderr='', error="Assertion failed", mode='subprocess', log_path=Path('log2.txt')),
    ]
    mock_test_orchestrator.run_tests.return_value = results
    mock_test_orchestrator.get_summary.return_value = {
        'total': 2, 'passed': 1, 'failed': 1, 'timeout': 0, 'skipped': 0, 'status': 'red'
    }

    runner = CliRunner()
    result = runner.invoke(cli, ['test', 'run', 'pad1'])

    assert result.exit_code == 0  # Command itself succeeds
    assert "❌ failed" in result.output
    assert "Tests Require Attention" in result.output
    assert "Some tests failed or timed out" in result.output
    assert "Passed: 1" in result.output
    assert "Failed: 1" in result.output

    mock_state_manager.create_test_run.assert_called_once_with('pad1', 'fast')
    assert mock_state_manager.update_test_run.call_count == 2
    final_kwargs = mock_state_manager.update_test_run.call_args_list[-1].kwargs
    assert final_kwargs['status'] == 'failed'
    assert final_kwargs['passed'] == 1
    assert final_kwargs['failed'] == 1
    assert final_kwargs['total_tests'] == 2
    assert len(final_kwargs['tests']) == 2
    assert final_kwargs['tests'][1].status == 'failed'


def test_test_run_exception_records_state(mock_git_engine, mock_test_orchestrator, mock_state_manager):
    """Ensure exceptions during test execution are captured in state."""
    mock_pad = MagicMock()
    mock_pad.title = "boom-pad"
    mock_git_engine.get_workpad.return_value = mock_pad

    mock_test_orchestrator.run_tests.side_effect = RuntimeError("boom")

    runner = CliRunner()
    result = runner.invoke(cli, ['test', 'run', 'pad1'])

    assert result.exit_code != 0
    assert "Test Execution Failed" in result.output

    mock_state_manager.create_test_run.assert_called_once_with('pad1', 'fast')
    assert mock_state_manager.update_test_run.call_count == 2
    final_kwargs = mock_state_manager.update_test_run.call_args_list[-1].kwargs
    assert final_kwargs['status'] == 'failed'
    assert final_kwargs['total_tests'] == 1
    assert len(final_kwargs['tests']) == 1
    assert final_kwargs['tests'][0].status == 'error'
    assert final_kwargs['tests'][0].error == 'boom'


def test_test_run_pad_not_found(mock_git_engine, mock_test_orchestrator, mock_state_manager):
    """Test `test run` for a non-existent workpad."""
    mock_git_engine.get_workpad.return_value = None
    runner = CliRunner()
    result = runner.invoke(cli, ['test', 'run', 'nonexistent'])
    assert result.exit_code != 0
    assert "Workpad nonexistent not found" in result.output
    mock_state_manager.create_test_run.assert_not_called()


def test_test_run_unexpected_exception(mock_git_engine, mock_test_orchestrator):
    """Test `test run` handles unexpected exceptions correctly with proper variable reference."""
def test_test_run_exception_handler(mock_git_engine, mock_test_orchestrator):
    """Test `test run` exception handler provides workpad context."""
    mock_pad = MagicMock()
    mock_pad.title = "test-pad"
    mock_git_engine.get_workpad.return_value = mock_pad
    
    # Simulate an unexpected exception during test execution
    mock_test_orchestrator.run_tests.side_effect = RuntimeError("Unexpected test orchestrator error")
    
    runner = CliRunner()
    result = runner.invoke(cli, ['test', 'run', 'test-pad-123'])
    
    assert result.exit_code != 0
    assert "Test execution failed" in result.output
    assert "Unexpected test orchestrator error" in result.output
    # Verify the error message uses pad_id correctly (not workpad_id which would cause NameError)
    assert "evogitctl test run test-pad-123" in result.output
    # Make run_tests raise an exception
    mock_test_orchestrator.run_tests.side_effect = Exception("Unexpected test failure")
    
    runner = CliRunner()
    result = runner.invoke(cli, ['test', 'run', 'pad123'])
    
    assert result.exit_code != 0
    assert "Test execution failed" in result.output
    assert "Workpad: pad123" in result.output  # Verify pad_id is shown
    assert "Unexpected test failure" in result.output
