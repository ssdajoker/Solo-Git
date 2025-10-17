"""
Command Palette with Fuzzy Finding for Heaven Interface.

Provides a VS Code-style command palette with fuzzy search,
keyboard navigation, and command execution.
"""

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import Input, Static, Label
from textual.binding import Binding
from textual.screen import ModalScreen
from typing import List, Callable, Optional, Tuple
import re
from dataclasses import dataclass

from sologit.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Command:
    """Represents a command that can be executed from the palette."""
    id: str
    label: str
    description: str
    category: str
    callback: Callable
    shortcut: Optional[str] = None
    keywords: List[str] = None
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []


class FuzzyMatcher:
    """Fuzzy matching algorithm for command search."""
    
    @staticmethod
    def match(query: str, text: str) -> Tuple[bool, int]:
        """
        Fuzzy match query against text.
        
        Returns:
            Tuple of (matched: bool, score: int)
            Higher score = better match
        """
        if not query:
            return True, 0
        
        query = query.lower()
        text = text.lower()
        
        # Exact match gets highest score
        if query in text:
            score = 1000 - text.index(query)
            return True, score
        
        # Fuzzy match: all query chars must appear in order
        query_idx = 0
        text_idx = 0
        score = 0
        last_match_idx = -1
        
        while query_idx < len(query) and text_idx < len(text):
            if query[query_idx] == text[text_idx]:
                # Bonus for consecutive matches
                if text_idx == last_match_idx + 1:
                    score += 10
                else:
                    score += 1
                last_match_idx = text_idx
                query_idx += 1
            text_idx += 1
        
        # All query characters must be found
        matched = query_idx == len(query)
        
        # Bonus for shorter text (more specific match)
        if matched:
            score += max(0, 100 - len(text))
        
        return matched, score if matched else 0


class CommandItem(Static):
    """A single command item in the palette."""
    
    def __init__(self, command: Command, **kwargs):
        super().__init__(**kwargs)
        self.command = command
    
    def render(self) -> str:
        """Render the command item."""
        shortcut = f"  [{self.command.shortcut}]" if self.command.shortcut else ""
        return f"▸ {self.command.label}{shortcut}\n  {self.command.description}"


class CommandPaletteScreen(ModalScreen):
    """Modal screen for the command palette."""
    
    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=False),
        Binding("ctrl+c", "dismiss", "Cancel", show=False),
        Binding("up", "select_previous", "Previous", show=False),
        Binding("down", "select_next", "Next", show=False),
        Binding("ctrl+p", "select_previous", "Previous", show=False),
        Binding("ctrl+n", "select_next", "Next", show=False),
        Binding("enter", "execute", "Execute", show=False),
    ]
    
    CSS = """
    CommandPaletteScreen {
        align: center middle;
    }
    
    #palette-container {
        width: 80;
        height: auto;
        max-height: 30;
        border: thick $primary;
        background: $surface;
        padding: 1;
    }
    
    #palette-input {
        dock: top;
        width: 100%;
        margin-bottom: 1;
        border: tall $accent;
    }
    
    #palette-results {
        width: 100%;
        height: auto;
        max-height: 20;
        overflow-y: auto;
    }
    
    CommandItem {
        padding: 1;
        margin-bottom: 1;
        border: none;
        background: $panel;
    }
    
    CommandItem.selected {
        background: $accent;
        border: tall $primary;
    }
    
    #category-label {
        color: $text-muted;
        text-style: bold;
        margin-top: 1;
    }
    
    #no-results {
        color: $text-muted;
        text-align: center;
        padding: 2;
    }
    """
    
    def __init__(self, commands: List[Command], **kwargs):
        super().__init__(**kwargs)
        self.commands = commands
        self.filtered_commands: List[Command] = []
        self.selected_index = 0
    
    def compose(self) -> ComposeResult:
        """Compose the command palette UI."""
        with Container(id="palette-container"):
            yield Input(
                placeholder="Type to search commands...",
                id="palette-input"
            )
            yield VerticalScroll(id="palette-results")
    
    def on_mount(self) -> None:
        """Handle mount event."""
        # Focus the input
        self.query_one("#palette-input", Input).focus()
        # Show all commands initially
        self.filter_commands("")
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes."""
        self.filter_commands(event.value)
    
    def filter_commands(self, query: str) -> None:
        """Filter commands based on query."""
        if not query:
            # Show all commands
            self.filtered_commands = self.commands.copy()
        else:
            # Fuzzy match and sort by score
            matches = []
            for cmd in self.commands:
                # Match against label, description, and keywords
                texts = [cmd.label, cmd.description, cmd.category] + cmd.keywords
                best_score = 0
                matched = False
                
                for text in texts:
                    match, score = FuzzyMatcher.match(query, text)
                    if match:
                        matched = True
                        best_score = max(best_score, score)
                
                if matched:
                    matches.append((cmd, best_score))
            
            # Sort by score (descending)
            matches.sort(key=lambda x: x[1], reverse=True)
            self.filtered_commands = [cmd for cmd, _ in matches]
        
        # Reset selection
        self.selected_index = 0
        
        # Update UI
        self.refresh_results()
    
    def refresh_results(self) -> None:
        """Refresh the results display."""
        results_container = self.query_one("#palette-results", VerticalScroll)
        results_container.remove_children()
        
        if not self.filtered_commands:
            results_container.mount(
                Label("No commands found", id="no-results")
            )
            return
        
        # Group commands by category
        by_category = {}
        for cmd in self.filtered_commands:
            if cmd.category not in by_category:
                by_category[cmd.category] = []
            by_category[cmd.category].append(cmd)
        
        # Render commands by category
        for idx, cmd in enumerate(self.filtered_commands):
            item = CommandItem(cmd)
            if idx == self.selected_index:
                item.add_class("selected")
            results_container.mount(item)
    
    def action_select_previous(self) -> None:
        """Select previous command."""
        if self.filtered_commands:
            self.selected_index = (self.selected_index - 1) % len(self.filtered_commands)
            self.refresh_results()
    
    def action_select_next(self) -> None:
        """Select next command."""
        if self.filtered_commands:
            self.selected_index = (self.selected_index + 1) % len(self.filtered_commands)
            self.refresh_results()
    
    def action_execute(self) -> None:
        """Execute the selected command."""
        if not self.filtered_commands:
            return
        
        selected_command = self.filtered_commands[self.selected_index]
        
        # Dismiss the palette
        self.dismiss()
        
        # Execute the command
        try:
            logger.info(f"Executing command: {selected_command.id}")
            selected_command.callback()
        except Exception as e:
            logger.error(f"Command execution failed: {e}", exc_info=True)
            self.app.notify(
                f"Command failed: {str(e)}",
                severity="error",
                timeout=5
            )
    
    def action_dismiss(self) -> None:
        """Dismiss the palette."""
        self.dismiss()


class CommandRegistry:
    """Registry for managing available commands."""
    
    def __init__(self):
        self.commands: List[Command] = []
        self._setup_default_commands()
    
    def register(self, command: Command) -> None:
        """Register a command."""
        self.commands.append(command)
        logger.debug(f"Registered command: {command.id}")
    
    def unregister(self, command_id: str) -> None:
        """Unregister a command."""
        self.commands = [c for c in self.commands if c.id != command_id]
        logger.debug(f"Unregistered command: {command_id}")
    
    def get_command(self, command_id: str) -> Optional[Command]:
        """Get a command by ID."""
        for cmd in self.commands:
            if cmd.id == command_id:
                return cmd
        return None
    
    def get_all_commands(self) -> List[Command]:
        """Get all registered commands."""
        return self.commands.copy()
    
    def _setup_default_commands(self) -> None:
        """Setup default commands."""
        # These will be populated by the application
        pass


# Global command registry
_command_registry = CommandRegistry()


def get_command_registry() -> CommandRegistry:
    """Get the global command registry."""
    return _command_registry


def show_command_palette(app, commands: Optional[List[Command]] = None) -> None:
    """
    Show the command palette.
    
    Args:
        app: The Textual app instance
        commands: List of commands (uses registry if None)
    """
    if commands is None:
        commands = get_command_registry().get_all_commands()
    
    palette = CommandPaletteScreen(commands)
    app.push_screen(palette)
