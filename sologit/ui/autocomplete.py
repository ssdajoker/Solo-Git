"""Autocomplete helpers for the Solo Git CLI."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import click
from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import Completer, Completion, FuzzyCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style

from sologit.ui.history import get_cli_history_path
from sologit.ui.theme import theme


class SoloGitCompleter(Completer):
    """Completer for Solo Git commands built from the Click command tree."""

    _DEFAULT_COMMANDS: Sequence[str] = (
        # Helpful fallbacks if dynamic discovery fails
        "config setup",
        "config show",
        "config test",
        "repo init --zip",
        "repo init --git",
        "repo list",
        "repo info",
        "pad create",
        "pad list",
        "pad info",
        "pad promote",
        "pad delete",
        "test run",
        "test config",
        "pair",
        "ci smoke",
        "ci status",
        "auto-merge run",
        "auto-merge status",
        "promote",
        "rollback --last",
        "version",
        "hello",
        "history",
        "undo",
        "redo",
    )

    def __init__(self, cli_app: Optional[click.MultiCommand] = None) -> None:
        self._cli_app = cli_app
        self.commands = self._build_command_list()

    def _build_command_list(self) -> List[str]:
        """Collect command and option combinations from the Click CLI."""

        if self._cli_app is None:
            return list(self._DEFAULT_COMMANDS)

        discovered: List[str] = []

        def option_tokens(command: click.Command) -> Iterable[str]:
            for param in getattr(command, "params", []):
                if isinstance(param, click.Option):
                    for opt in (*param.opts, *getattr(param, 'secondary_opts', ())):
                        yield opt

        def visit(command: click.Command, path: Tuple[str, ...]) -> None:
            base = " ".join(path).strip()
            if base:
                discovered.append(base)

            for opt in option_tokens(command):
                token = f"{base} {opt}" if base else opt
                discovered.append(token.strip())

            if isinstance(command, click.MultiCommand):
                subcommands = getattr(command, "commands", {}) or {}
                for name, sub in subcommands.items():
                    if sub is None:
                        continue
                    visit(sub, (*path, name))

        visit(self._cli_app, tuple())

        # Include helpful defaults and remove duplicates while preserving order
        seen = set()
        ordered: List[str] = []
        for candidate in list(discovered) + list(self._DEFAULT_COMMANDS):
            key = candidate.strip()
            if not key or key in seen:
                continue
            seen.add(key)
            ordered.append(key)

        return ordered

    def get_completions(  # type: ignore[override]
        self, document: Any, complete_event: Any
    ) -> Iterable[Completion]:
        """Yield completions that fuzzy-match the current buffer."""

        word = document.get_word_before_cursor() or ""
        text = document.text_before_cursor or ""
        lowered_text = text.lower()
        lowered_word = word.lower()

        for command in self.commands:
            command_lower = command.lower()
            if command_lower.startswith(lowered_text) or lowered_word in command_lower:
                yield Completion(
                    command,
                    start_position=-len(text),
                    display=command,
                    display_meta="Solo Git command",
                )


class CommandHistory:
    """Manages command history with persistence."""

    def __init__(self, history_file: Optional[Path] = None) -> None:
        if history_file is None:
            history_file = Path.home() / ".sologit" / "command_history"

        self.history_file = Path(history_file)
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

        # Stats file
        self.stats_file = self.history_file.parent / "command_stats.json"
        self.stats = self._load_stats()

    def _load_stats(self) -> Dict[str, Any]:
        """Load command statistics."""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "total_commands": 0,
            "command_counts": {},
            "last_updated": datetime.utcnow().isoformat()
        }

    def _save_stats(self) -> None:
        """Save command statistics."""
        self.stats["last_updated"] = datetime.utcnow().isoformat()
        try:
            with open(self.stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
        except Exception:
            pass

    def record_command(self, command: str) -> None:
        """Record a command execution."""
        self.stats["total_commands"] += 1

        # Extract base command
        base_cmd = command.split()[0] if command else "unknown"
        self.stats["command_counts"][base_cmd] = self.stats["command_counts"].get(base_cmd, 0) + 1

        self._save_stats()

    def get_popular_commands(self, limit: int = 10) -> List[tuple]:
        """Get most popular commands."""
        counts = self.stats["command_counts"]
        sorted_commands = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_commands[:limit]


def create_enhanced_prompt(
    history_path: Optional[Path] = None,
    cli_app: Optional[click.MultiCommand] = None,
) -> PromptSession:
    """Create an enhanced prompt with autocomplete and history."""
    if history_path is None:
        history_path = get_cli_history_path()

    history_file = Path(history_path)
    history_file.parent.mkdir(parents=True, exist_ok=True)
    history_file.touch(exist_ok=True)

    # Create style based on Heaven Interface theme
    prompt_style = Style.from_dict({
        'prompt': f'{theme.colors.blue}',
        'completion-menu': f'bg:{theme.colors.surface} {theme.colors.text_primary}',
        'completion-menu.completion': f'bg:{theme.colors.surface}',
        'completion-menu.completion.current': f'bg:{theme.colors.blue} {theme.colors.background}',
        'completion-menu.meta': f'{theme.colors.text_secondary}',
    })

    completer = FuzzyCompleter(SoloGitCompleter(cli_app=cli_app))

    session = PromptSession(
        history=FileHistory(str(history_file)),
        completer=completer,
        auto_suggest=AutoSuggestFromHistory(),
        style=prompt_style,
        complete_while_typing=True,
        enable_history_search=True,
    )

    return session


def interactive_prompt() -> None:
    """Run an interactive prompt with autocomplete."""
    print("╔══════════════════════════════════════════════════╗")
    print("║   Solo Git Interactive Shell                     ║")
    print("║   Press Tab for autocomplete, Ctrl+C to exit     ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    session = create_enhanced_prompt()
    history = CommandHistory()

    while True:
        try:
            # Get input with autocomplete
            text = session.prompt('evogitctl> ')

            if text.strip():
                # Record command
                history.record_command(text)

                # Execute (placeholder - would need to integrate with CLI)
                print(f"Executing: {text}")
                print("(Command execution not yet wired up to CLI in interactive mode)")
                print()

        except KeyboardInterrupt:
            print("\nInterrupted")
            break
        except EOFError:
            print("\nGoodbye!")
            break
