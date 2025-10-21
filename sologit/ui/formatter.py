
"""
Rich formatter for Heaven Interface.

Provides formatted output using the Rich library with Heaven Interface design system.
"""

from typing import Optional, Dict, Any, List, Sequence
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.syntax import Syntax
from rich.tree import Tree
from rich.live import Live
from rich import box
from datetime import datetime

from sologit.ui.theme import theme


class RichFormatter:
    """Formatter for Rich library output with Heaven Interface styling."""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.theme_obj = theme
    
    def print(self, text: str, style: Optional[str] = None) -> None:
        """Print text with optional style."""
        self.console.print(text, style=style)
    
    def set_console(self, console: Console) -> None:
        """Update the underlying console instance."""
        self.console = console

    def print_header(self, text: str) -> None:
        """Print a header."""
        self.console.print(f"\n[bold {theme.colors.blue}]{text}[/bold {theme.colors.blue}]")

    def print_subheader(self, text: str) -> None:
        """Print a smaller subheader."""
        self.console.print(f"[{theme.colors.text_secondary}]{text}[/{theme.colors.text_secondary}]")
    
    def print_success(self, text: str) -> None:
        """Print success message."""
        icon = theme.icons.success
        self.console.print(f"[{theme.colors.success}]{icon}[/{theme.colors.success}] {text}")
    
    def print_error(self, text: str) -> None:
        """Print error message."""
        icon = theme.icons.error
        self.console.print(f"[{theme.colors.error}]{icon}[/{theme.colors.error}] {text}")
    
    def print_warning(self, text: str) -> None:
        """Print warning message."""
        icon = theme.icons.warning
        self.console.print(f"[{theme.colors.warning}]{icon}[/{theme.colors.warning}] {text}")
    
    def print_info(self, text: str) -> None:
        """Print info message."""
        icon = theme.icons.info
        self.console.print(f"[{theme.colors.info}]{icon}[/{theme.colors.info}] {text}")
    
    def panel(self, content: str, title: Optional[str] = None, 
              border_color: Optional[str] = None) -> Panel:
        """Create a panel with Heaven Interface styling."""
        return Panel(
            content,
            title=title,
            border_style=border_color or theme.colors.blue,
            box=box.ROUNDED,
            padding=(1, 2)
        )
    
    def print_panel(self, content: str, title: Optional[str] = None,
                   border_color: Optional[str] = None) -> None:
        """Print a panel."""
        self.console.print(self.panel(content, title, border_color))

    def print_error_panel(self, content: str, title: str = "Error") -> None:
        """Print an error panel with red border."""
        icon = theme.icons.error
        self.print_panel(content, title=f"{icon} {title}", border_color=theme.colors.error)

    def print_success_panel(self, content: str, title: str = "Success") -> None:
        """Print a success panel with green border."""
        icon = theme.icons.success
        self.print_panel(content, title=f"{icon} {title}", border_color=theme.colors.success)

    def print_info_panel(self, content: str, title: str = "Info") -> None:
        """Print an informational panel with blue border."""
        icon = theme.icons.info
        self.print_panel(content, title=f"{icon} {title}", border_color=theme.colors.blue)

    def print_bullet_list(self, items: Sequence[str], icon: str = "•", style: Optional[str] = None) -> None:
        """Print a bullet list."""
        for item in items:
            bullet = f"[{style}]{icon}[/{style}]" if style else icon
            self.console.print(f"  {bullet} {item}")
    
    def table(self, title: Optional[str] = None, headers: Optional[List[str]] = None) -> Table:
        """Create a table with Heaven Interface styling."""
        table = Table(
            title=title,
            box=box.SIMPLE,
            border_style=theme.colors.text_secondary,
            header_style=f"bold {theme.colors.blue}",
            show_header=headers is not None,
            padding=(0, 1)
        )
        
        if headers:
            for header in headers:
                table.add_column(header)

        return table

    def syntax_highlight(self, code: str, language: str = "python") -> Syntax:
        """Create syntax-highlighted code block."""
        return Syntax(
            code,
            language,
            theme="monokai",
            line_numbers=True,
            background_color=theme.colors.surface,
        )

    def print_code(self, code: str, language: str = "python") -> None:
        """Print syntax-highlighted code."""
        self.console.print(self.syntax_highlight(code, language))
    
    def create_progress(self) -> Progress:
        """Create a progress bar with Heaven Interface styling."""
        return Progress(
            SpinnerColumn(spinner_name="dots", style=theme.colors.blue),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(complete_style=theme.colors.success, finished_style=theme.colors.success),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=self.console,
        )

    def progress(self, description: str) -> "ProgressContext":
        """Create a managed progress context with an initial indeterminate task."""
        return ProgressContext(self.create_progress(), description)


class ProgressContext:
    """Context manager that manages an indeterminate task for scoped progress."""

    def __init__(self, progress: Progress, description: str):
        self._progress = progress
        self._description = description
        self._task_id: Optional[int] = None

    def __enter__(self) -> Progress:
        progress = self._progress.__enter__()
        self._task_id = progress.add_task(self._description, total=None)
        return progress

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._task_id is not None:
            self._progress.remove_task(self._task_id)
        self._progress.__exit__(exc_type, exc_val, exc_tb)
    
    def tree(self, label: str) -> Tree:
        """Create a tree structure."""
        return Tree(
            f"[{theme.colors.blue}]{label}[/{theme.colors.blue}]",
            guide_style=theme.colors.text_secondary
        )
    
    def format_timestamp(self, timestamp: str) -> str:
        """Format timestamp for display."""
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return timestamp
    
    def format_duration(self, ms: int) -> str:
        """Format duration in milliseconds for display."""
        if ms < 1000:
            return f"{ms}ms"
        elif ms < 60000:
            return f"{ms/1000:.1f}s"
        else:
            mins = ms // 60000
            secs = (ms % 60000) / 1000
            return f"{mins}m {secs:.1f}s"
    
    def print_workpad_summary(self, workpad: Dict[str, Any]) -> None:
        """Print a workpad summary."""
        status = workpad.get('status', 'unknown')
        color = theme.get_status_color(status)
        icon = theme.get_status_icon(status)
        
        content = f"""[bold]Workpad:[/bold] {workpad.get('workpad_id', 'N/A')}
[bold]Title:[/bold] {workpad.get('title', 'N/A')}
[bold]Status:[/bold] [{color}]{icon} {status.upper()}[/{color}]
[bold]Branch:[/bold] {workpad.get('branch_name', 'N/A')}
[bold]Base Commit:[/bold] {workpad.get('base_commit', 'N/A')[:8]}
[bold]Patches Applied:[/bold] {workpad.get('patches_applied', 0)}
[bold]Test Runs:[/bold] {len(workpad.get('test_runs', []))}
[bold]Created:[/bold] {self.format_timestamp(workpad.get('created_at', ''))}"""
        
        self.print_panel(content, title=f"Workpad: {workpad.get('title', 'N/A')}", border_color=color)
    
    def print_test_summary(self, test_run: Dict[str, Any]) -> None:
        """Print a test run summary."""
        status = test_run.get('status', 'unknown')
        color = theme.get_status_color(status)
        icon = theme.get_status_icon(status)
        
        total = test_run.get('total_tests', 0)
        passed = test_run.get('passed', 0)
        failed = test_run.get('failed', 0)
        skipped = test_run.get('skipped', 0)
        duration = test_run.get('duration_ms', 0)
        
        content = f"""[bold]Status:[/bold] [{color}]{icon} {status.upper()}[/{color}]
[bold]Target:[/bold] {test_run.get('target', 'N/A')}
[bold]Total Tests:[/bold] {total}
[bold]Passed:[/bold] [{theme.colors.success}]{passed}[/{theme.colors.success}]
[bold]Failed:[/bold] [{theme.colors.error}]{failed}[/{theme.colors.error}]
[bold]Skipped:[/bold] [{theme.colors.warning}]{skipped}[/{theme.colors.warning}]
[bold]Duration:[/bold] {self.format_duration(duration)}
[bold]Started:[/bold] {self.format_timestamp(test_run.get('started_at', ''))}"""
        
        self.print_panel(content, title="Test Run Summary", border_color=color)
    
    def print_ai_operation_summary(self, operation: Dict[str, Any]) -> None:
        """Print an AI operation summary."""
        status = operation.get('status', 'unknown')
        color = theme.get_status_color(status)
        icon = theme.get_status_icon(status)
        
        content = f"""[bold]Operation:[/bold] {operation.get('operation_type', 'N/A')}
[bold]Status:[/bold] [{color}]{icon} {status.upper()}[/{color}]
[bold]Model:[/bold] {operation.get('model', 'N/A')}
[bold]Cost:[/bold] ${operation.get('cost_usd', 0):.4f}
[bold]Tokens:[/bold] {operation.get('tokens_used', 0):,}
[bold]Started:[/bold] {self.format_timestamp(operation.get('started_at', ''))}"""
        
        if operation.get('completed_at'):
            content += f"\n[bold]Completed:[/bold] {self.format_timestamp(operation['completed_at'])}"
        
        self.print_panel(content, title="AI Operation", border_color=color)


# Global formatter instance
formatter = RichFormatter()
