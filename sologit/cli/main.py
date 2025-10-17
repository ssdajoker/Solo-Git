
"""
Main CLI entry point for Solo Git.

Provides the evogitctl command-line interface with subcommands for
repository management, workpad operations, testing, and AI pairing.
"""

import click
import sys
from pathlib import Path

from sologit import __version__
from sologit.utils.logger import get_logger, setup_logging
from sologit.config.manager import ConfigManager
from sologit.cli import commands
from sologit.cli.config_commands import config_group

logger = get_logger(__name__)


@click.group()
@click.version_option(version=__version__, prog_name="evogitctl")
@click.option(
    "--verbose", "-v", 
    is_flag=True, 
    help="Enable verbose output"
)
@click.option(
    "--config", "-c",
    type=click.Path(exists=True, path_type=Path),
    help="Path to config file (default: ~/.sologit/config.yaml)"
)
@click.pass_context
def cli(ctx, verbose, config):
    """
    Solo Git - Frictionless Git workflow for AI-augmented solo developers.
    
    A paradigm shift in version control that eliminates branches, PRs, and manual reviews,
    replacing them with ephemeral workpads and test-driven auto-merging.
    
    \b
    Quick Start:
      evogitctl config setup              # Configure API credentials
      evogitctl repo init --zip app.zip   # Initialize from zip
      evogitctl pair "add login feature"  # Start AI pairing
    
    \b
    Philosophy:
      • Tests are the review
      • Single trunk, no PRs
      • Ephemeral workpads instead of branches
      • Green tests = instant merge
    """
    # Setup logging
    setup_logging(verbose=verbose)
    
    # Initialize context
    ctx.ensure_object(dict)
    
    # Load configuration
    try:
        config_manager = ConfigManager(config_path=config)
        ctx.obj['config'] = config_manager
        ctx.obj['verbose'] = verbose
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        if verbose:
            raise
        sys.exit(1)


@cli.command()
@click.pass_context
def version(ctx):
    """Show version information."""
    click.echo(f"Solo Git (evogitctl) version {__version__}")
    click.echo(f"Python {sys.version}")
    
    # Show config status
    config = ctx.obj.get('config')
    if config:
        api_configured = config.has_abacus_credentials()
        status = "✓ configured" if api_configured else "✗ not configured"
        click.echo(f"Abacus.ai API: {status}")


@cli.command()
def hello():
    """
    Test command to verify Solo Git is working.
    
    This is a simple "hello world" command that confirms the CLI is properly
    installed and can execute commands.
    """
    click.echo("🏁 Solo Git is ready!")
    click.echo()
    click.echo("Solo Git - where tests are the review and trunk is king.")
    click.echo()
    click.echo("Next steps:")
    click.echo("  1. Configure API credentials: evogitctl config setup")
    click.echo("  2. Initialize a repository:   evogitctl repo init --zip app.zip")
    click.echo("  3. Start pairing with AI:     evogitctl pair 'add feature'")
    click.echo()
    click.echo("Run 'evogitctl --help' for more information.")


# Register command groups
cli.add_command(config_group)

# Phase 1 command groups
from sologit.cli.commands import repo, pad, test
cli.add_command(repo)
cli.add_command(pad)
cli.add_command(test)

# Phase 3 command groups
from sologit.cli.commands import ci
cli.add_command(ci)


@cli.command()
@click.argument('prompt', required=False)
@click.option('--repo', 'repo_id', type=str, help='Repository ID (auto-selects if only one)')
@click.option('--title', type=str, help='Workpad title (derived from prompt if not provided)')
@click.option('--no-test', is_flag=True, help='Skip test execution')
@click.option('--no-promote', is_flag=True, help='Disable automatic promotion')
@click.option('--target', type=click.Choice(['fast', 'full']), default='fast', help='Test target')
@click.pass_context
def pair(ctx, prompt, repo_id, title, no_test, no_promote, target):
    """
    Start AI pair programming session.
    
    The pair command is the heart of Solo Git - it takes a natural language prompt
    and orchestrates the entire workflow: planning, coding, testing, and merging.
    
    \b
    Examples:
      evogitctl pair "add passwordless magic link login"
      evogitctl pair "refactor auth module to use JWT" --no-promote
      evogitctl pair "fix bug in payment processor" --target full
    
    \b
    Workflow:
      1. Creates ephemeral workpad
      2. AI plans implementation
      3. AI generates patch
      4. Applies patch to workpad
      5. Runs tests (unless --no-test)
      6. Auto-promotes if green (unless --no-promote)
    """
    if not prompt:
        click.echo("❌ Error: Prompt is required", err=True)
        click.echo("\nUsage: evogitctl pair \"your task description\"")
        click.echo("\nExample: evogitctl pair \"add user login feature\"")
        raise click.Abort()
    
    from sologit.cli.commands import execute_pair_loop
    
    try:
        execute_pair_loop(
            ctx=ctx,
            prompt=prompt,
            repo_id=repo_id,
            title=title,
            no_test=no_test,
            no_promote=no_promote,
            target=target
        )
    except Exception as e:
        logger.error(f"Pair command failed: {e}", exc_info=ctx.obj.get('verbose', False))
        click.echo(f"\n❌ Pair session failed: {e}", err=True)
        raise click.Abort()


def main():
    """Entry point for the CLI."""
    try:
        cli(obj={})
    except KeyboardInterrupt:
        click.echo("\n\nInterrupted by user.", err=True)
        sys.exit(130)
    except Exception as e:
        logger.exception("Unhandled exception")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

