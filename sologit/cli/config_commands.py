"""Configuration-related CLI commands for Solo Git."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, NoReturn, Optional, cast

import click
from rich.console import Console

from sologit.api.client import AbacusClient
from sologit.config.manager import ConfigManager
from sologit.config.templates import DEFAULT_CONFIG_TEMPLATE, ENV_TEMPLATE
from sologit.orchestration.cost_guard import BudgetConfig, CostGuard
from sologit.ui.formatter import RichFormatter
from sologit.ui.theme import theme
from sologit.utils.logger import get_logger

logger = get_logger(__name__)

formatter = RichFormatter()


def set_formatter_console(console: Console) -> None:
    """Allow external callers to reuse a shared Rich console."""

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
    """Render a formatted error panel and abort the command."""

    formatter.print_error(
        title or "Configuration Error",
        message,
        help_text=help_text or "Review the command usage below and adjust the provided arguments.",
        tip=tip or "Run 'evogitctl config --help' to list available options.",
        suggestions=suggestions or [
            "evogitctl config show",
            "evogitctl config setup",
        ],
        docs_url=docs_url or "docs/SETUP.md#configuration",
        details=details,
    )
    raise click.Abort()


def _ensure_context(ctx: click.Context) -> Dict[str, Any]:
    """Ensure the Click context stores a mutable dictionary."""

    ctx.ensure_object(dict)
    return ctx.obj  # type: ignore[return-value]


def _get_config_manager(ctx: click.Context) -> ConfigManager:
    """Fetch a ConfigManager attached to the Click context."""

    context_obj = _ensure_context(ctx)
    manager = context_obj.get("config")  # type: ignore[assignment]
    if manager is None:
        manager = ConfigManager()
        context_obj["config"] = manager
    return cast(ConfigManager, manager)


def _mask_secret(secret: Optional[str]) -> str:
    """Return a masked representation of a secret value."""

    if not secret:
        return "<not configured>"
    if len(secret) <= 12:
        return secret
    return f"{secret[:8]}...{secret[-4:]}"


@click.group(name="config")
def config_group() -> None:
    """Configuration management commands."""


@config_group.command(name="setup")
@click.option("--api-key", help="Abacus.ai API key")
@click.option(
    "--endpoint",
    help="Abacus.ai API endpoint",
    default="https://api.abacus.ai/v1",
)
@click.option(
    "--interactive/--no-interactive",
    default=True,
    help="Interactive setup mode",
)
def setup_config(api_key: Optional[str], endpoint: Optional[str], interactive: bool) -> None:
    """Guided Abacus.ai configuration setup."""

    formatter.print_header("Solo Git Configuration Setup")
    formatter.print_info("Guiding you through Abacus.ai credential setup.")

    config_manager = ConfigManager()

    if config_manager.has_abacus_credentials() and interactive:
        formatter.print_warning("Existing configuration detected.")
        if not click.confirm("Configuration already exists. Overwrite?", default=False):
            formatter.print_info("Keeping existing configuration.")
            return

    if interactive and not api_key:
        formatter.print_panel(
            "To use Solo Git you need Abacus.ai API credentials.\n"
            "Generate an API key from https://abacus.ai.",
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
            help_text="Provide your Abacus.ai API key using --api-key or rerun this command in interactive mode.",
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
    except Exception as exc:  # pragma: no cover - surfaced in tests via mocks
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

    formatter.print_subheader("Next Steps")
    formatter.print_bullet_list(
        [
            "Test configuration: evogitctl config test",
            "Check budget status: evogitctl config budget status",
            "Update credentials: evogitctl config setup",
        ],
        icon=theme.icons.arrow_right,
        style=theme.colors.blue,
    )


@config_group.command(name="test")
@click.pass_context
def test_config(ctx: click.Context) -> None:
    """Validate configuration and test the Abacus.ai API connection."""

    config_manager = _get_config_manager(ctx)
    is_valid, issues = config_manager.validate()
    if not is_valid:
        issue_text = "\n".join(f"- {issue}" for issue in issues)
        abort_with_error(
            "Configuration Validation Failed",
            issue_text,
            help_text="Review the issues below and update your configuration file accordingly.",
            tip="Run 'evogitctl config setup' to regenerate a fresh configuration.",
        )

    config = config_manager.get_config()
    if not config.abacus.is_configured():
        abort_with_error(
            "Abacus.ai credentials are missing",
            help_text="Configure your API key first using 'evogitctl config setup'.",
            tip="Ensure ABACUS_API_KEY is exported before running in non-interactive mode.",
        )

    formatter.print_header("Configuration Diagnostics")
    formatter.print_info("Validating local configuration ...")

    try:
        client = AbacusClient(config.abacus)
        connection_ok = client.test_connection()
    except Exception as exc:  # pragma: no cover - surfaced by tests via mocks
        abort_with_error(
            "API connection failed",
            str(exc),
            title="API Connection Failed",
            help_text="Ensure your API key is valid and the endpoint is reachable from this machine.",
            tip="Double-check firewall settings or retry with --verbose to see network diagnostics.",
            suggestions=["evogitctl config show", "evogitctl config setup"],
        )

    if not connection_ok:
        abort_with_error(
            "API connection failed",
            "Unable to connect to Abacus.ai with the provided credentials.",
            title="API Connection Failed",
            help_text="Confirm the API key is active and has permission to call Abacus.ai endpoints.",
            tip="Generate a fresh API key from the Abacus.ai dashboard and try again.",
        )

    formatter.print_success("Configuration is valid")
    formatter.print_success("API connection successful")
    formatter.print_success("All checks passed")


@config_group.group(name="budget")
def budget_group() -> None:
    """Budget monitoring commands."""


@budget_group.command(name="status")
@click.pass_context
def budget_status(ctx: click.Context) -> None:
    """Show the current budget usage summary."""

    config_manager = _get_config_manager(ctx)
    config = config_manager.get_config()

    if not isinstance(config.budget, BudgetConfig):
        abort_with_error(
            "Invalid budget configuration",
            "The 'budget' section of your configuration is missing or malformed.",
            help_text="Please check your configuration file and ensure the 'budget' section is correctly specified.",
            tip="Run 'evogitctl config setup' to regenerate a fresh configuration.",
        )

    guard = CostGuard(config.budget)
    status = guard.get_status()

    formatter.print_header("Solo Git Budget Status")
    summary_table = formatter.table(headers=["Metric", "Value"])
    summary_table.add_row("Daily Cap", f"${status['daily_cap']:.2f}")
    summary_table.add_row("Used Today", f"${status['current_cost']:.2f}")
    summary_table.add_row("Remaining", f"${status['remaining']:.2f}")
    summary_table.add_row("Usage", f"{status['percentage_used']:.1f}%")
    budget_icon = theme.icons.success if status["within_budget"] else theme.icons.warning
    budget_color = theme.colors.success if status["within_budget"] else theme.colors.warning
    summary_table.add_row(
        "Within Budget",
        f"[{budget_color}]{budget_icon} {'Yes' if status['within_budget'] else 'Check alerts'}[/{budget_color}]",
    )
    formatter.console.print(summary_table)

    formatter.print_info(f"Daily Cap:       ${status['daily_cap']:.2f}")
    formatter.print_info(f"Used Today:     ${status['current_cost']:.2f}")
    formatter.print_info(f"Remaining:      ${status['remaining']:.2f}")
    formatter.print_info(f"Usage:          {status['percentage_used']:.1f}%")

    alerts = status.get("alerts")
    if alerts:
        alerts_panel = "\n".join(
            f"[{theme.colors.warning}]{alert['timestamp']}[/] {alert['level'].upper()}: {alert['message']}"
            for alert in alerts
        )
        formatter.print_warning("Budget alerts detected.")
        formatter.print_info_panel(alerts_panel, title="Alerts")

    breakdown: Dict[str, Any] = status.get("usage_breakdown") or {}
    if breakdown:
        breakdown_table = formatter.table(headers=["Metric", "Value"])
        breakdown_table.add_row(
            "Total Tokens",
            f"{breakdown.get('total_tokens', 0)} in {breakdown.get('calls_count', 0)} calls",
        )
        if breakdown.get("by_model"):
            model_lines = [f"{model}: ${cost:.4f}" for model, cost in breakdown["by_model"].items()]
            breakdown_table.add_row("By Model", "\n".join(model_lines))
        if breakdown.get("by_task"):
            task_lines = [f"{task}: ${cost:.4f}" for task, cost in breakdown["by_task"].items()]
            breakdown_table.add_row("By Task", "\n".join(task_lines))
        formatter.print_info_panel("Usage breakdown", title="Detailed Usage")
        formatter.console.print(breakdown_table)

    last_usage = cast(Optional[Dict[str, Any]], status.get("last_usage"))
    if last_usage:
        last_panel = (
            f"Timestamp: {last_usage['timestamp']}\n"
            f"Model: {last_usage['model']}\n"
            f"Cost: ${last_usage['cost_usd']:.4f}\n"
            f"Tokens: {last_usage['total_tokens']}"
        )
        formatter.print_info_panel(last_panel, title="Most Recent Usage")


@config_group.command(name="init")
@click.option("--force", is_flag=True, help="Overwrite existing configuration file")
def init_config(force: bool) -> None:
    """Create the default configuration file on disk."""

    config_path = Path(ConfigManager.DEFAULT_CONFIG_FILE).expanduser()

    if config_path.exists() and not force:
        abort_with_error(
            "Configuration file already exists",
            str(config_path),
            title="Config Exists",
            help_text="Use --force to overwrite the existing file or edit it manually.",
            tip="Run 'evogitctl config show' to inspect the current configuration.",
        )

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(DEFAULT_CONFIG_TEMPLATE.rstrip() + "\n", encoding="utf-8")

    formatter.print_success(f"Created configuration file at {config_path}")


@config_group.command(name="env-template")
def env_template() -> None:
    """Generate .env template file."""

    env_path = Path.cwd() / ".env.example"
    if env_path.exists():
        formatter.print_warning(f"{env_path} already exists; overwriting.")
    env_path.write_text(ENV_TEMPLATE.rstrip() + "\n", encoding="utf-8")
    formatter.print_success(f"Wrote environment template to {env_path}")


@config_group.command(name="path")
def config_path() -> None:
    """Print the path to the active configuration file."""

    config_path = Path(ConfigManager.DEFAULT_CONFIG_FILE).expanduser()
    formatter.print_info(f"Configuration file: {config_path}")
