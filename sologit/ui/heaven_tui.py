"""
Heaven Interface - Comprehensive TUI for Solo Git.

Integrates all UI components into a production-ready interface following
the Heaven Interface Design System specifications.
"""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Header, Footer, Static, Label
from textual.screen import Screen
from textual import events
from pathlib import Path
from typing import Optional

from sologit.ui.command_palette import show_command_palette, Command, get_command_registry
from sologit.ui.file_tree import FileTreeWidget, DiffViewer, FileSelected
from sologit.ui.test_runner import TestRunnerWidget, TestsCompleted
from sologit.ui.history import get_command_history, undo, redo, can_undo, can_redo
from sologit.state.git_sync import GitStateSync
from sologit.utils.logger import get_logger

logger = get_logger(__name__)


class StatusBar(Static):
    """Status bar showing current context and state."""
    
    CSS = """
    StatusBar {
        dock: bottom;
        height: 1;
        background: $panel;
        color: $text;
        padding: 0 1;
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.repo_name = "No repository"
        self.workpad_name = "No workpad"
        self.test_status = "○"
    
    def render(self) -> str:
        """Render status bar."""
        undo_text = "↶" if can_undo() else "⊘"
        redo_text = "↷" if can_redo() else "⊘"
        
        return (
            f"📦 {self.repo_name}  "
            f"│  🔧 {self.workpad_name}  "
            f"│  {self.test_status} Tests  "
            f"│  {undo_text} Undo  {redo_text} Redo  "
            f"│  Ctrl+P: Commands  ?:  Help"
        )
    
    def update_context(self, repo_name: str, workpad_name: str = None, test_status: str = "○"):
        """Update status bar context."""
        self.repo_name = repo_name
        self.workpad_name = workpad_name or "No workpad"
        self.test_status = test_status
        self.refresh()


class CommitGraphPanel(Static):
    """Panel showing commit graph and history."""
    
    CSS = """
    CommitGraphPanel {
        width: 1fr;
        height: 100%;
        border: solid $primary;
        padding: 1;
    }
    
    .commit-entry {
        padding: 0 1;
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.commits = []
    
    def render(self) -> str:
        """Render commit graph."""
        if not self.commits:
            return "[dim]No commits yet[/]"
        
        lines = ["[bold cyan]Commit History[/]\n"]
        
        for i, commit in enumerate(self.commits[:15]):  # Show last 15
            sha_short = commit.get('sha', '')[:8]
            message = commit.get('message', '').split('\n')[0][:40]
            author = commit.get('author', '').split('<')[0].strip()[:20]
            
            # Graph line
            if i < len(self.commits) - 1:
                lines.append(f"  │")
            
            # Commit node
            lines.append(f"  ● [yellow]{sha_short}[/] {message}")
            lines.append(f"  │ [dim]{author}[/]")
        
        return '\n'.join(lines)
    
    def update_commits(self, commits: list):
        """Update commit list."""
        self.commits = commits
        self.refresh()


class WorkpadPanel(Static):
    """Panel showing workpad status and information."""
    
    CSS = """
    WorkpadPanel {
        width: 1fr;
        height: 100%;
        border: solid $primary;
        padding: 1;
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.workpads = []
        self.active_workpad = None
    
    def render(self) -> str:
        """Render workpad panel."""
        lines = ["[bold green]Active Workpads[/]\n"]
        
        if not self.workpads:
            lines.append("[dim]No active workpads[/]")
            return '\n'.join(lines)
        
        for wp in self.workpads[:10]:  # Show max 10
            wp_id = wp.get('id', '')[:12]
            title = wp.get('title', 'Untitled')[:30]
            status = wp.get('status', 'unknown')
            
            # Status indicator
            if status == 'active':
                indicator = "🟢"
            elif status == 'promoted':
                indicator = "✅"
            elif status == 'deleted':
                indicator = "❌"
            else:
                indicator = "⚪"
            
            # Active marker
            active = "→" if self.active_workpad and self.active_workpad == wp_id else " "
            
            lines.append(f"{active} {indicator} {title}")
            lines.append(f"   [dim]{wp_id}[/]")
        
        return '\n'.join(lines)
    
    def update_workpads(self, workpads: list, active_id: Optional[str] = None):
        """Update workpad list."""
        self.workpads = workpads
        self.active_workpad = active_id
        self.refresh()


class AIActivityPanel(Static):
    """Panel showing AI operation activity."""
    
    CSS = """
    AIActivityPanel {
        width: 1fr;
        height: 100%;
        border: solid $primary;
        padding: 1;
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.operations = []
    
    def render(self) -> str:
        """Render AI activity."""
        lines = ["[bold magenta]AI Activity[/]\n"]
        
        if not self.operations:
            lines.append("[dim]No AI operations yet[/]")
            return '\n'.join(lines)
        
        for op in self.operations[:8]:  # Show last 8
            op_type = op.get('type', 'unknown')
            status = op.get('status', 'unknown')
            model = op.get('model', '')[:15]
            cost = op.get('cost_usd', 0.0)
            
            # Status icon
            if status == 'completed':
                icon = "✓"
                color = "green"
            elif status == 'failed':
                icon = "✗"
                color = "red"
            elif status == 'running':
                icon = "⟳"
                color = "cyan"
            else:
                icon = "○"
                color = "dim"
            
            lines.append(f"[{color}]{icon}[/] {op_type}")
            lines.append(f"   [dim]{model} • ${cost:.4f}[/]")
        
        return '\n'.join(lines)
    
    def update_operations(self, operations: list):
        """Update operations list."""
        self.operations = operations
        self.refresh()


class HelpScreen(Screen):
    """Help screen showing keyboard shortcuts."""
    
    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=True),
        Binding("q", "dismiss", "Close", show=True),
    ]
    
    CSS = """
    HelpScreen {
        align: center middle;
    }
    
    #help-container {
        width: 80;
        height: auto;
        max-height: 40;
        border: thick $primary;
        background: $surface;
        padding: 2;
    }
    """
    
    def compose(self) -> ComposeResult:
        """Compose help screen."""
        help_text = """
[bold cyan]Heaven Interface - Keyboard Shortcuts[/]

[bold yellow]Navigation[/]
  Ctrl+P          Open command palette
  Tab / Shift+Tab Switch between panels
  ← → ↑ ↓         Navigate within panels
  
[bold yellow]Workpad Operations[/]
  Ctrl+N          Create new workpad
  Ctrl+W          Close workpad
  Ctrl+D          Show diff
  Ctrl+S          Commit changes
  
[bold yellow]Testing[/]
  Ctrl+T          Run tests (fast)
  Ctrl+Shift+T    Run all tests
  Ctrl+L          Clear test output
  
[bold yellow]AI Features[/]
  Ctrl+G          Generate code
  Ctrl+R          Review code
  Ctrl+M          Generate commit message
  
[bold yellow]History[/]
  Ctrl+Z          Undo last command
  Ctrl+Shift+Z    Redo command
  Ctrl+H          Show command history
  
[bold yellow]View[/]
  Ctrl+B          Toggle file browser
  Ctrl+1          Focus commit graph
  Ctrl+2          Focus workpad panel
  Ctrl+3          Focus test output
  Ctrl+F          Search files
  
[bold yellow]General[/]
  ?               Show this help
  Ctrl+Q          Quit application
  Ctrl+C          Cancel operation

[bold green]Press Escape or Q to close this help[/]
        """
        
        with Container(id="help-container"):
            yield Static(help_text)
    
    def action_dismiss(self) -> None:
        """Dismiss the help screen."""
        self.app.pop_screen()


class HeavenTUI(App):
    """
    Heaven Interface - Production-ready TUI for Solo Git.
    
    Implements the Heaven Interface Design System with:
    - Command palette with fuzzy search
    - File tree with git status
    - Real-time test runner
    - Commit graph visualization
    - AI operation tracking
    - Command history with undo/redo
    """
    
    CSS = """
    HeavenTUI {
        background: $surface;
    }
    
    #main-container {
        height: 100%;
        width: 100%;
    }
    
    #left-panel {
        width: 30%;
        height: 100%;
    }
    
    #center-panel {
        width: 40%;
        height: 100%;
    }
    
    #right-panel {
        width: 30%;
        height: 100%;
    }
    
    .panel-split {
        height: 50%;
    }
    """
    
    BINDINGS = [
        Binding("ctrl+p", "command_palette", "Commands", show=True),
        Binding("ctrl+q", "quit", "Quit", show=True),
        Binding("?", "help", "Help", show=True),
        Binding("ctrl+z", "undo", "Undo", show=False),
        Binding("ctrl+y", "redo", "Redo", show=False),
        Binding("ctrl+t", "run_tests", "Test", show=True),
        Binding("ctrl+n", "new_workpad", "New Workpad", show=False),
        Binding("ctrl+h", "show_history", "History", show=False),
        Binding("r", "refresh", "Refresh", show=True),
    ]
    
    def __init__(self, repo_path: Optional[str] = None):
        super().__init__()
        self.repo_path = repo_path
        self.git_sync = GitStateSync()
        self._setup_commands()
    
    def compose(self) -> ComposeResult:
        """Compose the TUI layout."""
        yield Header(show_clock=True)
        
        with Horizontal(id="main-container"):
            # Left panel: Commit graph + File tree
            with Vertical(id="left-panel"):
                yield CommitGraphPanel(id="commit-graph", classes="panel-split")
                if self.repo_path:
                    yield FileTreeWidget(
                        repo_path=self.repo_path,
                        id="file-tree",
                        classes="panel-split"
                    )
            
            # Center panel: Workpad status + AI activity
            with Vertical(id="center-panel"):
                yield WorkpadPanel(id="workpad-panel", classes="panel-split")
                yield AIActivityPanel(id="ai-panel", classes="panel-split")
            
            # Right panel: Test runner + Diff viewer
            with Vertical(id="right-panel"):
                if self.repo_path:
                    yield TestRunnerWidget(
                        repo_path=self.repo_path,
                        id="test-runner",
                        classes="panel-split"
                    )
                yield DiffViewer(id="diff-viewer", classes="panel-split")
        
        yield StatusBar(id="status-bar")
        yield Footer()
    
    def on_mount(self) -> None:
        """Handle mount event."""
        self.title = "Heaven Interface - Solo Git"
        self.sub_title = "Frictionless Git for AI-augmented developers"
        
        # Start auto-refresh
        self.set_interval(5.0, self.auto_refresh)
        
        # Load initial data
        self.refresh_all()
    
    def _setup_commands(self) -> None:
        """Setup command palette commands."""
        registry = get_command_registry()
        
        # Clear existing commands
        registry.commands.clear()
        
        # Workpad commands
        registry.register(Command(
            id="workpad.create",
            label="Create Workpad",
            description="Create a new ephemeral workpad",
            category="Workpad",
            callback=lambda: self.action_new_workpad(),
            shortcut="Ctrl+N",
            keywords=["new", "branch", "workspace"]
        ))
        
        registry.register(Command(
            id="workpad.promote",
            label="Promote Workpad",
            description="Merge workpad to trunk",
            category="Workpad",
            callback=lambda: self.notify("Promote workpad (CLI: evogitctl workpad-integrated promote)"),
            keywords=["merge", "commit", "trunk"]
        ))
        
        # Test commands
        registry.register(Command(
            id="test.run",
            label="Run Tests",
            description="Run fast tests on active workpad",
            category="Testing",
            callback=lambda: self.action_run_tests(),
            shortcut="Ctrl+T",
            keywords=["pytest", "test"]
        ))
        
        registry.register(Command(
            id="test.clear",
            label="Clear Test Output",
            description="Clear test output display",
            category="Testing",
            callback=lambda: self._clear_test_output(),
            keywords=["clean", "reset"]
        ))
        
        # AI commands
        registry.register(Command(
            id="ai.generate",
            label="Generate Code",
            description="Generate code using AI",
            category="AI",
            callback=lambda: self.notify("AI Code Generation (CLI: evogitctl ai generate)"),
            shortcut="Ctrl+G",
            keywords=["create", "code", "ai"]
        ))
        
        registry.register(Command(
            id="ai.review",
            label="Review Code",
            description="AI code review",
            category="AI",
            callback=lambda: self.notify("AI Code Review (CLI: evogitctl ai review)"),
            shortcut="Ctrl+R",
            keywords=["check", "lint", "ai"]
        ))
        
        # History commands
        registry.register(Command(
            id="history.undo",
            label="Undo",
            description="Undo last command",
            category="History",
            callback=lambda: self.action_undo(),
            shortcut="Ctrl+Z",
            keywords=["revert", "back"]
        ))
        
        registry.register(Command(
            id="history.redo",
            label="Redo",
            description="Redo last undone command",
            category="History",
            callback=lambda: self.action_redo(),
            shortcut="Ctrl+Y",
            keywords=["forward", "again"]
        ))
        
        # View commands
        registry.register(Command(
            id="view.refresh",
            label="Refresh All",
            description="Refresh all panels",
            category="View",
            callback=lambda: self.refresh_all(),
            shortcut="R",
            keywords=["reload", "update"]
        ))
        
        registry.register(Command(
            id="view.help",
            label="Show Help",
            description="Show keyboard shortcuts",
            category="View",
            callback=lambda: self.action_help(),
            shortcut="?",
            keywords=["shortcuts", "keys", "commands"]
        ))
    
    def action_command_palette(self) -> None:
        """Show command palette."""
        show_command_palette(self)
    
    def action_help(self) -> None:
        """Show help screen."""
        self.push_screen(HelpScreen())
    
    def action_undo(self) -> None:
        """Undo last command."""
        if can_undo():
            try:
                entry = undo()
                self.notify(f"Undone: {entry.description}", severity="information")
                self.refresh_all()
            except Exception as e:
                self.notify(f"Undo failed: {e}", severity="error")
        else:
            self.notify("Nothing to undo", severity="warning")
    
    def action_redo(self) -> None:
        """Redo last undone command."""
        if can_redo():
            try:
                entry = redo()
                self.notify(f"Redone: {entry.description}", severity="information")
                self.refresh_all()
            except Exception as e:
                self.notify(f"Redo failed: {e}", severity="error")
        else:
            self.notify("Nothing to redo", severity="warning")
    
    def action_run_tests(self) -> None:
        """Run tests."""
        try:
            test_runner = self.query_one("#test-runner", TestRunnerWidget)
            test_runner.run_tests("fast")
            self.notify("Running tests...", severity="information")
        except Exception as e:
            self.notify(f"Failed to run tests: {e}", severity="error")
    
    def action_new_workpad(self) -> None:
        """Create new workpad."""
        self.notify("Create workpad (CLI: evogitctl workpad-integrated create <title>)", severity="information")
    
    def action_show_history(self) -> None:
        """Show command history."""
        history = get_command_history()
        stats = history.get_statistics()
        self.notify(
            f"Command History: {stats['total_commands']} commands, "
            f"{stats['undoable_commands']} undoable",
            severity="information"
        )
    
    def action_refresh(self) -> None:
        """Refresh all panels."""
        self.refresh_all()
        self.notify("Refreshed all panels", severity="information")
    
    def refresh_all(self) -> None:
        """Refresh all panels with latest data."""
        try:
            # Get active context
            context = self.git_sync.get_active_context()
            repo_id = context.get('repo_id')
            workpad_id = context.get('workpad_id')
            
            # Update commit graph
            if repo_id:
                commits = self.git_sync.get_history(repo_id, limit=20)
                commit_graph = self.query_one("#commit-graph", CommitGraphPanel)
                commit_graph.update_commits(commits)
                
                repo = self.git_sync.get_repo(repo_id)
                repo_name = repo.get('name', 'Unknown')
            else:
                repo_name = "No repository"
            
            # Update workpad panel
            workpads = self.git_sync.list_workpads(repo_id)
            workpad_panel = self.query_one("#workpad-panel", WorkpadPanel)
            workpad_panel.update_workpads(workpads, workpad_id)
            
            workpad_name = None
            if workpad_id:
                for wp in workpads:
                    if wp['id'] == workpad_id:
                        workpad_name = wp.get('title', 'Untitled')
                        break
            
            # Update AI activity
            ai_ops = self.git_sync.list_ai_operations(workpad_id)
            ai_panel = self.query_one("#ai-panel", AIActivityPanel)
            ai_panel.update_operations(ai_ops)
            
            # Update status bar
            status_bar = self.query_one("#status-bar", StatusBar)
            status_bar.update_context(repo_name, workpad_name)
            
        except Exception as e:
            logger.error(f"Refresh failed: {e}", exc_info=True)
    
    def auto_refresh(self) -> None:
        """Auto-refresh panels periodically."""
        self.refresh_all()
    
    def _clear_test_output(self) -> None:
        """Clear test output."""
        try:
            test_runner = self.query_one("#test-runner", TestRunnerWidget)
            test_runner.clear_output()
            self.notify("Test output cleared", severity="information")
        except Exception as e:
            logger.error(f"Failed to clear test output: {e}")
    
    def on_tests_completed(self, message: TestsCompleted) -> None:
        """Handle test completion."""
        result = message.result
        if result.status.value == "passed":
            self.notify(
                f"Tests passed! {result.passed}/{result.total} in {result.duration:.1f}s",
                severity="information"
            )
        else:
            self.notify(
                f"Tests failed! {result.failed}/{result.total} failures",
                severity="error"
            )
        
        self.refresh_all()


def run_heaven_tui(repo_path: Optional[str] = None) -> None:
    """
    Run the Heaven Interface TUI.
    
    Args:
        repo_path: Path to repository (optional)
    """
    app = HeavenTUI(repo_path=repo_path)
    app.run()


if __name__ == "__main__":
    run_heaven_tui()
