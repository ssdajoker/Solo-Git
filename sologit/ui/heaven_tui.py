"""
Heaven Interface - Comprehensive TUI for Solo Git.

Integrates all UI components into a production-ready interface following
the Heaven Interface Design System specifications.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Label, Input
from textual.screen import Screen, ModalScreen
from textual import events

from sologit.ui.command_palette import show_command_palette, Command, get_command_registry
from sologit.ui.file_tree import FileTreeWidget
from sologit.ui.test_runner import TestRunnerWidget, TestsCompleted, TestStatus
from sologit.ui.history import get_command_history, undo, redo, can_undo, can_redo
from sologit.state.git_sync import GitStateSync
from sologit.orchestration.ai_orchestrator import AIOrchestrator
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
        self.commits: List[Dict[str, Any]] = []
    
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
    
    def update_commits(self, commits: List[Dict[str, Any]]):
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
        self.workpads: List[Dict[str, Any]] = []
        self.active_workpad: Optional[str] = None
    
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
    
    def update_workpads(self, workpads: List[Dict[str, Any]], active_id: Optional[str] = None):
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
        self.operations: List[Dict[str, Any]] = []
    
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
    
    def update_operations(self, operations: List[Dict[str, Any]]):
        """Update operations list."""
        self.operations = operations
        self.refresh()


class AIResponsePanel(Static):
    """Panel that streams AI responses."""

    CSS = """
    AIResponsePanel {
        width: 1fr;
        height: 100%;
        border: solid $primary;
        padding: 1;
        overflow-y: auto;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._title: Optional[str] = None
        self._lines: List[str] = []

    def render(self) -> str:
        if not self._lines:
            body = "[dim]No AI output yet. Trigger an AI command from the palette.[/]"
        else:
            body = "\n".join(self._lines)
        header = f"[bold magenta]{self._title}[/]\n" if self._title else ""
        return f"{header}{body}"

    def start_session(self, title: str) -> None:
        """Begin a new AI streaming session."""
        self._title = title
        self._lines.clear()
        self.refresh()

    def append_line(self, line: str) -> None:
        """Append a line to the response."""
        self._lines.append(line)
        self.refresh()

    def finish_session(self, footer: Optional[str] = None) -> None:
        """Complete the session with an optional footer."""
        if footer:
            self._lines.append(footer)
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


class PromptModal(ModalScreen[Optional[str]]):
    """Simple modal prompt for collecting single-line input."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
        Binding("ctrl+c", "cancel", "Cancel", show=False),
    ]

    CSS = """
    PromptModal {
        align: center middle;
    }

    #prompt-container {
        width: 60;
        height: auto;
        border: thick $accent;
        background: $surface;
        padding: 2;
    }

    #prompt-title {
        text-style: bold;
        margin-bottom: 1;
    }
    """

    def __init__(self, title: str, message: str, placeholder: str = "", *, default: str = ""):
        super().__init__()
        self._title = title
        self._message = message
        self._placeholder = placeholder
        self._default = default

    def compose(self) -> ComposeResult:
        with Container(id="prompt-container"):
            yield Static(self._title, id="prompt-title")
            yield Static(self._message, id="prompt-message")
            yield Input(placeholder=self._placeholder, id="prompt-input", value=self._default)

    def on_mount(self) -> None:
        self.query_one("#prompt-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.value.strip()
        self.dismiss(value or None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class HeavenTUI(App):
    """
    Heaven Interface - Production-ready TUI for Solo Git.

    Implements the Heaven Interface Design System with:
    - Command palette with fuzzy search
    - File tree with git status
    - Real-time test runner
    - Commit graph visualization
    - AI operation tracking with streaming output
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
        Binding("ctrl+shift+p", "promote_workpad", "Promote", show=False),
    ]

    def __init__(
        self,
        repo_path: Optional[str] = None,
        *,
        git_sync: Optional[GitStateSync] = None,
        ai_orchestrator: Optional[AIOrchestrator] = None,
    ):
        super().__init__()
        self.repo_path = repo_path
        self.git_sync = git_sync or GitStateSync()
        self.ai_orchestrator = ai_orchestrator or AIOrchestrator()
        self._background_tasks: set[asyncio.Task] = set()
        self._active_test_run_id: Optional[str] = None
        self._last_event_timestamp: Optional[str] = None
        self._last_plan = None
        self._last_patch = None
        self._setup_commands()

    def compose(self) -> ComposeResult:
        """Compose the TUI layout."""
        yield Header(show_clock=True)

        with Horizontal(id="main-container"):
            with Vertical(id="left-panel"):
                yield CommitGraphPanel(id="commit-graph", classes="panel-split")
                if self.repo_path:
                    yield FileTreeWidget(
                        repo_path=self.repo_path,
                        id="file-tree",
                        classes="panel-split",
                    )

            with Vertical(id="center-panel"):
                yield WorkpadPanel(id="workpad-panel", classes="panel-split")
                yield AIActivityPanel(id="ai-panel", classes="panel-split")

            with Vertical(id="right-panel"):
                if self.repo_path:
                    yield TestRunnerWidget(
                        repo_path=self.repo_path,
                        id="test-runner",
                        classes="panel-split",
                    )
                yield AIResponsePanel(id="ai-response", classes="panel-split")

        yield StatusBar(id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        """Handle mount event."""
        self.title = "Heaven Interface - Solo Git"
        self.sub_title = "Frictionless Git for AI-augmented developers"
        self._last_event_timestamp = datetime.utcnow().isoformat()

        self.set_interval(5.0, self.auto_refresh)
        self.set_interval(2.0, self.poll_state_events)
        self.refresh_all()

    def _setup_commands(self) -> None:
        """Setup command palette commands."""
        registry = get_command_registry()
        registry.commands.clear()

        registry.register(
            Command(
                id="workpad.create",
                label="Create Workpad",
                description="Create a new ephemeral workpad",
                category="Workpad",
                callback=lambda: self.action_new_workpad(),
                shortcut="Ctrl+N",
                keywords=["new", "branch", "workspace"],
            )
        )

        registry.register(
            Command(
                id="workpad.promote",
                label="Promote Workpad",
                description="Merge workpad to trunk",
                category="Workpad",
                callback=lambda: self.action_promote_workpad(),
                keywords=["merge", "commit", "trunk"],
            )
        )

        registry.register(
            Command(
                id="test.run",
                label="Run Tests",
                description="Run fast tests on active workpad",
                category="Testing",
                callback=lambda: self.action_run_tests(),
                shortcut="Ctrl+T",
                keywords=["pytest", "test"],
            )
        )

        registry.register(
            Command(
                id="test.clear",
                label="Clear Test Output",
                description="Clear test output display",
                category="Testing",
                callback=lambda: self._clear_test_output(),
                keywords=["clean", "reset"],
            )
        )

        registry.register(
            Command(
                id="ai.generate",
                label="AI Generate Patch",
                description="Use AI orchestrator to plan and generate a patch",
                category="AI",
                callback=lambda: self._start_ai_generate(),
                shortcut="Ctrl+G",
                keywords=["create", "code", "ai"],
            )
        )

        registry.register(
            Command(
                id="ai.review",
                label="AI Review Patch",
                description="Review last AI-generated patch",
                category="AI",
                callback=lambda: self._start_ai_review(),
                shortcut="Ctrl+R",
                keywords=["check", "lint", "ai"],
            )
        )

        registry.register(
            Command(
                id="history.undo",
                label="Undo",
                description="Undo last command",
                category="History",
                callback=lambda: self.action_undo(),
                shortcut="Ctrl+Z",
                keywords=["revert", "back"],
            )
        )

        registry.register(
            Command(
                id="history.redo",
                label="Redo",
                description="Redo last undone command",
                category="History",
                callback=lambda: self.action_redo(),
                shortcut="Ctrl+Y",
                keywords=["forward", "again"],
            )
        )

        registry.register(
            Command(
                id="view.refresh",
                label="Refresh All",
                description="Refresh all panels",
                category="View",
                callback=lambda: self.refresh_all(),
                shortcut="R",
                keywords=["reload", "update"],
            )
        )

        registry.register(
            Command(
                id="view.help",
                label="Show Help",
                description="Show keyboard shortcuts",
                category="View",
                callback=lambda: self.action_help(),
                shortcut="?",
                keywords=["shortcuts", "keys", "commands"],
            )
        )

    def action_command_palette(self) -> None:
        show_command_palette(self)

    def action_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_undo(self) -> None:
        if can_undo():
            try:
                entry = undo()
                self.notify(f"Undone: {entry.description}", severity="information")
                self.refresh_all()
            except Exception as exc:
                self.notify(f"Undo failed: {exc}", severity="error")
        else:
            self.notify("Nothing to undo", severity="warning")

    def action_redo(self) -> None:
        if can_redo():
            try:
                entry = redo()
                self.notify(f"Redone: {entry.description}", severity="information")
                self.refresh_all()
            except Exception as exc:
                self.notify(f"Redo failed: {exc}", severity="error")
        else:
            self.notify("Nothing to redo", severity="warning")

    def action_run_tests(self) -> None:
        self._run_async(self._run_tests_async("fast"))

    def action_new_workpad(self) -> None:
        prompt = PromptModal(
            "Create Workpad",
            "Enter a title for the new workpad",
            placeholder="Feature branch title",
        )
        self.push_screen(prompt, self._handle_new_workpad_prompt)

    def action_promote_workpad(self) -> None:
        self._run_async(self._promote_workpad_async())

    def action_show_history(self) -> None:
        history = get_command_history()
        stats = history.get_statistics()
        self.notify(
            f"Command History: {stats['total_commands']} commands, {stats['undoable_commands']} undoable",
            severity="information",
        )

    def action_refresh(self) -> None:
        self.refresh_all()
        self.notify("Refreshed all panels", severity="information")

    def refresh_all(self) -> None:
        try:
            context = self.git_sync.get_active_context()
            repo_id = context.get("repo_id")
            workpad_id = context.get("workpad_id")

            repo_name = "No repository"
            if repo_id:
                commits = self.git_sync.get_history(repo_id, limit=20)
                self.query_one("#commit-graph", CommitGraphPanel).update_commits(commits)
                repo = self.git_sync.get_repo(repo_id)
                if repo:
                    repo_name = repo.get("name", "Unknown")

            workpads = self.git_sync.list_workpads(repo_id)
            self.query_one("#workpad-panel", WorkpadPanel).update_workpads(workpads, workpad_id)

            workpad_name = None
            if workpad_id:
                for wp in workpads:
                    if wp.get("id") == workpad_id:
                        workpad_name = wp.get("title", "Untitled")
                        break

            ai_ops = self.git_sync.list_ai_operations(workpad_id)
            self.query_one("#ai-panel", AIActivityPanel).update_operations(ai_ops)

            test_status_icon = "○"
            if workpad_id:
                runs = self.git_sync.get_test_runs(workpad_id)
                if runs:
                    latest = runs[0]
                    status = latest.get("status")
                    if status == "passed":
                        test_status_icon = "✓"
                    elif status == "failed":
                        test_status_icon = "✗"
                    elif status == "running":
                        test_status_icon = "⟳"

            self.query_one("#status-bar", StatusBar).update_context(
                repo_name, workpad_name, test_status_icon
            )
        except Exception as exc:
            logger.error("Refresh failed: %s", exc, exc_info=True)

    def auto_refresh(self) -> None:
        self.refresh_all()

    def poll_state_events(self) -> None:
        try:
            events = self.git_sync.state_manager.get_events(
                since=self._last_event_timestamp,
                limit=20,
            )
            if not events:
                return

            newest = max(event.timestamp for event in events)
            self._last_event_timestamp = newest

            relevant = {
                "workpad_created",
                "workpad_updated",
                "workpad_promoted",
                "test_started",
                "test_completed",
                "ai_operation_started",
                "ai_operation_completed",
                "commit_created",
            }

            if any(event.event_type in relevant for event in events):
                self.refresh_all()
        except Exception as exc:
            logger.debug("Event polling failed: %s", exc)

    def _clear_test_output(self) -> None:
        try:
            test_runner = self.query_one("#test-runner", TestRunnerWidget)
            test_runner.clear_output()
            self.notify("Test output cleared", severity="information")
        except Exception as exc:
            logger.error("Failed to clear test output: %s", exc)

    def on_tests_completed(self, message: TestsCompleted) -> None:
        result = message.result
        status_map = {
            TestStatus.PASSED: "passed",
            TestStatus.FAILED: "failed",
            TestStatus.ERROR: "failed",
            TestStatus.CANCELLED: "failed",
        }
        status = status_map.get(result.status, "failed")
        exit_code = 0 if status == "passed" else 1
        output = result.output or ""

        if status == "passed":
            self.notify(
                f"Tests passed! {result.passed}/{result.total} in {result.duration:.1f}s",
                severity="information",
            )
        else:
            self.notify(
                f"Tests failed! {result.failed}/{result.total} failures",
                severity="error",
            )

        self._run_async(self._finalize_test_run(status, exit_code, output))

    def _run_async(self, coro) -> None:
        async def runner() -> None:
            try:
                await coro
            except Exception as exc:
                logger.error("Background task failed: %s", exc, exc_info=True)
                self.notify(f"Operation failed: {exc}", severity="error")

        task = asyncio.create_task(runner())
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    def _handle_new_workpad_prompt(self, title: Optional[str]) -> None:
        if not title:
            self.notify("Workpad creation cancelled", severity="warning")
            return
        self._run_async(self._create_workpad_async(title))

    async def _create_workpad_async(self, title: str) -> None:
        title = title.strip() or f"Workpad {datetime.utcnow().strftime('%H%M%S')}"
        context = self.git_sync.get_active_context()
        repo_id = context.get("repo_id")
        if not repo_id:
            self.notify("No active repository", severity="error")
            return

        workpad = await asyncio.to_thread(self.git_sync.create_workpad, repo_id, title)
        self.notify(f"Created workpad {workpad['title']}", severity="information")
        self.refresh_all()

    async def _promote_workpad_async(self) -> None:
        context = self.git_sync.get_active_context()
        workpad_id = context.get("workpad_id")
        if not workpad_id:
            self.notify("No active workpad", severity="warning")
            return

        try:
            merge_commit = await asyncio.to_thread(
                self.git_sync.promote_workpad, workpad_id
            )
            self.notify(
                f"Promoted workpad {workpad_id[:8]} → {merge_commit[:8]}",
                severity="information",
            )
        except Exception as exc:
            self.notify(f"Promotion failed: {exc}", severity="error")
            logger.error("Promotion failed", exc_info=True)
        finally:
            self.refresh_all()

    async def _run_tests_async(self, target: str) -> None:
        if not self.repo_path:
            self.notify("Tests unavailable without repository path", severity="warning")
            return

        context = self.git_sync.get_active_context()
        workpad_id = context.get("workpad_id")
        if not workpad_id:
            self.notify("No active workpad", severity="warning")
            return

        test_runner = self.query_one("#test-runner", TestRunnerWidget)
        test_run = await asyncio.to_thread(self.git_sync.create_test_run, workpad_id, target)
        self._active_test_run_id = test_run["run_id"]
        await asyncio.to_thread(self.git_sync.update_test_run, self._active_test_run_id, "running")
        test_runner.run_tests(target)
        self.notify("Running tests...", severity="information")

    async def _finalize_test_run(self, status: str, exit_code: int, output: str) -> None:
        if not self._active_test_run_id:
            return
        await asyncio.to_thread(
            self.git_sync.update_test_run,
            self._active_test_run_id,
            status,
            output,
            exit_code,
        )
        self._active_test_run_id = None
        self.refresh_all()

    def _start_ai_generate(self) -> None:
        prompt = PromptModal(
            "AI Generate Patch",
            "Describe the change you want the AI to implement",
            placeholder="Add feature X to module Y",
        )
        self.push_screen(prompt, self._handle_ai_generate_prompt)

    def _handle_ai_generate_prompt(self, prompt: Optional[str]) -> None:
        if not prompt:
            self.notify("AI generate cancelled", severity="warning")
            return
        self._run_async(self._run_ai_generate(prompt))

    async def _run_ai_generate(self, prompt: str) -> None:
        panel = self.query_one("#ai-response", AIResponsePanel)
        panel.start_session("AI Generation")
        panel.append_line("[cyan]Planning change...[/]")

        context = self.git_sync.get_active_context()
        repo_id = context.get("repo_id")
        workpad_id = context.get("workpad_id")
        repo_context = self._gather_repo_context(repo_id)

        planning_op = await asyncio.to_thread(
            self.git_sync.create_ai_operation,
            workpad_id,
            "planning",
            "pending",
            prompt,
        )
        await asyncio.to_thread(
            self.git_sync.state_manager.update_ai_operation,
            planning_op["operation_id"],
            status="planning",
        )

        coding_op = None
        try:
            plan_response = await asyncio.to_thread(
                self.ai_orchestrator.plan,
                prompt,
                repo_context,
            )
            plan_text = str(plan_response.plan)
            for line in plan_text.splitlines():
                panel.append_line(line)

            await asyncio.to_thread(
                self.git_sync.state_manager.update_ai_operation,
                planning_op["operation_id"],
                status="completed",
                response=plan_text,
                cost_usd=plan_response.cost_usd,
                model=plan_response.model_used,
            )
            self._last_plan = plan_response.plan

            coding_op = await asyncio.to_thread(
                self.git_sync.create_ai_operation,
                workpad_id,
                "coding",
                "pending",
                prompt,
            )
            await asyncio.to_thread(
                self.git_sync.state_manager.update_ai_operation,
                coding_op["operation_id"],
                status="coding",
            )

            panel.append_line("")
            panel.append_line("[cyan]Generating patch...[/]")
            file_contents = self._collect_file_context(plan_response.plan, repo_id)
            patch_response = await asyncio.to_thread(
                self.ai_orchestrator.generate_patch,
                plan_response.plan,
                file_contents,
            )

            diff = patch_response.patch.diff or "(no diff returned)"
            panel.append_line("```diff")
            for line in diff.splitlines():
                panel.append_line(line)
            panel.append_line("```")

            await asyncio.to_thread(
                self.git_sync.state_manager.update_ai_operation,
                coding_op["operation_id"],
                status="completed",
                response=diff,
                cost_usd=patch_response.cost_usd,
                model=patch_response.model_used,
            )

            self._last_patch = patch_response.patch
            panel.finish_session("[green]AI generation complete[/]")
            self.notify("AI patch generated", severity="information")
        except Exception as exc:
            panel.append_line("")
            panel.append_line(f"[red]AI generation failed: {exc}[/]")
            target_op = coding_op or planning_op
            await asyncio.to_thread(
                self.git_sync.state_manager.update_ai_operation,
                target_op["operation_id"],
                status="failed",
                error=str(exc),
            )
            self.notify(f"AI generation failed: {exc}", severity="error")
        finally:
            self.refresh_all()

    def _start_ai_review(self) -> None:
        self._run_async(self._run_ai_review())

    async def _run_ai_review(self) -> None:
        if not self._last_patch:
            self.notify("Generate a patch before requesting a review", severity="warning")
            return

        panel = self.query_one("#ai-response", AIResponsePanel)
        panel.start_session("AI Review")
        panel.append_line("[cyan]Reviewing last generated patch...[/]")

        context = self.git_sync.get_active_context()
        workpad_id = context.get("workpad_id")
        review_op = await asyncio.to_thread(
            self.git_sync.create_ai_operation,
            workpad_id,
            "reviewing",
            "pending",
            "Review last patch",
        )
        await asyncio.to_thread(
            self.git_sync.state_manager.update_ai_operation,
            review_op["operation_id"],
            status="reviewing",
        )

        try:
            review_response = await asyncio.to_thread(
                self.ai_orchestrator.review_patch,
                self._last_patch,
            )
            panel.append_line(f"Approved: {'yes' if review_response.approved else 'no'}")
            if review_response.issues:
                panel.append_line("Issues:")
                for issue in review_response.issues:
                    panel.append_line(f"  - {issue}")
            if review_response.suggestions:
                panel.append_line("Suggestions:")
                for suggestion in review_response.suggestions:
                    panel.append_line(f"  - {suggestion}")
            panel.finish_session("[green]Review completed[/]")

            await asyncio.to_thread(
                self.git_sync.state_manager.update_ai_operation,
                review_op["operation_id"],
                status="completed",
                response="\n".join(review_response.issues + review_response.suggestions),
                cost_usd=review_response.cost_usd,
                model=review_response.model_used,
            )
            self.notify("AI review finished", severity="information")
        except Exception as exc:
            panel.append_line(f"[red]AI review failed: {exc}[/]")
            await asyncio.to_thread(
                self.git_sync.state_manager.update_ai_operation,
                review_op["operation_id"],
                status="failed",
                error=str(exc),
            )
            self.notify(f"AI review failed: {exc}", severity="error")
        finally:
            self.refresh_all()

    def _gather_repo_context(self, repo_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if not repo_id:
            return None
        repo = self.git_sync.get_repo(repo_id)
        if not repo:
            return None
        repo_path = Path(repo["path"])
        files: List[str] = []
        for path in repo_path.rglob("*"):
            if path.is_file():
                files.append(str(path.relative_to(repo_path)))
            if len(files) >= 50:
                break
        return {"file_tree": files, "repo_name": repo.get("name")}

    def _collect_file_context(self, plan, repo_id: Optional[str]) -> Dict[str, str]:
        contents: Dict[str, str] = {}
        if not plan or not repo_id:
            return contents
        repo = self.git_sync.get_repo(repo_id)
        if not repo:
            return contents
        repo_path = Path(repo["path"])
        for change in getattr(plan, "file_changes", []):
            path = getattr(change, "path", None) or change.get("path")
            action = getattr(change, "action", None) or change.get("action")
            if action != "modify" or not path:
                continue
            file_path = repo_path / path
            if file_path.exists() and file_path.is_file():
                try:
                    contents[path] = file_path.read_text()[:4000]
                except Exception as exc:
                    logger.debug("Failed to read %s: %s", path, exc)
        return contents


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
