
"""
Heaven Interface - Interactive TUI Application using Textual.

Provides a full-screen, keyboard-driven interface for Solo Git operations.
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Tree, Log, Button, Input, Label
from textual.binding import Binding
from textual.reactive import reactive
from textual import work
from datetime import datetime
from pathlib import Path
import asyncio

from sologit.state.manager import StateManager
from sologit.ui.theme import theme


class CommitGraphWidget(Static):
    """Widget displaying commit graph."""
    
    def __init__(self, state_manager: StateManager):
        super().__init__()
        self.state_manager = state_manager
        self.commits = []
    
    def on_mount(self) -> None:
        self.update_commits()
        self.set_interval(5, self.update_commits)
    
    def update_commits(self) -> None:
        """Update commits from state."""
        context = self.state_manager.get_active_context()
        if context['repo_id']:
            self.commits = self.state_manager.get_commits(context['repo_id'], limit=15)
            self.refresh_display()
    
    def refresh_display(self) -> None:
        """Refresh the display."""
        lines = []
        lines.append("━━━ COMMIT GRAPH ━━━")
        lines.append("")
        
        for i, commit in enumerate(self.commits):
            # Node
            node = "●" if commit.is_trunk else "○"
            
            # Status
            if commit.test_status == 'passed':
                status = "✓"
            elif commit.test_status == 'failed':
                status = "✗"
            else:
                status = " "
            
            # Line
            line = f"{node} {status} {commit.short_sha} {commit.message[:40]}"
            lines.append(line)
            
            # Connection (except last)
            if i < len(self.commits) - 1:
                lines.append("│")
        
        self.update("\n".join(lines))


class WorkpadListWidget(Static):
    """Widget displaying workpad list."""
    
    def __init__(self, state_manager: StateManager):
        super().__init__()
        self.state_manager = state_manager
        self.workpads = []
    
    def on_mount(self) -> None:
        self.update_workpads()
        self.set_interval(3, self.update_workpads)
    
    def update_workpads(self) -> None:
        """Update workpads from state."""
        context = self.state_manager.get_active_context()
        if context['repo_id']:
            self.workpads = self.state_manager.list_workpads(context['repo_id'])[:10]
            self.refresh_display()
    
    def refresh_display(self) -> None:
        """Refresh the display."""
        lines = []
        lines.append("━━━ WORKPADS ━━━")
        lines.append("")
        
        active_id = self.state_manager.get_active_context()['workpad_id']
        
        for wp in self.workpads:
            status_icon = "●" if wp.workpad_id == active_id else "○"
            
            if wp.status == 'passed':
                status_char = "✓"
            elif wp.status == 'failed':
                status_char = "✗"
            elif wp.status == 'testing':
                status_char = "◉"
            else:
                status_char = " "
            
            line = f"{status_icon} {status_char} {wp.title[:35]}"
            lines.append(line)
        
        if not self.workpads:
            lines.append("No workpads")
        
        self.update("\n".join(lines))


class StatusBarWidget(Static):
    """Widget displaying status bar."""
    
    def __init__(self, state_manager: StateManager):
        super().__init__()
        self.state_manager = state_manager
    
    def on_mount(self) -> None:
        self.update_status()
        self.set_interval(1, self.update_status)
    
    def update_status(self) -> None:
        """Update status from state."""
        context = self.state_manager.get_active_context()
        global_state = self.state_manager.get_global_state()
        
        repo_name = "No repo"
        if context['repo_id']:
            repo = self.state_manager.get_repository(context['repo_id'])
            repo_name = repo.name if repo else context['repo_id'][:8]
        
        workpad_name = "No workpad"
        if context['workpad_id']:
            wp = self.state_manager.get_workpad(context['workpad_id'])
            workpad_name = wp.title[:20] if wp else context['workpad_id'][:8]
        
        status_text = f"📁 {repo_name}  |  🏷️  {workpad_name}  |  💰 ${global_state.total_cost_usd:.2f}"
        self.update(status_text)


class LogViewerWidget(Log):
    """Widget for viewing logs."""
    
    def __init__(self):
        super().__init__()
        self.max_lines = 1000


class HeavenTUI(App):
    """Heaven Interface TUI Application."""
    
    CSS = """
    Screen {
        background: #1E1E1E;
    }
    
    Header {
        background: #252526;
        color: #61AFEF;
        text-style: bold;
    }
    
    Footer {
        background: #252526;
        color: #5C6370;
    }
    
    #left_panel {
        width: 30;
        background: #252526;
        border: solid #5C6370;
        padding: 1;
    }
    
    #main_panel {
        background: #1E1E1E;
        padding: 1;
    }
    
    #status_bar {
        dock: bottom;
        height: 3;
        background: #252526;
        color: #DDDDDD;
        padding: 1;
    }
    
    CommitGraphWidget {
        height: 50%;
        border: solid #61AFEF;
        padding: 1;
        color: #DDDDDD;
    }
    
    WorkpadListWidget {
        height: 50%;
        border: solid #C678DD;
        padding: 1;
        color: #DDDDDD;
    }
    
    LogViewerWidget {
        border: solid #5C6370;
        color: #DDDDDD;
        background: #1E1E1E;
    }
    
    StatusBarWidget {
        color: #DDDDDD;
    }
    
    Input {
        dock: bottom;
        background: #252526;
        color: #DDDDDD;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("r", "refresh", "Refresh"),
        Binding("c", "clear_log", "Clear Log"),
        Binding("g", "show_graph", "Graph"),
        Binding("w", "show_workpads", "Workpads"),
        Binding("?", "help", "Help"),
    ]
    
    TITLE = "Solo Git - Heaven Interface"
    
    def __init__(self):
        super().__init__()
        self.state_manager = StateManager()
    
    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()
        
        with Horizontal():
            # Left panel - navigation
            with Vertical(id="left_panel"):
                yield CommitGraphWidget(self.state_manager)
                yield WorkpadListWidget(self.state_manager)
            
            # Main panel - logs and output
            with Vertical(id="main_panel"):
                yield LogViewerWidget()
        
        # Status bar
        with Container(id="status_bar"):
            yield StatusBarWidget(self.state_manager)
        
        # Command input (bottom)
        yield Input(placeholder="Type command... (or press ? for help)")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Called when app is mounted."""
        log = self.query_one(LogViewerWidget)
        log.write_line("╔══════════════════════════════════════════════════╗")
        log.write_line("║   Welcome to Solo Git - Heaven Interface        ║")
        log.write_line("║   Minimalist. Keyboard-first. AI-powered.       ║")
        log.write_line("╚══════════════════════════════════════════════════╝")
        log.write_line("")
        log.write_line("Press ? for help, q to quit")
        log.write_line("")
        
        # Load initial state
        context = self.state_manager.get_active_context()
        if context['repo_id']:
            repo = self.state_manager.get_repository(context['repo_id'])
            if repo:
                log.write_line(f"✓ Active repository: {repo.name}")
        else:
            log.write_line("⚠ No active repository. Initialize one with CLI.")
    
    def action_refresh(self) -> None:
        """Refresh all widgets."""
        log = self.query_one(LogViewerWidget)
        log.write_line("🔄 Refreshing...")
        
        # Refresh all widgets
        for widget in self.query(CommitGraphWidget):
            widget.update_commits()
        for widget in self.query(WorkpadListWidget):
            widget.update_workpads()
        for widget in self.query(StatusBarWidget):
            widget.update_status()
    
    def action_clear_log(self) -> None:
        """Clear the log."""
        log = self.query_one(LogViewerWidget)
        log.clear()
        log.write_line("Log cleared")
    
    def action_show_graph(self) -> None:
        """Show commit graph."""
        log = self.query_one(LogViewerWidget)
        context = self.state_manager.get_active_context()
        
        if not context['repo_id']:
            log.write_line("⚠ No active repository")
            return
        
        commits = self.state_manager.get_commits(context['repo_id'], limit=20)
        
        log.write_line("")
        log.write_line("━━━ COMMIT GRAPH ━━━")
        log.write_line("")
        
        for commit in commits:
            node = "●" if commit.is_trunk else "○"
            status = "✓" if commit.test_status == 'passed' else "✗" if commit.test_status == 'failed' else " "
            log.write_line(f"{node} {status} {commit.short_sha} {commit.message[:60]}")
    
    def action_show_workpads(self) -> None:
        """Show workpads."""
        log = self.query_one(LogViewerWidget)
        context = self.state_manager.get_active_context()
        
        if not context['repo_id']:
            log.write_line("⚠ No active repository")
            return
        
        workpads = self.state_manager.list_workpads(context['repo_id'])
        
        log.write_line("")
        log.write_line("━━━ WORKPADS ━━━")
        log.write_line("")
        
        for wp in workpads[:15]:
            status_icon = "✓" if wp.status == 'passed' else "✗" if wp.status == 'failed' else "◉" if wp.status == 'testing' else "○"
            log.write_line(f"{status_icon} {wp.title} - {wp.status}")
    
    def action_help(self) -> None:
        """Show help."""
        log = self.query_one(LogViewerWidget)
        log.write_line("")
        log.write_line("━━━ KEYBOARD SHORTCUTS ━━━")
        log.write_line("")
        log.write_line("q       - Quit application")
        log.write_line("r       - Refresh all panels")
        log.write_line("c       - Clear log")
        log.write_line("g       - Show commit graph")
        log.write_line("w       - Show workpads")
        log.write_line("?       - Show this help")
        log.write_line("")
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle command input."""
        log = self.query_one(LogViewerWidget)
        command = event.value.strip()
        
        if command:
            log.write_line(f"> {command}")
            log.write_line("⚠ Command execution not yet implemented in TUI")
            log.write_line("  Use CLI for now: evogitctl <command>")
        
        event.input.value = ""


def run_tui():
    """Run the TUI application."""
    app = HeavenTUI()
    app.run()


if __name__ == "__main__":
    run_tui()
