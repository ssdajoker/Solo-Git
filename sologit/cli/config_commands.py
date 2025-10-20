
"""
Configuration commands for Solo Git CLI.

Provides commands to setup, view, and validate configuration.
"""

import click
import sys
from pathlib import Path

from sologit.config.manager import ConfigManager
from sologit.config.templates import DEFAULT_CONFIG_TEMPLATE, ENV_TEMPLATE
from sologit.orchestration.cost_guard import CostGuard, BudgetConfig
from sologit.utils.logger import get_logger

logger = get_logger(__name__)


@click.group(name='config')
def config_group():
    """Configuration management commands."""
    pass


@config_group.command(name='setup')
@click.option('--api-key', help='Abacus.ai API key')
@click.option('--endpoint', help='Abacus.ai API endpoint', 
              default='https://api.abacus.ai/v1')
@click.option('--interactive/--no-interactive', default=True,
              help='Interactive setup mode')
def setup_config(api_key, endpoint, interactive):
    """
    Setup Solo Git configuration.
    
    Guides you through configuring API credentials and basic settings.
    """
    click.echo("🔧 Solo Git Configuration Setup\n")
    
    config_manager = ConfigManager()
    
    # Check if already configured
    if config_manager.has_abacus_credentials():
        if interactive:
            if not click.confirm("Configuration already exists. Overwrite?"):
                click.echo("Keeping existing configuration.")
                return
    
    # Interactive mode
    if interactive and not api_key:
        click.echo("To use Solo Git, you need Abacus.ai API credentials.")
        click.echo("Get your API key from: https://abacus.ai\n")
        
        api_key = click.prompt("Enter your Abacus.ai API key", hide_input=True)
        
        if click.confirm("Use default endpoint (https://api.abacus.ai/v1)?", default=True):
            endpoint = 'https://api.abacus.ai/v1'
        else:
            endpoint = click.prompt("Enter custom API endpoint")
    
    # Validate inputs
    if not api_key:
        click.echo("❌ Error: API key is required", err=True)
        sys.exit(1)
    
    # Save configuration
    try:
        config_manager.set_abacus_credentials(api_key, endpoint)
        click.echo(f"\n✅ Configuration saved to {config_manager.config_path}")
        
        # Show next steps
        click.echo("\n📋 Next steps:")
        click.echo("  1. Test the configuration: evogitctl config test")
        click.echo("  2. View configuration:     evogitctl config show")
        click.echo("  3. Initialize a repo:      evogitctl repo init --zip app.zip")
        
    except Exception as e:
        click.echo(f"❌ Error saving configuration: {e}", err=True)
        sys.exit(1)


@config_group.command(name='show')
@click.option('--secrets/--no-secrets', default=False,
              help='Show API keys (masked by default)')
@click.pass_context
def show_config(ctx, secrets):
    """Display current configuration."""
    config_manager = ctx.obj.get('config')
    if not config_manager:
        click.echo("❌ No configuration found", err=True)
        sys.exit(1)
    
    config = config_manager.get_config()
    
    click.echo("📋 Solo Git Configuration\n")
    
    # API Configuration
    click.echo("🔐 Abacus.ai API:")
    click.echo(f"  Endpoint:  {config.abacus.endpoint}")
    if config.abacus.api_key:
        if secrets:
            click.echo(f"  API Key:   {config.abacus.api_key}")
        else:
            masked = config.abacus.api_key[:8] + "..." + config.abacus.api_key[-4:]
            click.echo(f"  API Key:   {masked} (use --secrets to show)")
    else:
        click.echo("  API Key:   ❌ Not configured")
    
    # Model Configuration
    click.echo("\n🤖 Models:")

    def _render_tier(label: str, tier_config):
        primary = tier_config.primary
        click.echo(
            f"  {label}:  {primary.name}"
            f" [{primary.provider}]"
            f" • ${primary.cost_per_1k_tokens:.4f}/1k"
            f" • max {primary.max_tokens} tokens"
        )
        if tier_config.fallback:
            fallback = tier_config.fallback
            click.echo(
                f"           ↳ fallback: {fallback.name}"
                f" [{fallback.provider}]"
                f" • ${fallback.cost_per_1k_tokens:.4f}/1k"
                f" • max {fallback.max_tokens} tokens"
            )

    _render_tier("Planning", config.models.planning)
    _render_tier("Coding", config.models.coding)
    _render_tier("Fast", config.models.fast)
    
    # Budget Configuration
    click.echo("\n💰 Budget:")
    click.echo(f"  Daily Cap:       ${config.budget.daily_usd_cap:.2f}")
    click.echo(f"  Alert at:        {config.budget.alert_threshold * 100:.0f}%")
    click.echo(f"  Track by model:  {config.budget.track_by_model}")
    
    # Workflow Settings
    click.echo("\n⚙️  Workflow:")
    click.echo(f"  Auto-merge on green:  {config.promote_on_green}")
    click.echo(f"  Auto-rollback:        {config.rollback_on_ci_red}")
    click.echo(f"  Workpad TTL:          {config.workpad_ttl_days} days")
    
    # Paths
    click.echo("\n📁 Paths:")
    click.echo(f"  Config file:    {config_manager.config_path}")
    click.echo(f"  Repositories:   {config.repos_path}")


@config_group.command(name='test')
@click.pass_context
def test_config(ctx):
    """Test API connection and validate configuration."""
    config_manager = ctx.obj.get('config')
    if not config_manager:
        click.echo("❌ No configuration found", err=True)
        sys.exit(1)
    
    click.echo("🧪 Testing Solo Git Configuration\n")
    
    # Validate configuration
    is_valid, errors = config_manager.validate()
    
    if not is_valid:
        click.echo("❌ Configuration validation failed:")
        for error in errors:
            click.echo(f"  • {error}")
        sys.exit(1)
    
    click.echo("✅ Configuration is valid")
    
    # Test API connection
    config = config_manager.get_config()
    if not config.abacus.is_configured():
        click.echo("\n⚠️  Abacus.ai API not configured")
        click.echo("   Run: evogitctl config setup")
        sys.exit(1)
    
    click.echo("\n🔌 Testing Abacus.ai API connection...")
    
    # Import here to avoid circular dependency
    from sologit.api.client import AbacusClient
    
    try:
        client = AbacusClient(config.abacus)
        result = client.test_connection()
        
        if result:
            click.echo("✅ API connection successful")
            click.echo(f"   Endpoint: {config.abacus.endpoint}")
        else:
            click.echo("❌ API connection failed")
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"❌ API connection failed: {e}")
        sys.exit(1)
    
    click.echo("\n🎉 All checks passed! Solo Git is ready to use.")


@config_group.group(name='budget')
@click.pass_context
def budget_group(ctx):
    """Budget monitoring commands."""

    if 'config' not in ctx.obj:
        ctx.obj['config'] = ConfigManager()


@budget_group.command(name='status')
@click.pass_context
def budget_status(ctx):
    """Show current AI budget status."""

    config_manager: ConfigManager = ctx.obj.get('config')
    if not config_manager:
        click.echo("❌ No configuration found", err=True)
        sys.exit(1)

    config = config_manager.get_config()
    guard_config = BudgetConfig(
        daily_usd_cap=config.budget.daily_usd_cap,
        alert_threshold=config.budget.alert_threshold,
        track_by_model=config.budget.track_by_model,
    )
    cost_guard = CostGuard(guard_config)
    status = cost_guard.get_status()

    click.echo("💰 Solo Git Budget Status\n")
    click.echo(f"Daily Cap:      ${status['daily_cap']:.2f}")
    click.echo(f"Used Today:     ${status['current_cost']:.2f}")
    click.echo(f"Remaining:      ${status['remaining']:.2f}")
    click.echo(f"Usage:          {status['percentage_used']:.1f}%")
    click.echo(f"Within Budget:  {'✅' if status['within_budget'] else '⚠️'}")

    if status.get('alerts'):
        click.echo("\n🚨 Alerts:")
        for alert in status['alerts']:
            click.echo(
                f"  [{alert['timestamp']}] {alert['level'].upper()}: {alert['message']}"
            )

    breakdown = status.get('usage_breakdown') or {}
    if breakdown:
        click.echo("\n📊 Usage Breakdown:")
        click.echo(
            f"  Total Tokens: {breakdown.get('total_tokens', 0)}"
            f" in {breakdown.get('calls_count', 0)} calls"
        )
        if breakdown.get('by_model'):
            click.echo("  By Model:")
            for model, cost in breakdown['by_model'].items():
                click.echo(f"    • {model}: ${cost:.4f}")
        if breakdown.get('by_task'):
            click.echo("  By Task:")
            for task, cost in breakdown['by_task'].items():
                click.echo(f"    • {task}: ${cost:.4f}")

    last_usage = status.get('last_usage')
    if last_usage:
        click.echo("\n🧾 Last Usage:")
        click.echo(
            f"  {last_usage['timestamp']} • {last_usage['model']}"
            f" • ${last_usage['cost_usd']:.4f}"
            f" • {last_usage['total_tokens']} tokens"
        )


@config_group.command(name='init')
@click.option('--force', is_flag=True, help='Overwrite existing config file')
def init_config(force):
    """Initialize a new configuration file with defaults."""
    config_path = ConfigManager.DEFAULT_CONFIG_FILE
    
    if config_path.exists() and not force:
        click.echo(f"Configuration file already exists at {config_path}")
        click.echo("Use --force to overwrite, or edit it manually.")
        sys.exit(1)
    
    # Create config directory
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write template
    with open(config_path, 'w') as f:
        f.write(DEFAULT_CONFIG_TEMPLATE)
    
    click.echo(f"✅ Created configuration file at {config_path}")
    click.echo("\n📝 Edit the file to add your API credentials:")
    click.echo(f"   {config_path}")
    click.echo("\nOr run: evogitctl config setup")


@config_group.command(name='env-template')
def env_template():
    """Generate .env template file."""
    env_path = Path.cwd() / '.env.example'
    
    with open(env_path, 'w') as f:
        f.write(ENV_TEMPLATE)
    
    click.echo(f"✅ Created .env.example at {env_path}")
    click.echo("\n📝 Copy to .env and fill in your values:")
    click.echo("   cp .env.example .env")


@config_group.command(name='path')
def config_path():
    """Show configuration file path."""
    click.echo(ConfigManager.DEFAULT_CONFIG_FILE)

