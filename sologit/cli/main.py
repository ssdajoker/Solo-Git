
"""
Main CLI entry point for Solo Git.

Provides the evogitctl command-line interface with subcommands for
repository management, workpad operations, testing, and AI pairing.
"""

import os
import click
import subprocess
import shlex
import sys
from pathlib import Path
from typing import List, Optional

from rich.console import Console

from sologit import __version__
from sologit.utils.logger import get_logger, setup_logging
from sologit.cli import commands, config_commands

try:
    from sologit.cli import integrated_commands
except ImportError:  # pragma: no cover - optional feature set
    integrated_commands = None

# Re-export ConfigManager for backwards compatibility with existing patches
ConfigManager = config_commands.ConfigManager
_ORIGINAL_CONFIG_MANAGER = ConfigManager
from sologit.ui.formatter import RichFormatter
from sologit.ui.theme import theme
from sologit.ui.history import (
    get_command_history,
    CommandType,
    get_cli_history_path,
    append_cli_history,
)

try:
    from sologit.ui.autocomplete import create_enhanced_prompt
    _AUTOCOMPLETE_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    create_enhanced_prompt = None
    _AUTOCOMPLETE_AVAILABLE = False

logger = get_logger(__name__)

console = Console()
formatter = RichFormatter(console)


def _find_heaven_gui_dir() -> Optional[Path]:
    """Locate the heaven-gui project directory for development mode."""
    base_file = Path(__file__).resolve()
    candidates = []
    seen = set()

    # Prefer running from the current working directory if available
    cwd_candidate = (Path.cwd() / "heaven-gui").resolve()
    if cwd_candidate.exists() and cwd_candidate.is_dir():
        candidates.append(cwd_candidate)
        seen.add(cwd_candidate)

    for parent in base_file.parents:
        candidate = (parent / "heaven-gui").resolve()
        if candidate in seen:
            continue
        if candidate.exists() and candidate.is_dir():
            candidates.append(candidate)
            seen.add(candidate)

    return candidates[0] if candidates else None


def _resolve_gui_executable() -> Optional[Path]:
    """Resolve the built GUI executable path."""
    gui_dir = Path.home() / ".sologit" / "gui"

    candidates = []
    if sys.platform == "win32":
        candidates.append(gui_dir / "solo-git-gui.exe")
    elif sys.platform == "darwin":
        candidates.append(gui_dir / "solo-git-gui.app" / "Contents" / "MacOS" / "solo-git-gui")

    candidates.append(gui_dir / "solo-git-gui")

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None


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
    ctx.obj['history'] = get_command_history()
    formatter.set_console(console)
    commands.set_formatter_console(console)
    config_commands.set_formatter_console(console)
    if integrated_commands is not None:
        integrated_commands.set_formatter_console(console)

    # Load configuration
    try:
        manager_cls = ConfigManager
        if manager_cls is _ORIGINAL_CONFIG_MANAGER:
            manager_cls = getattr(config_commands, "ConfigManager", _ORIGINAL_CONFIG_MANAGER)

        config_manager = manager_cls(config_path=config)
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


@cli.command()
def shortcuts():
    """Display keyboard shortcuts for the Heaven Interface TUI."""
    formatter.print_header("Heaven Interface TUI - Keyboard Shortcuts")

    shortcuts_data = [
        ("Navigation", "Ctrl+P", "Open command palette"),
        ("Navigation", "Tab / Shift+Tab", "Switch between panels"),
        ("Navigation", "← → ↑ ↓", "Navigate within panels"),
        ("Workpads", "Ctrl+N", "Create new workpad"),
        ("Workpads", "Ctrl+W", "Close workpad"),
        ("Workpads", "Ctrl+D", "Show diff"),
        ("Workpads", "Ctrl+S", "Commit changes"),
        ("Testing", "Ctrl+T", "Run focused tests"),
        ("Testing", "Ctrl+Shift+T", "Run all tests"),
        ("Testing", "Ctrl+L", "Clear test output"),
        ("AI", "Ctrl+G", "Generate code"),
        ("AI", "Ctrl+R", "Review code"),
        ("AI", "Ctrl+M", "Generate commit message"),
        ("History", "Ctrl+Z", "Undo last command"),
        ("History", "Ctrl+Shift+Z", "Redo command"),
        ("History", "Ctrl+H", "Show command history"),
        ("View", "Ctrl+B", "Toggle file browser"),
        ("View", "Ctrl+1", "Focus commit graph"),
        ("View", "Ctrl+2", "Focus workpad panel"),
        ("View", "Ctrl+3", "Focus test output"),
        ("View", "Ctrl+F", "Search files"),
        ("General", "?", "Show help"),
        ("General", "Ctrl+Q", "Quit application"),
        ("General", "Ctrl+C", "Cancel current operation"),
    ]

    table = formatter.table(headers=["Category", "Shortcut", "Action"])
    for category, shortcut, action in shortcuts_data:
        table.add_row(category, shortcut, action)

    formatter.console.print(table)
    formatter.print_info(
        "Press '?' inside the TUI to view keyboard shortcuts at any time."
        "Press '?' inside the TUI to view this list at any time."
    )


@cli.command()
@click.option('--dev', is_flag=True, help='Launch in development mode')
@click.pass_context
def gui(ctx, dev: bool):
    """Launch the Heaven Interface GUI."""
    config_manager = ctx.obj.get('config') if ctx and ctx.obj else None
    env = os.environ.copy()
    if config_manager is not None and (
        config_path := getattr(config_manager, "config_path", None)
    ):
        env.setdefault("SOLOGIT_CONFIG_PATH", str(config_path))

    if dev:
        gui_dir = _find_heaven_gui_dir()
        if not gui_dir:
            abort_with_error(
                "Unable to locate heaven-gui project for development mode.",
                "Ensure the heaven-gui directory exists alongside the CLI sources."
            )

        formatter.print_info(
            "Launching Heaven Interface GUI in development mode (tauri:dev)..."
        )
        try:
            subprocess.run(['npm', 'run', 'tauri:dev'], cwd=str(gui_dir), check=True, env=env)
        except FileNotFoundError:
            abort_with_error(
                "Failed to launch development GUI.",
                "npm was not found on PATH. Install Node.js/npm and try again."
            )
        except subprocess.CalledProcessError as exc:
            abort_with_error(
                "Development GUI exited with a non-zero status.",
                f"Command: npm run tauri:dev\nExit code: {exc.returncode}"
            )
        return

    gui_path = _resolve_gui_executable()
    if not gui_path:
        abort_with_error(
            "GUI not built.",
            "Run: cd heaven-gui && npm run tauri:build"
        )

    formatter.print_info(f"Launching Heaven Interface GUI from {gui_path}...")
    try:
        launch_cwd = gui_path.parent
        subprocess.Popen(
            [str(gui_path)],
            env=env,
            cwd=str(launch_cwd),
            start_new_session=True,
        )
    except FileNotFoundError:
        abort_with_error(
            "GUI executable not found.",
            f"Expected to find executable at {gui_path}"
        )
    except Exception as exc:  # pragma: no cover - unexpected launch errors
        logger.error(f"Failed to launch GUI: {exc}")
        abort_with_error("GUI launch failed", str(exc))


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

def _launch_heaven_tui(repo_path: Optional[str] = None) -> None:
    """Shared launcher for the Heaven TUI."""
    try:
        from sologit.ui.heaven_tui import run_heaven_tui
        run_heaven_tui(repo_path=repo_path)
    except ImportError as e:
        formatter.print_error("Heaven TUI dependencies not installed")
        formatter.print_info("Install with: pip install textual")
        raise click.Abort()
    except Exception as e:
        formatter.print_error(f"Heaven TUI launch failed: {e}")
        logger.error(f"Heaven TUI error: {e}", exc_info=True)
        raise click.Abort()


@cli.command()
def tui():
    """
    Launch the Heaven Interface TUI (Text User Interface).

    This command is an alias for ``evogitctl heaven`` and launches the
    production HeavenTUI experience with the full-screen interface for
    repository management, test monitoring, and workpad control.

    \b
    Keyboard Shortcuts:
      q - Quit
      r - Refresh
      c - Clear log
      g - Show commit graph
      w - Show workpads
      ? - Help
    """
    _launch_heaven_tui()
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

    This command can also be accessed via the ``evogitctl tui`` alias.
    """
    _launch_heaven_tui(repo_path=repo_path)
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
    exit_code = _run_interactive_shell()
    if exit_code != 0:
        raise click.Abort()


@cli.command()
def undo():
    """Undo the last undoable command."""
    history = get_command_history()
    entry = history.undo()
    if not entry:
        formatter.print_warning("No undoable commands available.")
        return

    formatter.print_success(f"Undid: {entry.description}")


@cli.command()
def redo():
    """Redo the next command if available."""
    history = get_command_history()
    entry = history.redo()
    if not entry:
        formatter.print_warning("No commands available to redo.")
        return

    formatter.print_success(f"Redid: {entry.description}")


@cli.command(name="history")
@click.option("--limit", default=10, show_default=True, type=click.IntRange(1, 1000))
@click.option("--all", "show_all", is_flag=True, help="Include non-CLI commands.")
def show_history(limit: int, show_all: bool):
    """Display recent command history."""
    history = get_command_history()

    entries = history.get_history()
    if not show_all:
        entries = [entry for entry in entries if entry.type == CommandType.CLI_COMMAND]

    if not entries:
        formatter.print_info("No commands recorded yet.")
        return

    rows = entries[:limit]

    table = formatter.table(headers=["Time", "Type", "Command", "Result"])
    for entry in rows:
        timestamp = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        result = entry.result or {}
        exit_code = result.get("exit_code")
        status = "success" if exit_code in (0, None) else f"exit {exit_code}"
        if result.get("error"):
            status = f"error: {result['error']}"

        table.add_row(
            timestamp,
            entry.type.value,
            entry.description,
            status,
        )

    formatter.console.print(table)


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


# Phase 4: Integrated Heaven Interface commands
try:
    from sologit.cli.integrated_commands import (
        workpad as integrated_workpad,
        ai as integrated_ai,
        history as integrated_history,
        edit as integrated_edit
    )

    # Register with distinct names to avoid clashing with core commands
    cli.add_command(integrated_workpad, name="workpad-integrated")
    cli.add_command(integrated_ai, name="ai")
    cli.add_command(integrated_history, name="heaven-history")
    cli.add_command(integrated_edit, name="edit")

    logger.info("Integrated Heaven Interface commands loaded")
except ImportError as e:
    logger.warning(f"Could not load integrated commands: {e}")


def main():
    """Entry point for the CLI."""
    try:
        if len(sys.argv) == 1 and sys.stdin.isatty():
            exit_code = _run_interactive_shell()
        else:
            exit_code = _execute_cli_command(sys.argv[1:])
    except KeyboardInterrupt:
        formatter.print_warning("Interrupted by user.")
        exit_code = 130
    except Exception as e:
        logger.exception("Unhandled exception")
        formatter.print_error_panel(str(e), title="Unhandled Error")
        exit_code = 1

    sys.exit(exit_code)

def _run_interactive_shell() -> int:
    """Launch interactive shell with history and autocomplete."""
    if not _AUTOCOMPLETE_AVAILABLE:
        abort_with_error(
            "Interactive shell dependencies not installed",
            "Install with: pip install prompt-toolkit"
        )

    from prompt_toolkit.key_binding import KeyBindings, merge_key_bindings
    from prompt_toolkit.completion import FuzzyWordCompleter
    from prompt_toolkit.shortcuts import prompt as toolkit_prompt
    from prompt_toolkit.document import Document

    formatter.print_header("Interactive Shell")
    formatter.print_info("Press Ctrl+R for history search, Tab for autocomplete.")

    cli_history_path = get_cli_history_path()
    session = create_enhanced_prompt(history_path=cli_history_path, cli_app=cli)

    def _load_history_strings() -> List[str]:
        if not cli_history_path.exists():
            return []
        try:
            with cli_history_path.open('r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip()]
        except Exception:
            return []

    bindings = KeyBindings()

    @bindings.add('c-r')
    def _(event) -> None:
        items = _load_history_strings()
        if not items:
            formatter.print_warning("No history entries yet.")
            return

        completer = FuzzyWordCompleter(items, ignore_case=True)
        try:
            selection = toolkit_prompt(
                "History search: ",
                completer=completer,
                complete_in_thread=True,
            )
        except (KeyboardInterrupt, EOFError):
            return
        if selection:
            event.current_buffer.document = Document(
                selection,
                cursor_position=len(selection)
            )

    session.app.key_bindings = merge_key_bindings([session.app.key_bindings, bindings])

    history = get_command_history()

    while True:
        try:
            text = session.prompt('evogitctl> ', enable_history_search=True)
        except KeyboardInterrupt:
            formatter.print_warning("Interrupted")
            return 130
        except EOFError:
            formatter.print_info("Goodbye!")
            return 0

        command = text.strip()
        if not command:
            continue
        if command.lower() in {"exit", "quit"}:
            formatter.print_info("Exiting interactive shell.")
            return 0

        try:
            args = shlex.split(command)
        except ValueError as exc:
            formatter.print_error_panel(str(exc), title="Invalid command")
            continue

        entry_id = history.record_cli_command(
            command,
            arguments={"argv": args},
            record_text=False,
        )

        exit_code = _execute_cli_command(
            args,
            record_cli_history=False,
            command_entry_id=entry_id,
            command_text=command
        )
        if exit_code != 0:
            formatter.print_warning(f"Command exited with code {exit_code}")


def _execute_cli_command(
    argv: List[str],
    *,
    record_cli_history: bool = True,
    command_entry_id: Optional[str] = None,
    command_text: Optional[str] = None
) -> int:
    """Execute CLI command with history integration."""
    history = get_command_history()

    command_str = command_text or " ".join(shlex.quote(arg) for arg in argv)
    entry_id = command_entry_id

    if command_str and entry_id is None:
        entry_id = history.record_cli_command(
            command_str,
            arguments={"argv": argv},
            record_text=record_cli_history,
        )
    elif command_str and record_cli_history and entry_id is not None:
        append_cli_history(command_str)

    exit_code = 0

    try:
        cli.main(args=argv, prog_name="evogitctl", standalone_mode=False, obj={})
    except SystemExit as exc:
        exit_code = exc.code or 0
    except Exception as exc:
        exit_code = 1
        if entry_id:
            history.update_command_result(
                entry_id,
                {
                    "exit_code": exit_code,
                    "error": str(exc),
                },
            )
        raise
    else:
        exit_code = 0

    if entry_id:
        history.update_command_result(entry_id, {"exit_code": exit_code})

    return exit_code


if __name__ == "__main__":
    main()
