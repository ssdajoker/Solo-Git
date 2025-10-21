
"""
Command history and fuzzy autocomplete for Heaven Interface CLI.

Provides intelligent autocomplete for Solo Git commands using prompt_toolkit.
"""

from typing import List, Optional, Dict, Any
from pathlib import Path
import json
from datetime import datetime

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion, FuzzyCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.styles import Style

from sologit.ui.theme import theme
from sologit.ui.history import get_cli_history_path


class SoloGitCompleter(Completer):
    """Completer for Solo Git commands."""
    
    def __init__(self):
        self.commands = [
            # Config commands
            'config setup',
            'config show',
            'config test',
            
            # Repo commands
            'repo init --zip',
            'repo init --git',
            'repo list',
            'repo info',
            
            # Pad commands
            'pad create',
            'pad list',
            'pad info',
            'pad promote',
            'pad delete',
            
            # Test commands
            'test run',
            'test run --target fast',
            'test run --target full',
            'test config',
            
            # Pair command
            'pair',
            
            # CI commands
            'ci smoke',
            'ci status',
            
            # Workflow commands
            'auto-merge run',
            'auto-merge status',
            'promote',
            'rollback --last',
            
            # Utility commands
            'version',
            'hello',
        ]
    
    def get_completions(self, document, complete_event):
        """Get completions for the current input."""
        word = document.get_word_before_cursor()
        text = document.text_before_cursor
        
        for command in self.commands:
            if command.startswith(text.lower()) or word.lower() in command.lower():
                yield Completion(
                    command,
                    start_position=-len(text),
                    display=command,
                    display_meta="Solo Git command"
                )


class CommandHistory:
    """Manages command history with persistence."""
    
    def __init__(self, history_file: Optional[Path] = None):
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
            except:
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
        except:
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


def create_enhanced_prompt(history_path: Optional[Path] = None) -> PromptSession:
    """Create an enhanced prompt with autocomplete and history."""
    if history_path is None:
        history_path = get_cli_history_path()

    history_file = Path(history_path)
    history_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Create style based on Heaven Interface theme
    prompt_style = Style.from_dict({
        'prompt': f'{theme.colors.blue}',
        'completion-menu': f'bg:{theme.colors.surface} {theme.colors.text_primary}',
        'completion-menu.completion': f'bg:{theme.colors.surface}',
        'completion-menu.completion.current': f'bg:{theme.colors.blue} {theme.colors.background}',
        'completion-menu.meta': f'{theme.colors.text_secondary}',
    })
    
    completer = FuzzyCompleter(SoloGitCompleter())
    
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


if __name__ == "__main__":
    interactive_prompt()
