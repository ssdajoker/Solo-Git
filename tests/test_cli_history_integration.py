import pytest

from sologit.cli.main import _execute_cli_command
from sologit.ui.history import (
    CommandType,
    get_command_history,
    reset_command_history,
)


@pytest.fixture()
def cli_history_env(tmp_path, monkeypatch):
    """Provide isolated history/config directories for CLI history tests."""
    home = tmp_path / "home"
    home.mkdir()

    def _home():
        return home

    # Redirect Path.home() usages to the isolated directory across modules
    monkeypatch.setattr("sologit.ui.history.Path.home", _home)
    monkeypatch.setattr("sologit.cli.main.Path.home", _home)
    monkeypatch.setattr("sologit.config.manager.Path.home", _home)

    config_dir = home / ".sologit"
    config_dir.mkdir(parents=True, exist_ok=True)

    # Ensure ConfigManager uses the isolated config directory
    monkeypatch.setattr(
        "sologit.config.manager.ConfigManager.DEFAULT_CONFIG_DIR",
        config_dir,
        raising=False,
    )
    monkeypatch.setattr(
        "sologit.config.manager.ConfigManager.DEFAULT_CONFIG_FILE",
        config_dir / "config.yaml",
        raising=False,
    )

    history_file = config_dir / "history.txt"
    monkeypatch.setattr("sologit.ui.history.CLI_HISTORY_PATH", history_file, raising=False)

    # Reset global history state before and after each test
    reset_command_history()
    yield history_file
    reset_command_history()


def test_execute_cli_command_records_history(cli_history_env):
    """Executing a CLI command should capture history and append to the log file."""
    exit_code = _execute_cli_command(["hello"])

    assert exit_code == 0

    history = get_command_history()
    entries = history.get_history(limit=1)
    assert entries, "Expected a CLI history entry to be recorded"

    entry = entries[0]
    assert entry.type == CommandType.CLI_COMMAND
    assert entry.description == "hello"
    assert entry.result is not None
    assert entry.result.get("exit_code") == 0

    persisted_lines = cli_history_env.read_text(encoding="utf-8").strip().splitlines()
    assert "hello" in persisted_lines


def test_command_history_persists_between_sessions(cli_history_env):
    """Structured command history should reload from disk across sessions."""
    exit_code = _execute_cli_command(["hello"])
    assert exit_code == 0

    # Simulate a new CLI session
    reset_command_history()
    history = get_command_history()

    entries = history.get_history(limit=1)
    assert entries, "Expected persisted history to reload"

    entry = entries[0]
    assert entry.description == "hello"
    assert entry.type == CommandType.CLI_COMMAND
    assert entry.result is not None
    assert entry.result.get("exit_code") == 0

    # The plain-text CLI history file should retain the command as well
    assert "hello" in history.get_recent_cli_history()
