
"""
Main CLI entry point for Solo Git.

Provides the evogitctl command-line interface with subcommands for
repository management, workpad operations, testing, and AI pairing.
"""

import click
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console

from sologit import __version__
from sologit.utils.logger import get_logger, setup_logging
from sologit.config.manager import ConfigManager
from sologit.cli import commands, config_commands
from sologit.ui.formatter import RichFormatter
from sologit.ui.theme import theme

logger = get_logger(__name__)

console = Console()
formatter = RichFormatter(console)


def abort_with_error(message: str, details: Optional[str] = None) -> None:
    """Display a formatted error and abort the command."""
    content = f"[bold]{message}[/bold]"
    if details:
        content += f"\n\n{details}"
    formatter.print_error_panel(content)
    raise click.Abort()


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
    ctx.obj['console'] = console
    formatter.set_console(console)
    commands.set_formatter_console(console)
    config_commands.set_formatter_console(console)

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
    formatter.print_header("Solo Git Version")
    version_table = formatter.table(headers=["Component", "Value"])
    version_table.add_row("evogitctl", __version__)
    version_table.add_row("Python", sys.version.split()[0])

    config = ctx.obj.get('config')
    if config:
        api_configured = config.has_abacus_credentials()
        status_icon = theme.icons.success if api_configured else theme.icons.warning
        status_color = theme.colors.success if api_configured else theme.colors.warning
        status_text = "Configured" if api_configured else "Missing credentials"
        version_table.add_row(
            "Abacus.ai API",
            f"[{status_color}]{status_icon} {status_text}[/{status_color}]"
        )

    formatter.console.print(version_table)


@cli.command()
def hello():
    """
    Test command to verify Solo Git is working.
    
    This is a simple "hello world" command that confirms the CLI is properly
    installed and can execute commands.
    """
    formatter.print_header("Solo Git")
    formatter.print_success("Solo Git is ready!")
    formatter.print_info("Where tests are the review and trunk is king.")

    formatter.print_subheader("Next steps")
    formatter.print_bullet_list([
        "Configure API credentials: evogitctl config setup",
        "Initialize a repository: evogitctl repo init --zip app.zip",
        "Start pairing with AI: evogitctl pair 'add feature'",
    ], icon=theme.icons.arrow_right, style=theme.colors.blue)
    formatter.print_info("Run 'evogitctl --help' for more information.")


# Register command groups
cli.add_command(config_commands.config_group)

# Phase 1 command groups
from sologit.cli.commands import repo, pad, test
cli.add_command(repo)
cli.add_command(pad)
cli.add_command(test)

# Phase 3 command groups
from sologit.cli.commands import ci
cli.add_command(ci)

# Phase 4: Integrated Heaven Interface commands
try:
    from sologit.cli.integrated_commands import (
        workpad as integrated_workpad,
        ai as integrated_ai,
        history as integrated_history,
        edit as integrated_edit
    )
    
    # Register with different names to avoid conflicts
    cli.add_command(integrated_workpad, name="workpad-integrated")
    cli.add_command(integrated_ai, name="ai")
    cli.add_command(integrated_history, name="history")
    cli.add_command(integrated_edit, name="edit")
    
    logger.info("Integrated Heaven Interface commands loaded")
except ImportError as e:
    logger.warning(f"Could not load integrated commands: {e}")


@cli.command()
def tui():
    """
    Launch the Heaven Interface TUI (Text User Interface).
    
    The TUI provides an interactive, full-screen interface with:
    - Real-time commit graph visualization
    - Live workpad status
    - Test run monitoring
    - Keyboard-driven navigation
    
    \b
    Keyboard Shortcuts:
      q - Quit
      r - Refresh
      c - Clear log
      g - Show commit graph
      w - Show workpads
      ? - Help
    """
    formatter.print_header("Heaven Interface TUI")
    formatter.print_info("Launching classic Heaven Interface experience...")
    try:
        from sologit.ui.tui_app import run_tui
        run_tui()
    except ImportError as e:
        abort_with_error(
            "TUI dependencies not installed",
            "Install with: pip install textual"
        )
    except Exception as e:
        abort_with_error("TUI launch failed", str(e))


@cli.command()
@click.option('--repo', 'repo_path', type=click.Path(exists=True), help='Repository path')
def heaven(repo_path: Optional[str]):
    """
    Launch the Heaven Interface TUI (Production Version).
    
    The Heaven Interface is a comprehensive, production-ready TUI with:
    - Command palette with fuzzy search (Ctrl+P)
    - File tree with git status
    - Real-time commit graph visualization
    - Live workpad status updates
    - Real-time test output streaming with pytest integration
    - AI operation tracking with cost monitoring
    - Command history with undo/redo (Ctrl+Z/Ctrl+Y)
    - Full keyboard navigation
    
    \b
    Key Features (>90% Integration):
      ✓ Complete workpad lifecycle management
      ✓ AI integration (code gen, review, refactor, test gen)
      ✓ Real-time test execution with live output
      ✓ Visual diff viewer and file browser
      ✓ Command history with undo/redo
      ✓ Fuzzy command palette
      ✓ Keyboard shortcuts for all operations
      ✓ Multi-panel layout following Heaven Design System
    
    \b
    Essential Shortcuts:
      Ctrl+P - Command palette
      Ctrl+T - Run tests
      Ctrl+Z/Y - Undo/Redo
      ? - Help (full shortcuts)
      R - Refresh
      Ctrl+Q - Quit
    
    \b
    Layout (Heaven Interface Design System):
      • Left:   Commit graph + File tree
      • Center: Workpad status + AI activity
      • Right:  Test runner + Diff viewer
    """
    formatter.print_header("Heaven Interface")
    formatter.print_info("Launching production Heaven Interface...")
    try:
        from sologit.ui.heaven_tui import run_heaven_tui
        run_heaven_tui(repo_path=repo_path)
    except ImportError as e:
        abort_with_error(
            "Heaven TUI dependencies not installed",
            "Install with: pip install textual"
        )
    except Exception as e:
        logger.error(f"Heaven TUI error: {e}", exc_info=True)
        abort_with_error("Heaven TUI launch failed", str(e))


@cli.command()
def heaven_legacy():
    """
    Launch the Legacy Enhanced Heaven Interface TUI.
    
    This is the previous version with basic functionality.
    Use 'evogitctl heaven' for the new production version.
    """
    formatter.print_header("Heaven Interface (Legacy)")
    formatter.print_info("Launching legacy enhanced interface...")
    try:
        from sologit.ui.enhanced_tui import run_enhanced_tui
        run_enhanced_tui()
    except ImportError as e:
        abort_with_error(
            "Enhanced TUI dependencies not installed",
            "Install with: pip install textual"
        )
    except Exception as e:
        logger.error(f"Enhanced TUI error: {e}", exc_info=True)
        abort_with_error("Enhanced TUI launch failed", str(e))


@cli.command()
def interactive():
    """
    Launch interactive shell with autocomplete.
    
    Provides an enhanced command-line experience with:
    - Command history (persisted across sessions)
    - Fuzzy autocomplete (Tab to complete)
    - Auto-suggest from history
    - Syntax highlighting
    
    Press Ctrl+C to exit.
    """
    formatter.print_header("Interactive Shell")
    formatter.print_info("Launching interactive prompt with autocomplete...")
    try:
        from sologit.ui.autocomplete import interactive_prompt
        interactive_prompt()
    except ImportError as e:
        abort_with_error(
            "Interactive shell dependencies not installed",
            "Install with: pip install prompt-toolkit"
        )
    except Exception as e:
        abort_with_error("Interactive shell failed", str(e))


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
        abort_with_error(
            "Prompt is required",
            "Usage: evogitctl pair \"your task description\"\n"
            "Example: evogitctl pair \"add user login feature\""
        )

    from sologit.cli.commands import execute_pair_loop

    formatter.print_header("AI Pair Programming")
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
        abort_with_error("Pair session failed", str(e))


def main():
    """Entry point for the CLI."""
    try:
        cli(obj={})
    except KeyboardInterrupt:
        formatter.print_warning("Interrupted by user.")
        sys.exit(130)
    except Exception as e:
        logger.exception("Unhandled exception")
        formatter.print_error_panel(str(e), title="Unhandled Error")
        sys.exit(1)


if __name__ == "__main__":
    main()

