"""Tests for the CLI config commands."""
import pytest
from click.testing import CliRunner
from unittest.mock import MagicMock, patch
from sologit.cli.main import cli as sologit_cli
from sologit.config.manager import ConfigManager
from pathlib import Path
from sologit.config.manager import ConfigManager, SoloGitConfig, AbacusAPIConfig, ModelConfig, BudgetConfig, TestConfig, CISmokeConfig, DeploymentCredentials, TierModelConfig, ModelVariantConfig

@pytest.fixture
def mock_config_manager():
    """Fixture for a mocked ConfigManager."""
    with patch('sologit.cli.main.ConfigManager', autospec=True) as mock_cm_constructor:
        mock_cm_instance = mock_cm_constructor.return_value

        # Create a full, valid config object
        mock_config = SoloGitConfig(
            abacus=AbacusAPIConfig(endpoint="https://api.example.com", api_key="test_api_key_123456789"),
            models=ModelConfig(
                planning=TierModelConfig(primary=ModelVariantConfig(name="model-p", provider="abacus", cost_per_1k_tokens=0.001, max_tokens=1024)),
                coding=TierModelConfig(primary=ModelVariantConfig(name="model-c", provider="abacus", cost_per_1k_tokens=0.001, max_tokens=1024)),
                fast=TierModelConfig(primary=ModelVariantConfig(name="model-f", provider="abacus", cost_per_1k_tokens=0.001, max_tokens=1024)),
            ),
            budget=BudgetConfig(daily_usd_cap=10.0),
            tests=TestConfig(),
            ci=CISmokeConfig(),
            deployments={'test': DeploymentCredentials(deployment_id='abc', deployment_token='123')}
        )

        mock_cm_instance.get_config.return_value = mock_config
        mock_cm_instance.config = mock_config  # Ensure the config attribute is also set

        yield mock_cm_instance

@pytest.fixture
def isolated_cli_runner(tmp_path):
    """Provides a CliRunner within an isolated filesystem."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path) as isolated_dir:
        # Yield both the runner and the path to the isolated directory
        yield runner, Path(isolated_dir)


def test_config_show(mock_config_manager):
    """Test `config show` command."""
    runner = CliRunner()
    result = runner.invoke(sologit_cli, ['config', 'show'])

    assert result.exit_code == 0, result.output
    assert "Solo Git Configuration" in result.output
    assert "https://api.example.com" in result.output
    assert "test_api...6789" in result.output
    assert "$10.00" in result.output


def test_config_show_with_secrets(mock_config_manager):
    """Test `config show --secrets`."""
    mock_config_manager.get_config.return_value.abacus.api_key = "full_secret_key"
    runner = CliRunner()
    result = runner.invoke(sologit_cli, ['config', 'show', '--secrets'])
    assert "full_secret_key" in result.output
    assert "..." not in result.output


def test_config_setup_interactive():
    """Test `config setup` in interactive mode."""
    runner = CliRunner()
    with patch('sologit.cli.config_commands.ConfigManager') as mock_cm:
        mock_instance = mock_cm.return_value
        result = runner.invoke(sologit_cli, ['config', 'setup'], input="my_api_key\ny\n")

        assert result.exit_code == 0
        assert "Solo Git Configuration Setup" in result.output
        assert "Enter your Abacus.ai API key" in result.output
        assert "Configuration saved" in result.output
        mock_instance.set_abacus_credentials.assert_called_with('my_api_key', 'https://api.abacus.ai/v1')


def test_config_setup_non_interactive():
    """Test `config setup` with command-line arguments."""
    runner = CliRunner()
    with patch('sologit.cli.config_commands.ConfigManager') as mock_cm:
        mock_instance = mock_cm.return_value
        result = runner.invoke(sologit_cli, ['config', 'setup', '--api-key', 'key123', '--endpoint', 'http://localhost'])

        assert result.exit_code == 0
        mock_instance.set_abacus_credentials.assert_called_with('key123', 'http://localhost')


def test_config_test_success():
    """Test `config test` with a valid configuration."""
    with patch('sologit.cli.config_commands.ConfigManager') as mock_cm_constructor:
        mock_instance = mock_cm_constructor.return_value
        mock_instance.validate.return_value = (True, [])
        mock_config = MagicMock()
        mock_config.abacus.is_configured.return_value = True
        mock_instance.get_config.return_value = mock_config

        with patch('sologit.cli.config_commands.AbacusClient') as mock_abacus_client:
            mock_abacus_client.return_value.test_connection.return_value = True

            runner = CliRunner()
            result = runner.invoke(sologit_cli, ['config', 'test'])

            assert result.exit_code == 0
            assert "Configuration is valid" in result.output
            assert "API connection successful" in result.output
            assert "All checks passed" in result.output


def test_config_test_validation_fails():
    """Test `config test` when validation fails."""
    with patch('sologit.cli.config_commands.ConfigManager') as mock_cm_constructor:
        mock_instance = mock_cm_constructor.return_value
        mock_instance.validate.return_value = (False, ["Invalid model name"])

        runner = CliRunner()
        result = runner.invoke(sologit_cli, ['config', 'test'], catch_exceptions=False)

        assert result.exit_code != 0
        assert "Configuration Validation Failed" in result.output
        assert "Review the issues below" in result.output
        assert "Invalid model name" in result.output

def test_config_budget_status(mock_config_manager):
    """Test `config budget status` command."""
    with patch('sologit.cli.config_commands.CostGuard') as mock_cost_guard_constructor:
        mock_guard_instance = mock_cost_guard_constructor.return_value
        mock_guard_instance.get_status.return_value = {
            'daily_cap': 10.0,
            'current_cost': 2.5,
            'remaining': 7.5,
            'percentage_used': 25.0,
            'within_budget': True
        }
        runner = CliRunner()
        result = runner.invoke(sologit_cli, ['config', 'budget', 'status'])
        assert result.exit_code == 0
        assert "Solo Git Budget Status" in result.output
        assert "Used Today:     $2.50" in result.output
        assert "Remaining:      $7.50" in result.output
        assert "Usage:          25.0%" in result.output


def test_config_init(isolated_cli_runner):
    """Test `config init`."""
    runner, temp_dir = isolated_cli_runner

    # Set the home directory for the ConfigManager to use the isolated environment
    with patch.object(ConfigManager, 'DEFAULT_CONFIG_FILE', temp_dir / 'config.yaml'):
        result = runner.invoke(sologit_cli, ['config', 'init'])

        assert result.exit_code == 0, result.output
        assert "Created configuration file" in result.output

        config_file = temp_dir / 'config.yaml'
        assert config_file.exists()
        content = config_file.read_text()
        assert "abacus:" in content
        assert "models:" in content

def test_config_init_force(isolated_cli_runner):
    """Test `config init --force`."""
    runner, temp_dir = isolated_cli_runner
    config_file = temp_dir / 'config.yaml'
    config_file.write_text("old content")

    with patch.object(ConfigManager, 'DEFAULT_CONFIG_FILE', config_file):
        result = runner.invoke(sologit_cli, ['config', 'init', '--force'])

        assert result.exit_code == 0
        content = config_file.read_text()
        assert "old content" not in content
        assert "abacus:" in content


def test_config_path(isolated_cli_runner):
    """Test `config path` command."""
    runner, temp_dir = isolated_cli_runner
    expected_path = temp_dir / "sologit/config.yaml"
    with patch.object(ConfigManager, 'DEFAULT_CONFIG_FILE', expected_path):
        result = runner.invoke(sologit_cli, ['config', 'path'])
        assert result.exit_code == 0
        assert str(expected_path) in result.output

def test_config_env_template(isolated_cli_runner):
    """Test `config env-template` command."""
    runner, temp_dir = isolated_cli_runner
    result = runner.invoke(sologit_cli, ['config', 'env-template'])
    assert result.exit_code == 0
    assert "Created .env.example" in result.output
    env_file = temp_dir / '.env.example'
    assert env_file.exists()
    content = env_file.read_text()
    assert "ABACUS_API_KEY" in content
