"""
Real-time Test Runner for Heaven Interface.

Executes tests with live output streaming and result visualization.
"""

import asyncio
import subprocess
import re
from pathlib import Path
from typing import Optional, List, Dict, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from textual.widgets import Static, ProgressBar, Label
from textual.containers import Container, Vertical
from textual.reactive import reactive
from textual import events, work
from rich.text import Text
from rich.console import Console
from rich.syntax import Syntax

from sologit.utils.logger import get_logger

logger = get_logger(__name__)


class TestStatus(Enum):
    """Test execution status."""
    IDLE = "idle"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class TestResult:
    """Test execution result."""
    status: TestStatus
    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    duration: float = 0.0
    output: str = ""
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total == 0:
            return 0.0
        return (self.passed / self.total) * 100


class TestOutputWidget(Static):
    """Widget for displaying live test output."""
    
    CSS = """
    TestOutputWidget {
        width: 100%;
        height: 100%;
        border: solid $primary;
        padding: 1;
        overflow-y: scroll;
        background: $surface;
    }
    
    .test-header {
        color: $primary;
        text-style: bold;
        padding: 1;
        background: $panel;
    }
    
    .test-pass {
        color: $success;
    }
    
    .test-fail {
        color: $error;
    }
    
    .test-skip {
        color: $warning;
    }
    
    .test-running {
        color: $accent;
    }
    """
    
    output_lines: reactive[List[str]] = reactive(list, init=False)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._output_buffer = []
        self.auto_scroll = True
    
    def render(self) -> Text:
        """Render test output."""
        if not self._output_buffer:
            return Text("No test output yet. Run tests to see results.", style="dim")
        
        text = Text()
        for line in self._output_buffer[-500:]:  # Keep last 500 lines
            text.append(self._colorize_line(line))
            text.append("\n")
        
        return text
    
    def _colorize_line(self, line: str) -> Text:
        """Colorize test output line based on content."""
        text = Text()
        
        # Test result patterns
        if re.search(r'PASSED|✓|✔', line, re.IGNORECASE):
            text.append(line, style="green")
        elif re.search(r'FAILED|✗|✘', line, re.IGNORECASE):
            text.append(line, style="red bold")
        elif re.search(r'ERROR|EXCEPTION', line, re.IGNORECASE):
            text.append(line, style="red bold")
        elif re.search(r'SKIPPED|SKIP', line, re.IGNORECASE):
            text.append(line, style="yellow")
        elif re.search(r'RUNNING|\.\.\.', line, re.IGNORECASE):
            text.append(line, style="cyan")
        elif line.startswith('==='):
            text.append(line, style="bold magenta")
        elif line.startswith('---'):
            text.append(line, style="bold blue")
        elif line.startswith('>'):
            text.append(line, style="yellow")
        elif re.search(r'File ".*", line \d+', line):
            text.append(line, style="cyan underline")
        else:
            text.append(line, style="white")
        
        return text
    
    def append_output(self, line: str) -> None:
        """Append a line to the output."""
        self._output_buffer.append(line.rstrip())
        self.refresh()
        
        if self.auto_scroll:
            self.scroll_end(animate=False)
    
    def clear_output(self) -> None:
        """Clear all output."""
        self._output_buffer.clear()
        self.refresh()
    
    def toggle_auto_scroll(self) -> None:
        """Toggle auto-scroll."""
        self.auto_scroll = not self.auto_scroll


class TestSummaryWidget(Static):
    """Widget displaying test execution summary."""
    
    CSS = """
    TestSummaryWidget {
        width: 100%;
        height: auto;
        border: solid $primary;
        padding: 1;
        background: $panel;
    }
    
    .summary-stat {
        padding: 0 1;
    }
    """
    
    result: reactive[Optional[TestResult]] = reactive(None)
    
    def render(self) -> Text:
        """Render test summary."""
        if not self.result:
            return Text("No test results yet", style="dim")
        
        text = Text()
        
        # Status indicator
        status_styles = {
            TestStatus.PASSED: ("✓ PASSED", "green bold"),
            TestStatus.FAILED: ("✗ FAILED", "red bold"),
            TestStatus.ERROR: ("⚠ ERROR", "red bold"),
            TestStatus.RUNNING: ("⟳ RUNNING", "cyan bold"),
            TestStatus.IDLE: ("○ IDLE", "dim"),
            TestStatus.CANCELLED: ("✗ CANCELLED", "yellow"),
        }
        
        status_text, status_style = status_styles.get(
            self.result.status,
            ("?", "white")
        )
        
        text.append(status_text, style=status_style)
        text.append(" | ")
        
        # Test counts
        text.append(f"Total: {self.result.total}", style="white")
        text.append(" | ")
        text.append(f"Passed: {self.result.passed}", style="green")
        text.append(" | ")
        text.append(f"Failed: {self.result.failed}", style="red")
        
        if self.result.errors > 0:
            text.append(" | ")
            text.append(f"Errors: {self.result.errors}", style="red bold")
        
        if self.result.skipped > 0:
            text.append(" | ")
            text.append(f"Skipped: {self.result.skipped}", style="yellow")
        
        # Duration and success rate
        text.append(" | ")
        text.append(f"Duration: {self.result.duration:.2f}s", style="cyan")
        text.append(" | ")
        text.append(f"Success: {self.result.success_rate:.1f}%", style="green")
        
        return text
    
    def update_result(self, result: TestResult) -> None:
        """Update the test result."""
        self.result = result
        self.refresh()


class TestRunner:
    """
    Test runner that executes pytest and streams output.
    """
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.process: Optional[subprocess.Popen] = None
        self.is_running = False
    
    async def run_tests(
        self,
        target: str = "fast",
        output_callback: Optional[Callable[[str], None]] = None,
        result_callback: Optional[Callable[[TestResult], None]] = None
    ) -> TestResult:
        """
        Run tests asynchronously with output streaming.
        
        Args:
            target: Test target ('fast' or 'full')
            output_callback: Callback for each output line
            result_callback: Callback for result updates
            
        Returns:
            TestResult with execution details
        """
        self.is_running = True
        result = TestResult(status=TestStatus.RUNNING)
        
        if result_callback:
            result_callback(result)
        
        try:
            # Determine test command
            if target == "fast":
                cmd = ["pytest", "-v", "--tb=short", "-x"]
            else:
                cmd = ["pytest", "-v", "--tb=long", "--cov=sologit"]
            
            # Start the process
            logger.info(f"Starting test execution: {' '.join(cmd)}")
            
            start_time = datetime.now()
            
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(self.repo_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env={**subprocess.os.environ, "PYTEST_CURRENT_TEST": ""}
            )
            
            output_lines = []
            
            # Stream output
            async for line in self.process.stdout:
                if not self.is_running:
                    break
                
                line_str = line.decode('utf-8', errors='replace').rstrip()
                output_lines.append(line_str)
                
                if output_callback:
                    output_callback(line_str)
                
                # Parse test results from output
                self._parse_test_line(line_str, result)
                
                if result_callback:
                    result_callback(result)
            
            # Wait for completion
            await self.process.wait()
            
            end_time = datetime.now()
            result.duration = (end_time - start_time).total_seconds()
            result.output = '\n'.join(output_lines)
            
            # Determine final status
            if not self.is_running:
                result.status = TestStatus.CANCELLED
            elif result.failed > 0 or result.errors > 0:
                result.status = TestStatus.FAILED
            elif result.total > 0:
                result.status = TestStatus.PASSED
            else:
                result.status = TestStatus.ERROR
            
            if result_callback:
                result_callback(result)
            
            logger.info(f"Test execution completed: {result.status.value}")
            
        except Exception as e:
            logger.error(f"Test execution failed: {e}", exc_info=True)
            result.status = TestStatus.ERROR
            result.output += f"\n\nError: {str(e)}"
            
            if output_callback:
                output_callback(f"ERROR: {str(e)}")
            
            if result_callback:
                result_callback(result)
        
        finally:
            self.is_running = False
            self.process = None
        
        return result
    
    def _parse_test_line(self, line: str, result: TestResult) -> None:
        """Parse a test output line and update result."""
        # Parse pytest output patterns
        
        # Test result line: test_name.py::TestClass::test_method PASSED/FAILED
        if ' PASSED' in line:
            result.passed += 1
            result.total = result.passed + result.failed + result.errors + result.skipped
        elif ' FAILED' in line:
            result.failed += 1
            result.total = result.passed + result.failed + result.errors + result.skipped
        elif ' ERROR' in line:
            result.errors += 1
            result.total = result.passed + result.failed + result.errors + result.skipped
        elif ' SKIPPED' in line:
            result.skipped += 1
            result.total = result.passed + result.failed + result.errors + result.skipped
        
        # Summary line: "5 passed, 2 failed in 1.23s"
        summary_match = re.search(
            r'(\d+)\s+passed(?:,\s+(\d+)\s+failed)?(?:,\s+(\d+)\s+error)?(?:,\s+(\d+)\s+skipped)?\s+in\s+([\d.]+)s',
            line
        )
        if summary_match:
            result.passed = int(summary_match.group(1))
            result.failed = int(summary_match.group(2) or 0)
            result.errors = int(summary_match.group(3) or 0)
            result.skipped = int(summary_match.group(4) or 0)
            result.duration = float(summary_match.group(5))
            result.total = result.passed + result.failed + result.errors + result.skipped
    
    def cancel(self) -> None:
        """Cancel running tests."""
        self.is_running = False
        if self.process:
            try:
                self.process.terminate()
            except Exception as e:
                logger.warning(f"Failed to terminate test process: {e}")


class TestRunnerWidget(Container):
    """Complete test runner widget with output and summary."""
    
    def __init__(self, repo_path: str, **kwargs):
        super().__init__(**kwargs)
        self.repo_path = repo_path
        self.runner = TestRunner(repo_path)
        self.current_result: Optional[TestResult] = None
    
    def compose(self):
        """Compose the widget."""
        yield TestSummaryWidget(id="test-summary")
        yield TestOutputWidget(id="test-output")
    
    @work
    async def run_tests(self, target: str = "fast") -> None:
        """Run tests asynchronously."""
        output_widget = self.query_one("#test-output", TestOutputWidget)
        summary_widget = self.query_one("#test-summary", TestSummaryWidget)
        
        output_widget.clear_output()
        
        def output_callback(line: str):
            output_widget.append_output(line)
        
        def result_callback(result: TestResult):
            summary_widget.update_result(result)
            self.current_result = result
        
        result = await self.runner.run_tests(
            target=target,
            output_callback=output_callback,
            result_callback=result_callback
        )
        
        # Emit completion event
        self.post_message(TestsCompleted(result))
    
    def cancel_tests(self) -> None:
        """Cancel running tests."""
        self.runner.cancel()
    
    def clear_output(self) -> None:
        """Clear test output."""
        output_widget = self.query_one("#test-output", TestOutputWidget)
        output_widget.clear_output()


class TestsCompleted(events.Message):
    """Message emitted when tests complete."""
    
    def __init__(self, result: TestResult):
        super().__init__()
        self.result = result
