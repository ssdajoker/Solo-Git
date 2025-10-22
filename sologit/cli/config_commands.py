
"""
Configuration commands for Solo Git CLI.

Provides commands to setup, view, and validate configuration.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, NoReturn, Optional, cast

import click
from rich.console import Console

from sologit.api.client import AbacusClient
from sologit.config.manager import ConfigManager
from sologit.config.templates import DEFAULT_CONFIG_TEMPLATE, ENV_TEMPLATE
from sologit.orchestration.cost_guard import CostGuard, BudgetConfig
from sologit.utils.logger import get_logger
from sologit.ui.formatter import RichFormatter
from sologit.ui.theme import theme

logger = get_logger(__name__)


formatter = RichFormatter()


def set_formatter_console(console: Console) -> None:
    """Configure the shared console instance."""
    formatter.set_console(console)


def _ensure_context(ctx: click.Context) -> Dict[str, Any]:
    """Ensure the Click context has an initialized object dictionary and return it."""
    ctx.ensure_object(dict)
    return cast(Dict[str, Any], ctx.obj)


def _get_config_manager(ctx: click.Context) -> ConfigManager:
    """Retrieve a ConfigManager instance from the context or create one."""
    context_obj = _ensure_context(ctx)
    config_manager = context_obj.get('config')
    if config_manager is None:
        config_manager = ConfigManager()
        context_obj['config'] = config_manager
    return config_manager


def abort_with_error(message: str, details: Optional[str] = None) -> NoReturn:
    """Display a formatted error and exit."""
    plain_message = f"Error: {message}"
    formatter.print_error(plain_message)

    content = f"[bold]{plain_message}[/bold]"
    if details:
        content += f"\n\n{details}"
    formatter.print_error_panel(content)
    sys.exit(1)

@click.group(name='config')
def config_group() -> None:
    """Configuration management commands."""
    pass


@config_group.command(name='setup')
@click.option('--api-key', help='Abacus.ai API key')
@click.option('--endpoint', help='Abacus.ai API endpoint',
              default='https://api.abacus.ai/v1')
@click.option('--interactive/--no-interactive', default=True,
              help='Interactive setup mode')
def setup_config(api_key: Optional[str], endpoint: Optional[str], interactive: bool) -> None:
    """
    Setup Solo Git configuration.
    
    Guides you through configuring API credentials and basic settings.
    """
    formatter.print_header("Solo Git Configuration Setup")
    formatter.print_info("Guiding you through Abacus.ai credential setup.")

    config_manager = ConfigManager()

    # Check if already configured
    if config_manager.has_abacus_credentials() is True:
        if interactive:
            formatter.print_warning("Existing configuration detected.")
            if not click.confirm("Configuration already exists. Overwrite?"):
                formatter.print_info("Keeping existing configuration.")
                return

    # Interactive mode
    if interactive and not api_key:
        formatter.print_info_panel(
            "To use Solo Git you need Abacus.ai API credentials.\n"
            "Generate an API key from https://abacus.ai.",
            title="Abacus.ai Credentials"
        )

        api_key = click.prompt("Enter your Abacus.ai API key", hide_input=True)

        if click.confirm("Use default endpoint (https://api.abacus.ai/v1)?", default=True):
            endpoint = 'https://api.abacus.ai/v1'
        else:
            endpoint = click.prompt("Enter custom API endpoint")

    # Validate inputs
    if not api_key:
        abort_with_error("API key is required")

    # Save configuration
    try:
        assert api_key is not None
        endpoint_value = endpoint or 'https://api.abacus.ai/v1'
        config_manager.set_abacus_credentials(api_key, endpoint_value)
        config_path = cast(Path, getattr(config_manager, "config_path", ConfigManager.DEFAULT_CONFIG_FILE))
        formatter.print_success_panel(
            f"Configuration saved to [bold]{config_path}[/bold]",
            title="Configuration Saved"
        )

        formatter.print_subheader("Next Steps")
        formatter.print_bullet_list([
            "Test the configuration: evogitctl config test",
            "View configuration: evogitctl config show",
            "Initialize a repo: evogitctl repo init --zip app.zip",
        ], icon=theme.icons.arrow_right, style=theme.colors.blue)

    except Exception as e:
        abort_with_error("Error saving configuration", str(e))


@config_group.command(name='show')
@click.option('--secrets/--no-secrets', default=False,
              help='Show API keys (masked by default)')
@click.pass_context
def show_config(ctx: click.Context, secrets: bool) -> None:
    """Display current configuration."""
    config_manager = _get_config_manager(ctx)

    config = config_manager.get_config()

    formatter.print_header("Solo Git Configuration")

    api_table = formatter.table(headers=["Field", "Value"])
    api_table.add_row("Endpoint", config.abacus.endpoint)
    if config.abacus.api_key:
        api_value = config.abacus.api_key if secrets else config.abacus.api_key[:8] + "..." + config.abacus.api_key[-4:]
        if not secrets:
            api_value += " (use --secrets to show)"
        api_table.add_row("API Key", api_value)
    else:
        api_table.add_row("API Key", f"[{theme.colors.error}]Not configured[/{theme.colors.error}]")
    formatter.print_info_panel("Abacus.ai API Settings", title="API")
    formatter.console.print(api_table)

    def render_tier(label: str, tier_config: Any) -> None:
        primary = tier_config.primary
        row_value = (
            f"{primary.name} [{primary.provider}]\n"
            f"${primary.cost_per_1k_tokens:.4f}/1k • max {primary.max_tokens} tokens"
        )
        model_table.add_row(label, row_value)
        if tier_config.fallback:
            fallback = tier_config.fallback
            fallback_value = (
                f"Fallback: {fallback.name} [{fallback.provider}]\n"
                f"${fallback.cost_per_1k_tokens:.4f}/1k • max {fallback.max_tokens} tokens"
            )
            model_table.add_row("", fallback_value)

    model_table = formatter.table(headers=["Tier", "Model Details"])
    render_tier("Planning", config.models.planning)
    render_tier("Coding", config.models.coding)
    render_tier("Fast", config.models.fast)
    formatter.print_info_panel("Model configuration tiers", title="AI Models")
    formatter.console.print(model_table)

    budget_table = formatter.table(headers=["Setting", "Value"])
    budget_table.add_row("Daily Cap", f"${config.budget.daily_usd_cap:.2f}")
    budget_table.add_row("Alert Threshold", f"{config.budget.alert_threshold * 100:.0f}%")
    budget_table.add_row("Track by Model", str(config.budget.track_by_model))
    formatter.print_info_panel("Budget guardrails", title="Budget")
    formatter.console.print(budget_table)

    workflow_table = formatter.table(headers=["Setting", "Value"])
    workflow_table.add_row("Auto-merge on green", str(config.promote_on_green))
    workflow_table.add_row("Auto-rollback", str(config.rollback_on_ci_red))
    workflow_table.add_row("Workpad TTL", f"{config.workpad_ttl_days} days")
    formatter.print_info_panel("Workflow automation", title="Workflow")
    formatter.console.print(workflow_table)

    paths_table = formatter.table(headers=["Path", "Value"])
    config_path = getattr(config_manager, "config_path", ConfigManager.DEFAULT_CONFIG_FILE)
    paths_table.add_row("Config file", str(config_path))
    paths_table.add_row("Repositories", str(config.repos_path))
    formatter.print_info_panel("Paths", title="Filesystem")
    formatter.console.print(paths_table)


@config_group.command(name='test')
@click.pass_context
def test_config(ctx: click.Context) -> None:
    """Test API connection and validate configuration."""
    config_manager = _get_config_manager(ctx)

    formatter.print_header("Testing Solo Git Configuration")

    # Validate configuration
    is_valid, errors = config_manager.validate()
    error_messages: List[str] = errors

    if not is_valid:
        formatter.print_error_panel(
            "Configuration validation failed. Review the following issues:",
            title="Validation"
        )
        error_table = formatter.table(headers=["Issues"])
        for error in error_messages:
            error_table.add_row(error)
            formatter.print_error(error)
        formatter.console.print(error_table)
        sys.exit(1)

    formatter.print_success("Configuration is valid")

    # Test API connection
    config = config_manager.get_config()
    if not config.abacus.is_configured():
        formatter.print_warning("Abacus.ai API not configured.")
        formatter.print_info("Run: evogitctl config setup")
        sys.exit(1)

    formatter.print_info("Testing Abacus.ai API connection...")

    try:
        client = AbacusClient(config.abacus)
        result = client.test_connection()

        if result:
            formatter.print_success_panel(
                f"Endpoint: {config.abacus.endpoint}",
                title="API Connection Successful"
            )
            formatter.print_success("API connection successful")
        else:
            abort_with_error("API connection failed")

    except Exception as e:
        abort_with_error("API connection failed", str(e))

    formatter.print_success_panel(
        "All checks passed! Solo Git is ready to use.",
        title="Ready"
    )


@config_group.group(name='budget')
@click.pass_context
def budget_group(ctx: click.Context) -> None:
    """Budget monitoring commands."""
    context_obj = _ensure_context(ctx)
    if 'config' not in context_obj:
        context_obj['config'] = ConfigManager()


@budget_group.command(name='status')
@click.pass_context
def budget_status(ctx: click.Context) -> None:
    """Show current AI budget status."""
    config_manager = _get_config_manager(ctx)

    config = config_manager.get_config()
    guard_config = BudgetConfig(
        daily_usd_cap=config.budget.daily_usd_cap,
        alert_threshold=config.budget.alert_threshold,
        track_by_model=config.budget.track_by_model,
    )
    cost_guard = CostGuard(guard_config)
    status: Dict[str, Any] = cost_guard.get_status()

    formatter.print_header("Solo Git Budget Status")
    summary_table = formatter.table(headers=["Metric", "Value"])
    summary_table.add_row("Daily Cap", f"${status['daily_cap']:.2f}")
    summary_table.add_row("Used Today", f"${status['current_cost']:.2f}")
    summary_table.add_row("Remaining", f"${status['remaining']:.2f}")
    summary_table.add_row("Usage", f"{status['percentage_used']:.1f}%")
    budget_icon = theme.icons.success if status['within_budget'] else theme.icons.warning
    budget_color = theme.colors.success if status['within_budget'] else theme.colors.warning
    summary_table.add_row("Within Budget", f"[{budget_color}]{budget_icon} {'Yes' if status['within_budget'] else 'Check alerts'}[/{budget_color}]")
    formatter.console.print(summary_table)

    # Provide simple textual summary for log parsing/tests
    formatter.print_info(f"Daily Cap:       ${status['daily_cap']:.2f}")
    formatter.print_info(f"Used Today:     ${status['current_cost']:.2f}")
    formatter.print_info(f"Remaining:      ${status['remaining']:.2f}")
    formatter.print_info(f"Usage:          {status['percentage_used']:.1f}%")

    if status.get('alerts'):
        alerts_panel = "\n".join(
            f"[{theme.colors.warning}]{alert['timestamp']}[/] {alert['level'].upper()}: {alert['message']}"
            for alert in status['alerts']
        )
        formatter.print_warning("Budget alerts detected.")
        formatter.print_info_panel(alerts_panel, title="Alerts")

    breakdown: Dict[str, Any] = status.get('usage_breakdown') or {}
    if breakdown:
        breakdown_table = formatter.table(headers=["Metric", "Value"])
        breakdown_table.add_row(
            "Total Tokens",
            f"{breakdown.get('total_tokens', 0)} in {breakdown.get('calls_count', 0)} calls"
        )
        if breakdown.get('by_model'):
            model_lines = [f"{model}: ${cost:.4f}" for model, cost in breakdown['by_model'].items()]
            breakdown_table.add_row("By Model", "\n".join(model_lines))
        if breakdown.get('by_task'):
            task_lines = [f"{task}: ${cost:.4f}" for task, cost in breakdown['by_task'].items()]
            breakdown_table.add_row("By Task", "\n".join(task_lines))
        formatter.print_info_panel("Usage breakdown", title="Detailed Usage")
        formatter.console.print(breakdown_table)

    last_usage = cast(Optional[Dict[str, Any]], status.get('last_usage'))
    if last_usage:
        last_panel = (
            f"Timestamp: {last_usage['timestamp']}\n"
            f"Model: {last_usage['model']}\n"
            f"Cost: ${last_usage['cost_usd']:.4f}\n"
            f"Tokens: {last_usage['total_tokens']}"
        )
        formatter.print_info_panel(last_panel, title="Last Usage")


@config_group.command(name='init')
@click.option('--force', is_flag=True, help='Overwrite existing config file')
def init_config(force: bool) -> None:
    """Initialize a new configuration file with defaults."""
    config_path = ConfigManager.DEFAULT_CONFIG_FILE
    
    formatter.print_header("Initialize Configuration")

    if config_path.exists() and not force:
        abort_with_error(
            "Configuration file already exists",
            f"Path: {config_path}\nUse --force to overwrite, or edit it manually."
        )

    # Create config directory
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Write template
    with open(config_path, 'w') as f:
        f.write(DEFAULT_CONFIG_TEMPLATE)

    formatter.print_success_panel(
        f"Created configuration file at [bold]{config_path}[/bold]",
        title="Config Initialized"
    )
    formatter.print_info("Edit the file to add your API credentials or run: evogitctl config setup")


@config_group.command(name='env-template')
def env_template() -> None:
    """Generate .env template file."""
    env_path = Path.cwd() / '.env.example'
    
    formatter.print_header("Generate .env Template")

    with open(env_path, 'w') as f:
        f.write(ENV_TEMPLATE)

    formatter.print_success_panel(
        f"Created .env.example at [bold]{env_path}[/bold]",
        title="Environment Template"
    )
    formatter.print_info("Copy to .env and fill in your values: cp .env.example .env")


@config_group.command(name='path')
def config_path() -> None:
    """Show configuration file path."""
    formatter.print_header("Configuration Path")
    formatter.print_info(str(ConfigManager.DEFAULT_CONFIG_FILE))

