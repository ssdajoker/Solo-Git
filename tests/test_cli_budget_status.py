"""Tests for the `evogitctl config budget status` command."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from sologit.cli.main import cli
from sologit.config.manager import ConfigManager


def test_budget_status_cli(monkeypatch):
    """Ensure the budget status command surfaces persisted usage."""

    runner = CliRunner()
    with runner.isolated_filesystem():
        home_dir = Path.cwd()
        monkeypatch.setenv('HOME', str(home_dir))
        config_path = home_dir / '.sologit' / 'config.yaml'

        manager = ConfigManager(config_path=config_path)
        manager.save_config()

        result = runner.invoke(
            cli,
            ['--config', str(config_path), 'config', 'budget', 'status'],
        )

        assert result.exit_code == 0
        assert "Solo Git Budget Status" in result.output
