from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

import click
import io
from click.testing import CliRunner
from rich.console import Console

import pytest

from sologit.cli import commands
from sologit.cli.commands import (
    _parse_test_override,
    _tests_from_config_entries,
    abort_with_error,
    repo,
    set_formatter_console,
)
from sologit.engines.test_orchestrator import TestConfig


ORIGINAL_FORMATTER = commands.formatter


@pytest.fixture(autouse=True)
def reset_singletons():
    commands._git_engine = None
    commands._patch_engine = None
    commands._test_orchestrator = None
    commands._config_manager = None
    commands._git_state_sync = None
    commands.formatter = ORIGINAL_FORMATTER
    yield
    commands._git_engine = None
    commands._patch_engine = None
    commands._test_orchestrator = None
    commands._config_manager = None
    commands._git_state_sync = None
    commands.formatter = ORIGINAL_FORMATTER


def test_abort_with_error_invokes_formatter():
    mock_formatter = Mock()
    mock_formatter.print_error = Mock()
    commands.formatter = mock_formatter

    with pytest.raises(click.Abort):
        abort_with_error("boom", details="stacktrace")

    mock_formatter.print_error.assert_called_once()


def test_parse_test_override_parses_timeout():
    config = _parse_test_override("lint=pytest -m lint:45", default_timeout=60)
    assert isinstance(config, TestConfig)
    assert config.name == "lint"
    assert config.timeout == 45
    assert config.cmd == "pytest -m lint"


def test_tests_from_config_entries_accepts_dicts():
    entries = [
        TestConfig(name="lint", cmd="flake8"),
        {"name": "unit", "cmd": "pytest", "timeout": "30", "depends_on": ["lint"]},
    ]

    tests = _tests_from_config_entries(entries, default_timeout=60)

    assert [t.name for t in tests] == ["lint", "unit"]
    assert tests[1].timeout == 30
    assert tests[1].depends_on == ["lint"]


def test_repo_list_no_repos_outputs_help():
    runner = CliRunner()
    buffer = io.StringIO()
    console = Console(file=buffer, record=True, force_terminal=False, color_system=None)
    set_formatter_console(console)

    fake_engine = Mock()
    fake_engine.list_repos.return_value = []
    with patch("sologit.cli.commands.get_git_engine", return_value=fake_engine):
        result = runner.invoke(repo, ["list"])

    assert result.exit_code == 0
    output = buffer.getvalue()
    assert "No repositories found" in output


def test_repo_list_renders_table_with_repo_details():
    runner = CliRunner()
    buffer = io.StringIO()
    console = Console(file=buffer, record=True, force_terminal=False, color_system=None)
    set_formatter_console(console)

    repo_obj = SimpleNamespace(
        id="repo-1",
        name="Sample Repo",
        trunk_branch="main",
        workpad_count=2,
        created_at=datetime(2024, 1, 1, 12, 0, 0),
    )
    fake_engine = Mock()
    fake_engine.list_repos.return_value = [repo_obj]
    with patch("sologit.cli.commands.get_git_engine", return_value=fake_engine):
        result = runner.invoke(repo, ["list"])

    assert result.exit_code == 0
    output = buffer.getvalue()
    assert "Sample Repo" in output
    assert "repo-1" in output
