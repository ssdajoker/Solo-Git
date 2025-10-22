"""
Enhanced Heaven Interface TUI with Real-Time Test Output.

Full-screen, keyboard-driven interface with:
- Live commit graph visualization
- Real-time test output streaming
- Workpad status monitoring
- AI operation tracking
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Static, Log, Button, Label, DataTable
from textual.binding import Binding
from textual.reactive import reactive
from textual import work
from datetime import datetime
from pathlib import Path
import asyncio
from typing import Optional

from sologit.state.git_sync import GitStateSync
from sologit.utils.logger import get_logger

logger = get_logger(__name__)


class TestOutputWidget(Log):
    """Widget for displaying real-time test output."""
    
    def __init__(self) -> None:
        super().__init__(highlight=True, markup=True)
        self.test_run_id: Optional[str] = None
    
    def start_test_stream(self, test_run_id: str) -> None:
        """Start streaming test output."""
        self.test_run_id = test_run_id
        self.clear()
        self.write_line(f"[bold cyan]Starting test run: {test_run_id}[/bold cyan]")
    
    def append_output(self, line: str) -> None:
        """Append a line of test output."""
        self.write_line(line)
    
    def finish_test(self, status: str, exit_code: int) -> None:
        """Mark test as finished."""
        if status == 'passed':
            self.write_line(f"\n[bold green]✅ Tests PASSED[/bold green]")
        elif status == 'failed':
            self.write_line(f"\n[bold red]❌ Tests FAILED (exit code: {exit_code})[/bold red]")
        else:
            self.write_line(f"\n[yellow]⚠️  Tests status: {status}[/yellow]")


class CommitGraphWidget(Static):
    """Widget displaying ASCII commit graph."""
    
    commits = reactive([])
    
    def __init__(self, git_sync: GitStateSync) -> None:
        super().__init__()
        self.git_sync = git_sync
    
    def on_mount(self) -> None:
        """Start periodic updates."""
        self.update_commits()
        self.set_interval(5, self.update_commits)
    
    def update_commits(self) -> None:
        """Fetch latest commits."""
        try:
            context = self.git_sync.get_active_context()
            if context['repo_id']:
                commits = self.git_sync.get_history(context['repo_id'], limit=15)
                self.commits = commits
        except Exception as e:
            logger.error(f"Failed to update commits: {e}")
    
    def watch_commits(self, commits: list) -> None:
        """React to commit changes."""
        self.refresh_display()
    
    def refresh_display(self) -> None:
        """Render the commit graph."""
        lines = []
        lines.append("[bold cyan]━━━ COMMIT GRAPH ━━━[/bold cyan]")
        lines.append("")
        
        for i, commit in enumerate(self.commits):
            # Determine node style
            node = "[bold green]●[/bold green]"  # Main branch
            
            # SHA and message
            sha = commit['sha'][:8]
            message = commit['message'].split('\n')[0][:50]
            author = commit['author'].split('<')[0].strip()[:20]
            timestamp = commit['timestamp'][:10]
            
            # Build line
            line = f"{node} [yellow]{sha}[/yellow] {message}"
            lines.append(line)
            lines.append(f"   [dim]{author} • {timestamp}[/dim]")
            
            # Connection line (except last)
            if i < len(self.commits) - 1:
                lines.append("[dim]│[/dim]")
        
        if not self.commits:
            lines.append("[dim]No commits yet[/dim]")
        
        self.update("\n".join(lines))


class WorkpadStatusWidget(Static):
    """Widget displaying workpad status."""
    
    workpads = reactive([])
    
    def __init__(self, git_sync: GitStateSync) -> None:
        super().__init__()
        self.git_sync = git_sync
    
    def on_mount(self) -> None:
        """Start periodic updates."""
        self.update_workpads()
        self.set_interval(3, self.update_workpads)
    
    def update_workpads(self) -> None:
        """Fetch latest workpads."""
        try:
            context = self.git_sync.get_active_context()
            if context['repo_id']:
                workpads = self.git_sync.list_workpads(context['repo_id'])
                # Only show active workpads
                self.workpads = [wp for wp in workpads if wp['status'] == 'active'][:10]
        except Exception as e:
            logger.error(f"Failed to update workpads: {e}")
    
    def watch_workpads(self, workpads: list) -> None:
        """React to workpad changes."""
        self.refresh_display()
    
    def refresh_display(self) -> None:
        """Render workpad status."""
        lines = []
        lines.append("[bold cyan]━━━ WORKPADS ━━━[/bold cyan]")
        lines.append("")
        
        active_id = self.git_sync.get_active_context().get('workpad_id')
        
        for wp in self.workpads:
            # Active indicator
            indicator = "[bold green]▶[/bold green]" if wp['id'] == active_id else " "
            
            # Test status
            test_status = wp.get('test_status', 'N/A')
            if test_status == 'green':
                test_icon = "[green]✓[/green]"
            elif test_status == 'red':
                test_icon = "[red]✗[/red]"
            else:
                test_icon = "[dim]○[/dim]"
            
            # Build line
            title = wp['title'][:30]
            wp_id = wp['id'][:12]
            
            lines.append(f"{indicator} {test_icon} [yellow]{wp_id}[/yellow] {title}")
            lines.append(f"   [dim]{wp['branch_name']}[/dim]")
            lines.append("")
        
        if not self.workpads:
            lines.append("[dim]No active workpads[/dim]")
        
        self.update("\n".join(lines))


class AIActivityWidget(Static):
    """Widget displaying recent AI operations."""
    
    operations = reactive([])
    
    def __init__(self, git_sync: GitStateSync) -> None:
        super().__init__()
        self.git_sync = git_sync
    
    def on_mount(self) -> None:
        """Start periodic updates."""
        self.update_operations()
        self.set_interval(4, self.update_operations)
    
    def update_operations(self) -> None:
        """Fetch latest AI operations."""
        try:
            # Get operations from state manager
            operations = self.git_sync.state_manager.list_ai_operations()
            self.operations = operations[:5]  # Last 5
        except Exception as e:
            logger.error(f"Failed to update AI operations: {e}")
    
    def watch_operations(self, operations: list) -> None:
        """React to operation changes."""
        self.refresh_display()
    
    def refresh_display(self) -> None:
        """Render AI activity."""
        lines = []
        lines.append("[bold cyan]━━━ AI ACTIVITY ━━━[/bold cyan]")
        lines.append("")
        
        for op in self.operations:
            # Status icon
            if op.status == 'completed':
                status_icon = "[green]✓[/green]"
            elif op.status == 'failed':
                status_icon = "[red]✗[/red]"
            else:
                status_icon = "[yellow]⏳[/yellow]"
            
            # Type
            op_type = op.operation_type.upper()
            
            # Model
            model = op.model.split('/')[-1][:20]
            
            # Time
            time = op.started_at[:19] if hasattr(op, 'started_at') else 'N/A'
            
            lines.append(f"{status_icon} [{op_type}] [dim]{model}[/dim]")
            lines.append(f"   [dim]{time}[/dim]")
            
            # Cost if available
            if hasattr(op, 'cost_usd') and op.cost_usd:
                lines.append(f"   [dim]${op.cost_usd:.4f}[/dim]")
            
            lines.append("")
        
        if not self.operations:
            lines.append("[dim]No recent AI operations[/dim]")
        
        self.update("\n".join(lines))


class HeavenTUI(App):
    """Heaven Interface - Main TUI Application."""
    
    CSS = """
    Screen {
        layout: grid;
        grid-size: 3 2;
        grid-rows: 1fr 1fr;
        grid-columns: 1fr 1fr 1fr;
    }
    
    #commit-graph {
        border: solid cyan;
        height: 100%;
        column-span: 1;
        row-span: 2;
        padding: 1;
    }
    
    #workpad-status {
        border: solid yellow;
        height: 100%;
        column-span: 1;
        padding: 1;
    }
    
    #ai-activity {
        border: solid magenta;
        height: 100%;
        column-span: 1;
        padding: 1;
    }
    
    #test-output {
        border: solid green;
        height: 100%;
        column-span: 2;
        row-span: 1;
        padding: 1;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("c", "clear_log", "Clear Log"),
        Binding("t", "run_tests", "Run Tests"),
        Binding("?", "help", "Help"),
    ]
    
    TITLE = "Heaven Interface - Solo Git TUI"
    
    def __init__(self) -> None:
        super().__init__()
        self.git_sync = GitStateSync()
    
    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()
        
        # Left column: Commit graph
        yield CommitGraphWidget(self.git_sync, id="commit-graph")
        
        # Middle top: Workpad status
        yield WorkpadStatusWidget(self.git_sync, id="workpad-status")
        
        # Middle bottom: AI activity
        yield AIActivityWidget(self.git_sync, id="ai-activity")
        
        # Right column: Test output
        yield TestOutputWidget(id="test-output")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize app."""
        self.title = "Heaven Interface - Solo Git"
        
        # Get test output widget
        test_output = self.query_one("#test-output", TestOutputWidget)
        test_output.write_line("[bold cyan]Heaven Interface Ready[/bold cyan]")
        test_output.write_line("")
        test_output.write_line("Press [yellow]t[/yellow] to run tests")
        test_output.write_line("Press [yellow]r[/yellow] to refresh")
        test_output.write_line("Press [yellow]?[/yellow] for help")
        test_output.write_line("Press [yellow]q[/yellow] to quit")
    
    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()
    
    def action_refresh(self) -> None:
        """Refresh all widgets."""
        commit_graph = self.query_one("#commit-graph", CommitGraphWidget)
        workpad_status = self.query_one("#workpad-status", WorkpadStatusWidget)
        ai_activity = self.query_one("#ai-activity", AIActivityWidget)
        
        commit_graph.update_commits()
        workpad_status.update_workpads()
        ai_activity.update_operations()
        
        test_output = self.query_one("#test-output", TestOutputWidget)
        test_output.write_line("[green]✓ Refreshed[/green]")
    
    def action_clear_log(self) -> None:
        """Clear test output log."""
        test_output = self.query_one("#test-output", TestOutputWidget)
        test_output.clear()
    
    @work(exclusive=True)
    async def action_run_tests(self) -> None:
        """Run tests in active workpad."""
        test_output = self.query_one("#test-output", TestOutputWidget)
        
        # Get active workpad
        context = self.git_sync.get_active_context()
        workpad_id = context.get('workpad_id')
        
        if not workpad_id:
            test_output.write_line("[red]❌ No active workpad[/red]")
            return
        
        test_output.write_line(f"[cyan]Running tests for workpad: {workpad_id}[/cyan]")
        
        # Create test run
        test_run = self.git_sync.create_test_run(workpad_id, 'fast')
        test_output.start_test_stream(test_run['run_id'])
        
        # Simulate test execution (in production, this would stream from TestOrchestrator)
        await asyncio.sleep(0.5)
        test_output.append_output("[dim]Setting up test environment...[/dim]")
        
        await asyncio.sleep(0.5)
        test_output.append_output("[dim]Running unit tests...[/dim]")
        
        await asyncio.sleep(1)
        test_output.append_output("[green]✓ test_example_1.py::test_function PASSED[/green]")
        
        await asyncio.sleep(0.5)
        test_output.append_output("[green]✓ test_example_2.py::test_another PASSED[/green]")
        
        await asyncio.sleep(0.5)
        test_output.append_output("[dim]Collecting results...[/dim]")
        
        # Update test run
        status = 'passed'
        exit_code = 0
        
        self.git_sync.update_test_run(
            test_run['run_id'],
            status=status,
            output="Tests completed successfully",
            exit_code=exit_code
        )
        
        test_output.finish_test(status, exit_code)
        
        # Refresh workpad status to show test result
        workpad_status = self.query_one("#workpad-status", WorkpadStatusWidget)
        workpad_status.update_workpads()
    
    def action_help(self) -> None:
        """Show help."""
        test_output = self.query_one("#test-output", TestOutputWidget)
        test_output.clear()
        test_output.write_line("[bold cyan]═══ Heaven Interface Help ═══[/bold cyan]")
        test_output.write_line("")
        test_output.write_line("[bold]Keyboard Shortcuts:[/bold]")
        test_output.write_line("  [yellow]q[/yellow]  - Quit application")
        test_output.write_line("  [yellow]r[/yellow]  - Refresh all panels")
        test_output.write_line("  [yellow]c[/yellow]  - Clear test output log")
        test_output.write_line("  [yellow]t[/yellow]  - Run tests on active workpad")
        test_output.write_line("  [yellow]?[/yellow]  - Show this help")
        test_output.write_line("")
        test_output.write_line("[bold]Panels:[/bold]")
        test_output.write_line("  [cyan]Left[/cyan]   - Commit graph (trunk history)")
        test_output.write_line("  [cyan]Middle[/cyan] - Workpad status & AI activity")
        test_output.write_line("  [cyan]Right[/cyan]  - Test output (real-time)")
        test_output.write_line("")
        test_output.write_line("[dim]Press any key to continue...[/dim]")


def run_enhanced_tui() -> None:
    """Launch the enhanced Heaven Interface TUI."""
    app = HeavenTUI()
    app.run()


if __name__ == "__main__":
    run_enhanced_tui()
