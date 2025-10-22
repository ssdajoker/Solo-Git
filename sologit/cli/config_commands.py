"""Configuration-related CLI commands for Solo Git."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, NoReturn, Optional

import click
from rich.console import Console

from sologit.api.client import AbacusClient
from sologit.config.manager import ConfigManager
from sologit.config.templates import DEFAULT_CONFIG_TEMPLATE, ENV_TEMPLATE
from sologit.orchestration.cost_guard import CostGuard
from sologit.ui.formatter import RichFormatter
from sologit.ui.theme import theme
from sologit.utils.logger import get_logger

logger = get_logger(__name__)

formatter = RichFormatter()


def set_formatter_console(console: Console) -> None:
    """Allow the caller to reuse an existing Rich console instance."""

    formatter.set_console(console)


def abort_with_error(
    message: str,
    details: Optional[str] = None,
    *,
    title: Optional[str] = None,
    help_text: Optional[str] = None,
    tip: Optional[str] = None,
    suggestions: Optional[Iterable[str]] = None,
    docs_url: Optional[str] = None,
) -> NoReturn:
    """Display a formatted error panel with context and abort the command."""

    formatter.print_error(
        title or "Configuration Error",
        message,
        help_text=help_text or "Review the command usage below and update the provided arguments.",
        tip=tip or "Run 'evogitctl config --help' to list available options.",
        suggestions=suggestions or [
            "evogitctl config show",
            "evogitctl config setup",
        ],
        docs_url=docs_url or "docs/SETUP.md#configuration",
        details=details,
    )
    raise click.Abort()


def _ensure_context(ctx: click.Context) -> Dict[str, object]:
    """Ensure the Click context carries a dictionary object."""

    ctx.ensure_object(dict)
    return ctx.obj  # type: ignore[return-value]


def _get_config_manager(ctx: click.Context) -> ConfigManager:
    """Fetch or create a ConfigManager stored on the Click context."""

    context_obj = _ensure_context(ctx)
    manager = context_obj.get("config")  # type: ignore[assignment]
    if manager is None:
        manager = ConfigManager()
        context_obj["config"] = manager
    return manager


def _mask_secret(secret: Optional[str]) -> str:
    """Return a masked representation of a secret value."""

    if not secret:
        return "<not configured>"
    if len(secret) <= 12:
        return secret
    return f"{secret[:8]}...{secret[-4:]}"


def _format_currency(amount: Optional[float]) -> str:
    """Return a USD currency string for display."""

    if amount is None:
        return "$0.00"
    return f"${amount:0.2f}"


@click.group(name="config")
def config_group() -> None:
    """Configuration management commands."""


@config_group.command(name="show")
@click.option("--secrets/--no-secrets", default=False, help="Show API keys (masked by default)")
@click.pass_context
def show_config(ctx: click.Context, secrets: bool) -> None:
    """Display the current Solo Git configuration."""

    config_manager = _get_config_manager(ctx)
    config = config_manager.get_config()

    formatter.print_header("Solo Git Configuration")

    api_table = formatter.table(headers=["Field", "Value"])
    api_table.add_row("Endpoint", config.abacus.endpoint)
    api_key_display = config.abacus.api_key if secrets else _mask_secret(config.abacus.api_key)
    api_table.add_row("API Key", api_key_display)
    formatter.console.print(api_table)

    budget_table = formatter.table(headers=["Budget", "Value"])
    budget_table.add_row("Daily Cap", _format_currency(getattr(config.budget, "daily_usd_cap", None)))
    formatter.console.print(budget_table)


@config_group.command(name="setup")
@click.option("--api-key", help="Abacus.ai API key")
@click.option("--endpoint", help="Abacus.ai API endpoint", default="https://api.abacus.ai/v1")
@click.option("--interactive/--no-interactive", default=True, help="Interactive setup mode")
def setup_config(api_key: Optional[str], endpoint: Optional[str], interactive: bool) -> None:
    """Guided Abacus.ai configuration setup."""

    formatter.print_header("Solo Git Configuration Setup")
    formatter.print_info("Guiding you through Abacus.ai credential setup.")

    config_manager = ConfigManager()

    if config_manager.has_abacus_credentials() is True and interactive:
        formatter.print_warning("Existing configuration detected.")
        if not click.confirm("Configuration already exists. Overwrite?"):
            formatter.print_info("Keeping existing configuration.")
            return

    if interactive and not api_key:
        formatter.print_panel(
            "To use Solo Git you need Abacus.ai API credentials.\nGenerate an API key from https://abacus.ai.",
            title="Abacus.ai Credentials",
        )
        api_key = click.prompt("Enter your Abacus.ai API key", hide_input=True)
        if click.confirm("Use default endpoint (https://api.abacus.ai/v1)?", default=True):
            endpoint = "https://api.abacus.ai/v1"
        else:
            endpoint = click.prompt("Enter custom API endpoint")

    if not api_key:
        abort_with_error(
            "API key is required",
            title="Configuration Incomplete",
            help_text="Provide your Abacus.ai API key using --api-key or rerun this command in interactive mode to enter it securely.",
            tip="You can export ABACUS_API_KEY in your shell and rerun 'evogitctl config setup --no-interactive'.",
            suggestions=[
                "evogitctl config setup --interactive",
                "export ABACUS_API_KEY=...",
            ],
        )

    try:
        config_manager.set_abacus_credentials(api_key, endpoint or "https://api.abacus.ai/v1")
        config_path = Path(getattr(config_manager, "config_path", ConfigManager.DEFAULT_CONFIG_FILE))
        formatter.print_success_panel(
            f"Configuration saved to [bold]{config_path}[/bold]",
            title="Configuration Saved",
        )

        formatter.print_subheader("Next Steps")
        formatter.print_bullet_list(
            [
                "Test the configuration: evogitctl config test",
                "View configuration: evogitctl config show",
                "Initialize a repo: evogitctl repo init --zip app.zip",
            ],
            icon=theme.icons.arrow_right,
            style=theme.colors.blue,
        )
    except Exception as exc:  # pragma: no cover - surfaced via tests with mocks
        abort_with_error(
            "Error saving configuration",
            str(exc),
            title="Configuration Write Failed",
            help_text="Verify that the destination directory is writable and that the configuration file is not locked by another process.",
            tip="Run again with elevated permissions only if absolutely necessary.",
            suggestions=[
                "Check filesystem permissions",
                "evogitctl config show",
            ],
        )


@config_group.command(name="test")
def test_config() -> None:
    """Validate configuration and test API connectivity."""

    formatter.print_header("Solo Git Configuration Test")

    config_manager = ConfigManager()
    is_valid, issues = config_manager.validate()

    if not is_valid:
        abort_with_error(
            "Configuration Validation Failed",
            "\n".join(issues),
            title="Configuration Validation Failed",
            help_text="Review the issues below and update your configuration.",
            tip="Run 'evogitctl config show' to inspect the current values.",
        )

    config = config_manager.get_config()
    if not config.abacus.is_configured():
        abort_with_error(
            "Abacus.ai credentials are not configured",
            title="Configuration Incomplete",
            help_text="Run 'evogitctl config setup' to provide API credentials.",
        )

    client = AbacusClient(config.abacus)
    connection_ok = client.test_connection()

    formatter.print_success("Configuration is valid")
    if connection_ok:
        formatter.print_success("API connection successful")
        formatter.print_success("All checks passed")
    else:
        formatter.print_warning("Configuration saved, but API connection failed")


@config_group.group(name="budget")
def budget_group() -> None:
    """Budget monitoring commands."""


@budget_group.command(name="status")
def budget_status() -> None:
    """Show current budget usage."""

    formatter.print_header("Solo Git Budget Status")

    config_manager = ConfigManager()
    guard = CostGuard(config_manager)
    status = guard.get_status()

    within_budget = status.get("within_budget", True)
    icon = theme.icons.success if within_budget else theme.icons.warning
    color = theme.colors.success if within_budget else theme.colors.warning

    formatter.console.print(
        f"[{color}]{icon}[/{color}] Budget status: {'Within budget' if within_budget else 'Over budget'}"
    )
    formatter.console.print(f"Daily Cap:      {_format_currency(status.get('daily_cap'))}")
    formatter.console.print(f"Used Today:     {_format_currency(status.get('current_cost'))}")
    formatter.console.print(f"Remaining:      {_format_currency(status.get('remaining'))}")
    formatter.console.print(f"Usage:          {status.get('percentage_used', 0)}%")


@config_group.command(name="init")
@click.option("--force", is_flag=True, help="Overwrite existing config file if present")
def init_config(force: bool) -> None:
    """Create a default configuration file."""

    target_path = Path(ConfigManager.DEFAULT_CONFIG_FILE).expanduser()
    if target_path.exists() and not force:
        formatter.print_warning("Configuration file already exists. Use --force to overwrite.")
        return

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(DEFAULT_CONFIG_TEMPLATE)
    formatter.print_success("Created configuration file at %s" % target_path)


@config_group.command(name="path")
def config_path() -> None:
    """Print the resolved path to the configuration file."""

    target_path = Path(ConfigManager.DEFAULT_CONFIG_FILE).expanduser()
    formatter.print_info(str(target_path))


@config_group.command(name="env-template")
def config_env_template() -> None:
    """Generate a .env.example file with required variables."""

    env_path = Path(".env.example")
    env_path.write_text(ENV_TEMPLATE)
    formatter.print_success("Created .env.example")
