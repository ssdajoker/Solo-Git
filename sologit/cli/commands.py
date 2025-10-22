"""Command implementations for the Solo Git CLI."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, NoReturn, Optional, Sequence

import click
from rich.console import Console

from sologit.core.repository import Repository
from sologit.core.workpad import Workpad
from sologit.engines.git_engine import GitEngine, GitEngineError
from sologit.engines.patch_engine import PatchEngine
from sologit.engines.test_orchestrator import (
    TestConfig,
    TestOrchestrator,
    TestResult,
    TestStatus,
)
from sologit.state.git_sync import GitStateSync
from sologit.state.manager import StateManager
from sologit.state.schema import TestResult as StateTestResult
from sologit.ui.formatter import RichFormatter
from sologit.ui.theme import theme
from sologit.utils.logger import get_logger
from sologit.workflows.ci_orchestrator import CIOrchestrator
from sologit.workflows.rollback_handler import RollbackHandler

logger = get_logger(__name__)

formatter = RichFormatter()


def set_formatter_console(console: Console) -> None:
    """Allow the CLI to reuse an externally managed Rich console."""

    formatter.set_console(console)


def abort_with_error(
    message: str,
    details: Optional[str] = None,
    *,
    title: Optional[str] = None,
    help_text: Optional[str] = None,
    tip: Optional[str] = None,
    suggestions: Optional[Iterable[str]] = None,
    docs_url: Optional[str] = None,
) -> NoReturn:
    """Render a contextual error panel and abort the active command."""

    formatter.print_error(
        title or "Command Error",
        message,
        help_text=help_text,
        tip=tip,
        suggestions=suggestions,
        docs_url=docs_url,
        details=details,
    )
    raise click.Abort()


_git_engine: Optional[GitEngine] = None
_patch_engine: Optional[PatchEngine] = None
_test_orchestrator: Optional[TestOrchestrator] = None
_git_state_sync: Optional[GitStateSync] = None
_ci_orchestrator: Optional[CIOrchestrator] = None
_rollback_handler: Optional[RollbackHandler] = None


def get_git_engine() -> GitEngine:
    """Return the singleton GitEngine instance."""

    global _git_engine
    if _git_engine is None:
        _git_engine = GitEngine()
    return _git_engine


def get_patch_engine() -> PatchEngine:
    """Return the singleton PatchEngine instance."""

    global _patch_engine
    if _patch_engine is None:
        _patch_engine = PatchEngine(get_git_engine())
    return _patch_engine


def get_test_orchestrator() -> TestOrchestrator:
    """Return the singleton TestOrchestrator instance."""

    global _test_orchestrator
    if _test_orchestrator is None:
        _test_orchestrator = TestOrchestrator(get_git_engine(), formatter=formatter)
        config = get_config_manager().config.tests
        log_dir = Path(config.log_dir).expanduser() if config.log_dir else None
        _test_orchestrator = TestOrchestrator(
            get_git_engine(),
            log_dir=log_dir,
            formatter=formatter,
        )
    return _test_orchestrator


def get_git_sync() -> GitStateSync:
    """Return the singleton GitStateSync instance."""

    global _git_state_sync
    if _git_state_sync is None:
        _git_state_sync = GitStateSync()
    return _git_state_sync


def get_ci_orchestrator() -> CIOrchestrator:
    """Return the singleton CI orchestrator."""

    global _ci_orchestrator
    if _ci_orchestrator is None:
        _ci_orchestrator = CIOrchestrator(get_git_engine(), formatter=formatter)
    return _ci_orchestrator


def get_rollback_handler() -> RollbackHandler:
    """Return the singleton rollback handler."""

    global _rollback_handler
    if _rollback_handler is None:
        _rollback_handler = RollbackHandler(get_git_engine(), formatter=formatter)
    return _rollback_handler


def _require_repository(repo: Optional[Repository], repo_id: str) -> Repository:
    """Ensure a repository is available and raise a helpful error otherwise."""

    if repo is None:
        abort_with_error(f"Repository {repo_id} not found")
    return repo


def _require_workpad(workpad: Optional[Workpad], pad_id: str) -> Workpad:
    """Ensure a workpad is available and raise a helpful error otherwise."""

    if workpad is None:
        abort_with_error(f"Workpad {pad_id} not found")
    return workpad


@click.group()
def repo() -> None:
    """Repository management commands."""


@repo.command("init")
@click.option("--zip", "zip_file", type=click.Path(exists=True, path_type=Path), help="Initialize from zip file")
@click.option("--git", "git_url", type=str, help="Initialize from Git URL")
@click.option("--name", type=str, help="Repository name (optional)")
def repo_init(zip_file: Optional[Path], git_url: Optional[str], name: Optional[str]) -> None:
    """Initialize a repository from a zip archive or a Git URL."""

    formatter.print_header("Repository Initialization")

    selected_sources = [bool(zip_file), bool(git_url)]
    if sum(selected_sources) == 0:
        abort_with_error(
            "Missing Repository Source",
            "Provide either --zip <path> or --git <url> so Solo Git knows where to initialize from.",
            title="Repository Initialization Blocked",
            help_text="Choose exactly one source option. Use --zip for local archives or --git for remote repositories.",
            tip="If you already cloned locally, package it as a zip and pass --zip to speed up initialization.",
            suggestions=[
                "evogitctl repo init --zip app.zip",
                "evogitctl repo init --git https://github.com/org/project.git",
            ],
            docs_url="docs/SETUP.md#initialize-a-repository",
        )

    if all(selected_sources):
@repo.command('init')
@click.option('--zip', 'zip_file', type=click.Path(exists=True), help='Initialize from zip file')
@click.option('--git', 'git_url', type=str, help='Initialize from Git URL')
@click.option('--empty', is_flag=True, help='Initialize an empty repository managed by Solo Git')
@click.option('--path', 'target_path', type=click.Path(path_type=Path), help='Directory for empty repository (defaults to Solo Git data dir)')
@click.option('--name', type=str, help='Repository name (optional)')
def repo_init(zip_file: Optional[str], git_url: Optional[str], empty: bool, target_path: Optional[Path], name: Optional[str]):
    """Initialize a new repository from zip file, Git URL, or empty."""
    formatter.print_header("Repository Initialization")

    sources = {
        'zip': zip_file,
        'git': git_url,
        'empty': empty
    }

    provided_sources = [name for name, value in sources.items() if value]

    if len(provided_sources) != 1:
        abort_with_error(
            "Invalid Source Specification",
            f"Please specify exactly one of --zip, --git, or --empty. Provided: {', '.join(provided_sources) or 'None'}",
            title="Repository Initialization Blocked",
            help_text="Choose one initialization method.",
            suggestions=[
                "evogitctl repo init --zip app.zip",
                "evogitctl repo init --git https://github.com/user/repo.git",
                "evogitctl repo init --empty --path ./new-repo",
            ]
        )

    git_engine = get_git_engine()

    try:
        repo_info = None
        if zip_file is not None:
            repo_name = name or zip_file.stem
            formatter.print_info(f"Initializing repository from zip: {zip_file.name}")
            repo_id = git_engine.init_from_zip(zip_file.read_bytes(), repo_name)
        if empty:
            repo_name = name or (target_path.name if target_path else "solo-git-repo")
            formatter.print_info(f"Creating empty repository: {repo_name}")
            repo_info = git_sync.create_empty_repo(repo_name, str(target_path) if target_path else None)
        elif zip_file:
            zip_path = Path(zip_file)
            repo_name = name or zip_path.stem
            formatter.print_info(f"Initializing from zip: {zip_path.name}")
            repo_info = git_sync.init_repo_from_zip(zip_path.read_bytes(), repo_name)
        elif git_url:
            repo_name = name or Path(git_url).stem.replace('.git', '')
            formatter.print_info(f"Cloning from: {git_url}")
            repo_info = git_sync.init_repo_from_git(git_url, repo_name)
        else:
            assert git_url is not None
            repo_name = name or Path(git_url.rstrip("/")).stem
            formatter.print_info(f"Cloning repository from: {git_url}")
            repo_id = git_engine.init_from_git(git_url, repo_name)

        repo_obj = _require_repository(git_engine.get_repo(repo_id), repo_id)

        formatter.print_success("Repository initialized!")
        formatter.print_info(f"Repo ID: {repo_obj.id}")
        formatter.print_info(f"Name: {repo_obj.name}")
        formatter.print_info(f"Path: {repo_obj.path}")
        formatter.print_info(f"Trunk: {getattr(repo_obj, 'trunk_branch', 'main')}")

        summary = formatter.table(headers=["Field", "Value"])
        summary.add_row("ID", f"[cyan]{repo_obj.id}[/cyan]")
        summary.add_row("Name", f"[bold]{repo_obj.name}[/bold]")
        summary.add_row("Path", str(repo_obj.path))
        summary.add_row("Trunk", f"[cyan]{getattr(repo_obj, 'trunk_branch', 'main')}[/cyan]")
        formatter.console.print(summary)

    except GitEngineError as exc:
        abort_with_error(
            "Repository initialization failed",
            str(exc),
            title="Repository Initialization Blocked",
            help_text="Confirm the source path or URL is reachable and that your credentials allow cloning the repository.",
            tip="If cloning from a private remote, ensure your SSH keys or HTTPS tokens are configured locally.",
            suggestions=[
                "Retry the command with --verbose",
                "Check git remote access manually",
            ],
            docs_url="docs/SETUP.md#initialize-a-repository",
        )


@repo.command("list")
def repo_list() -> None:
    """List registered repositories."""

    git_engine = get_git_engine()
    repos = git_engine.list_repos()

    if not repos:
        formatter.print_info("No repositories found.")
        formatter.print("\n💡 Create a repository with: evogitctl repo init --zip app.zip")
        return

    formatter.print_header(f"Repositories ({len(repos)})")
    table = formatter.table(headers=["ID", "Name", "Trunk", "Workpads", "Created"])

    for repo_obj in repos:
        created = repo_obj.created_at
        if isinstance(created, datetime):
            created_str = created.strftime("%Y-%m-%d %H:%M")
        else:
            created_str = str(created)

        table.add_row(
            f"[cyan]{repo_obj.id}[/cyan]",
            f"[bold]{getattr(repo_obj, 'name', repo_obj.id)}[/bold]",
            getattr(repo_obj, 'trunk_branch', 'main'),
            str(getattr(repo_obj, 'workpad_count', 0)),
            created_str,
        )

    formatter.console.print(table)


@repo.command("delete")
@click.argument("repo_id")
@click.option("--keep-files", is_flag=True, help="Retain repository directory on disk")
def repo_delete(repo_id: str, keep_files: bool) -> None:
    """Delete a repository and optionally keep its working directory."""

    git_sync = get_git_sync()

    try:
        repo = git_sync.git_engine.get_repo(repo_id)
        if not repo:
            abort_with_error(f"Repository {repo_id} not found")

        formatter.print_info(f"Deleting repository {repo.name} ({repo_id})")
        git_sync.delete_repository(repo_id, remove_files=not keep_files)
        formatter.print_success("Repository deleted")
        if keep_files:
            formatter.print_info("Repository files retained on disk")
        formatter.console.print()
    except GitEngineError as exc:
        abort_with_error(str(exc), "Failed to delete repository")


@repo.command("info")
@click.argument("repo_id")
def repo_info(repo_id: str) -> None:
    """Display repository metadata."""

    git_engine = get_git_engine()
    repo_obj = git_engine.get_repo(repo_id)

    if not repo_obj:
        available = [f"{r.id} • {getattr(r, 'name', r.id)}" for r in git_engine.list_repos()]
        abort_with_error(
            f"Repository '{repo_id}' is not registered with Solo Git.",
            title="Repository Not Found",
            help_text="Select one of the available repository IDs or initialize a new repository before retrying.",
            tip="Run 'evogitctl repo list' to review active repositories before invoking repo info.",
            suggestions=["evogitctl repo list"] + available[:5],
            docs_url="docs/SETUP.md#initialize-a-repository",
        )

    formatter.print_panel(
        "\n".join(
            [
                f"[bold cyan]Repository:[/bold cyan] {repo_obj.id}",
                f"[bold]Name:[/bold] {repo_obj.name}",
                f"[bold]Path:[/bold] {repo_obj.path}",
                f"[bold]Trunk:[/bold] {repo_obj.trunk_branch}",
                f"[bold]Created:[/bold] {repo_obj.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
                f"[bold]Workpads:[/bold] {repo_obj.workpad_count} active",
                f"[bold]Source:[/bold] {getattr(repo_obj, 'source_type', 'unknown')}",
            ]
        ),
        title=f"📦 Repository: {repo_obj.name}",
    )

    if getattr(repo_obj, "source_url", None):
        formatter.print_info(f"Source URL: {repo_obj.source_url}")


@click.group()
def pad() -> None:
    """Workpad management commands."""


@pad.command("create")
@click.argument("title")
@click.option("--repo", "repo_id", type=str, help="Repository ID (required if multiple repos)")
def pad_create(title: str, repo_id: Optional[str]) -> None:
    """Create a new workpad."""

    git_engine = get_git_engine()

    formatter.print_header("Workpad Creation")

    if not repo_id:
        repos = git_engine.list_repos()
        if len(repos) == 0:
            abort_with_error(
                "No repositories found",
                "Initialize a repository first: evogitctl repo init --zip app.zip",
            )
        if len(repos) == 1:
            repo_id = repos[0].id
            formatter.print_info(f"Using repository: {repos[0].name} ({repo_id})")
        else:
            formatter.print_warning("Multiple repositories found. Use --repo to specify an ID.")
            table = formatter.table(headers=["ID", "Name"])
            for repo_obj in repos:
                table.add_row(f"[cyan]{repo_obj.id}[/cyan]", getattr(repo_obj, "name", repo_obj.id))
            formatter.print_panel(
                "Multiple repositories found. Please rerun with --repo <ID>.",
                title="Repository Selection Required",
            )
            formatter.console.print(table)
            raise click.Abort()

    try:
        assert repo_id is not None
        formatter.print_info(f"Creating workpad: {title}")
        pad_id = git_engine.create_workpad(repo_id, title)
        workpad = _require_workpad(git_engine.get_workpad(pad_id), pad_id)

        formatter.print_success("Workpad created!")
        formatter.print_info(f"Pad ID: {workpad.id}")
        formatter.print_info(f"Title: {workpad.title}")
        formatter.print_info(f"Branch: {workpad.branch_name}")
        formatter.print_info("Base: main")

        details = formatter.table(headers=["Field", "Value"])
        details.add_row("Pad ID", f"[cyan]{workpad.id}[/cyan]")
        details.add_row("Title", f"[bold]{workpad.title}[/bold]")
        details.add_row("Branch", workpad.branch_name)
        details.add_row("Base", "main")
        formatter.console.print(details)

    except GitEngineError as exc:
        abort_with_error("Failed to create workpad", str(exc))


@pad.command("list")
@click.option("--repo", "repo_id", type=str, help="Filter by repository ID")
def pad_list(repo_id: Optional[str]) -> None:
    """List workpads, optionally filtered by repository."""

    git_engine = get_git_engine()
    workpads = git_engine.list_workpads(repo_id)

    if not workpads:
        formatter.print_info("No workpads found.")
        formatter.print("\n💡 Create a workpad with: evogitctl pad create \"add feature\"")
        return

    title = f"Workpads ({len(workpads)})"
    if repo_id:
        title += f" for repo {repo_id}"

    formatter.print_header(title)
    table = formatter.table(headers=["ID", "Title", "Status", "Checkpoints", "Tests", "Created"])

    for pad_obj in workpads:
        status = getattr(pad_obj, "status", "unknown")
        status_color = theme.get_status_color(status)
        status_icon = theme.get_status_icon(status)
        status_display = f"[{status_color}]{status_icon} {pad_obj.status}[/{status_color}]"

        test_display = ""
        if getattr(pad_obj, "test_status", None):
            test_status = pad_obj.test_status
            if test_status == "passed":
                test_display = "✅ passed"
            elif test_status == "failed":
                test_display = "❌ failed"
            else:
                test_display = "⏳ pending"

        created = pad_obj.created_at
        if isinstance(created, datetime):
            created_str = created.strftime("%Y-%m-%d %H:%M")
        else:
            created_str = str(created)

        table.add_row(
            f"[cyan]{pad_obj.id[:8]}[/cyan]",
            f"[bold]{pad_obj.title}[/bold]",
            status_display,
            str(len(getattr(pad_obj, "checkpoints", []))),
            test_display or "-",
            created_str,
        )

    formatter.console.print(table)


@pad.command("info")
@click.argument("pad_id")
def pad_info(pad_id: str) -> None:
    """Show workpad information."""

    git_engine = get_git_engine()
    workpad = _require_workpad(git_engine.get_workpad(pad_id), pad_id)

    formatter.print_header(f"Workpad Details: {workpad.title}")
    formatter.print_info(f"Workpad: {workpad.id}")
    formatter.print_info(f"Title: {workpad.title}")
    formatter.print_info(f"Repo: {workpad.repo_id}")
    formatter.print_info(f"Branch: {workpad.branch_name}")
    formatter.print_info(f"Status: {workpad.status}")
    formatter.print_info(f"Checkpoints: {len(workpad.checkpoints)}")
    if getattr(workpad, "test_status", None):
        formatter.print_info(f"Last Test: {workpad.test_status}")

    status_color = theme.get_status_color(workpad.status)
    status_icon = theme.get_status_icon(workpad.status)
    panel_content = "\n".join(
        [
            f"[bold]Workpad ID:[/bold] [cyan]{workpad.id}[/cyan]",
            f"[bold]Repository:[/bold] {workpad.repo_id}",
            f"[bold]Branch:[/bold] {workpad.branch_name}",
            f"[bold]Status:[/bold] [{status_color}]{status_icon} {workpad.status.upper()}[/{status_color}]",
            f"[bold]Created:[/bold] {workpad.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"[bold]Checkpoints:[/bold] {len(workpad.checkpoints)}",
        ]
    )

    if getattr(workpad, "test_status", None):
        test_color = theme.get_status_color(workpad.test_status)
        test_icon = theme.get_status_icon(workpad.test_status)
        panel_content += f"\n[bold]Last Test:[/bold] [{test_color}]{test_icon} {workpad.test_status.upper()}[/{test_color}]"

    formatter.print_panel(panel_content, title="Workpad Summary")

    if workpad.checkpoints:
        formatter.print_subheader("Checkpoints")
        formatter.print_bullet_list(workpad.checkpoints, icon=theme.icons.commit, style=theme.colors.blue)


@pad.command("promote")
@click.argument("pad_id")
def pad_promote(pad_id: str) -> None:
    """Promote a workpad to trunk via a fast-forward merge."""

    git_engine = get_git_engine()
    workpad = git_engine.get_workpad(pad_id)
    if workpad is None:
        abort_with_error(f"Workpad {pad_id} not found")

    if not git_engine.can_promote(pad_id):
        abort_with_error(
            "Cannot promote: not fast-forward-able",
            "Trunk has diverged. Manual merge required before promotion.",
        )

    try:
        formatter.print_header("Workpad Promotion")
        formatter.print_info(f"Promoting workpad: {workpad.title}")
        commit_hash = git_engine.promote_workpad(pad_id)

        formatter.print_success("Workpad promoted to trunk!")
        formatter.print_info(f"Commit: {commit_hash}")
        formatter.print_info(f"Branch Removed: {workpad.branch_name}")
        formatter.print_info(f"Trunk Updated: main @ {commit_hash[:8]}")

        details = formatter.table(headers=["Field", "Value"])
        details.add_row("Commit", f"[green]{commit_hash}[/green]")
        details.add_row("Branch Removed", workpad.branch_name)
        details.add_row("Trunk Updated", f"main @ {commit_hash[:8]}")
        formatter.console.print(details)

    except GitEngineError as exc:
        abort_with_error("Promotion failed", str(exc))


@pad.command("diff")
@click.argument("pad_id")
def pad_diff(pad_id: str) -> None:
    """Display the diff between a workpad and trunk."""

    git_engine = get_git_engine()
    workpad = git_engine.get_workpad(pad_id)
    if workpad is None:
        abort_with_error(f"Workpad {pad_id} not found")

    try:
        diff = git_engine.get_diff(pad_id)
        if diff:
            formatter.print_header(f"Diff for {workpad.title}")
            formatter.print_code(diff, language="diff")
        else:
            formatter.print_info("No changes between workpad and trunk.")
    except GitEngineError as exc:
        abort_with_error("Failed to generate diff", str(exc))


@click.group()
def test() -> None:
    """Test execution commands."""


def _default_tests(target: str) -> Sequence[TestConfig]:
    """Return a default set of tests for the given target."""

    if target == "fast":
        return [TestConfig(name="unit-tests", cmd="python -m pytest tests/ -q", timeout=60)]

    return [
        TestConfig(name="unit-tests", cmd="python -m pytest tests/ -q", timeout=60),
        TestConfig(name="integration", cmd="python -m pytest tests/integration/ -q", timeout=120),
    ]


@test.command("run")
@click.argument("pad_id")
@click.option("--target", type=click.Choice(["fast", "full"]), default="fast", help="Test target")
@click.option("--parallel/--sequential", default=True, help="Parallel execution")
def test_run(pad_id: str, target: str, parallel: bool) -> None:
    """Run tests for a workpad with live output streaming."""

    git_engine = get_git_engine()
    test_orchestrator = get_test_orchestrator()
    state_manager = StateManager()

    workpad = git_engine.get_workpad(pad_id)
    if workpad is None:
        abort_with_error(f"Workpad {pad_id} not found")

    run_record = state_manager.create_test_run(pad_id, target)
    run_id = run_record.run_id
    state_manager.update_test_run(run_id, status="running")
    run_started_at = time.time()

    tests = list(_default_tests(target))

    info_panel = "\n".join(
        [
            f"[bold]Workpad:[/bold] {workpad.title}",
            f"[bold]Tests:[/bold] {len(tests)}",
            f"[bold]Execution:[/bold] {'Parallel' if parallel else 'Sequential'}",
            f"[bold]Mode:[/bold] {test_orchestrator.mode.value if hasattr(test_orchestrator, 'mode') else 'unknown'}",
            f"[bold]Target:[/bold] {target}",
        ]
    )
    formatter.print_panel(info_panel, title="🧪 Test Execution")

    try:
        info = f"""[bold]Workpad:[/bold] {workpad.title}
[bold]Tests:[/bold] {len(tests)}
[bold]Execution:[/bold] {'Parallel' if parallel else 'Sequential'}
[bold]Mode:[/bold] {test_orchestrator.mode}
[bold]Target:[/bold] {target}"""
        formatter.print_panel(info, title="🧪 Test Execution")

        with formatter.create_progress() as progress:
            task_id = progress.add_task(f"Running {target} tests...", total=len(tests))

            def on_output(test_name: str, stream: str, line: str) -> None:
                style = "cyan" if stream == "stdout" else "red"
                prefix = "stdout" if stream == "stdout" else "stderr"
                formatter.console.print(f"[{prefix}] {test_name}: {line}", style=style)

            def on_complete(_: TestResult) -> None:
                progress.advance(task_id)

            results: Sequence[TestResult] = asyncio.run(
                test_orchestrator.run_tests(
                    pad_id,
                    tests,
                    parallel=parallel,
                    on_output=on_output,
                    on_test_complete=on_complete,
                )
            )

        formatter.console.print()

        table = formatter.table(headers=["Test", "Status", "Duration", "Mode", "Notes", "Log"])
        state_results: List[StateTestResult] = []

        for index, result in enumerate(results):
            if result.status == TestStatus.PASSED:
                status_icon = "✅"
            elif result.status == TestStatus.SKIPPED:
                status_icon = "⏭️"
            elif result.status == TestStatus.TIMEOUT:
                status_icon = "⏱️"
            elif result.status == TestStatus.ERROR:
                status_icon = "⚠️"
            else:
                status_icon = "❌"

            status_text = f"{status_icon} {result.status.value}"
            duration_s = result.duration_ms / 1000
            notes_segments = [segment for segment in [result.error, result.stderr] if segment]
            notes = " ".join(segment.strip().replace("\n", " ") for segment in notes_segments)
            if len(notes) > 80:
                notes = notes[:77] + "..."
            log_display = result.log_path.name if result.log_path else "-"

            table.add_row(result.name, status_text, f"{duration_s:.2f}s", result.mode, notes, log_display)

            combined_output = "\n".join(
                segment
                for segment in [result.stdout or "", result.stderr or ""]
                if segment
            )

            state_results.append(
                StateTestResult(
                    test_id=f"{run_id}-{index}",
                    name=result.name,
                    status=result.status.value,
                    duration_ms=result.duration_ms,
                    output=combined_output,
                    error=result.error,
                )
            )

        formatter.console.print(table)

        summary = test_orchestrator.get_summary(results)
        formatter.print_header("Test Summary")

        passed = summary.get("passed", 0)
        failed = summary.get("failed", 0)
        skipped = summary.get("skipped", 0)
        total = summary.get("total", len(results))
        timeout = summary.get("timeout", 0)

        if failed == 0 and timeout == 0:
            formatter.print_success("All tests passed!")
            final_status = "passed"
        else:
            formatter.print_error(
                "Tests Require Attention",
                "Some tests failed or timed out.",
            )
            final_status = "failed"

        formatter.print_info(f"Passed: {passed}")
        formatter.print_info(f"Failed: {failed}")
        formatter.print_info(f"Skipped: {skipped}")
        formatter.print_info(f"Total: {total}")

        duration_ms = sum(result.duration_ms for result in results)

        state_manager.update_test_run(
            run_id,
            status=final_status,
            total_tests=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            duration_ms=duration_ms,
            tests=state_results,
        )

    except Exception as exc:  # pragma: no cover - defensive, but tested via mocks
        duration_ms = int((time.time() - run_started_at) * 1000)
        error_result = StateTestResult(
            test_id=f"{run_id}-error",
            name="test-run",
            status="error",
            duration_ms=duration_ms,
            output="",
            error=str(exc),
        )
        state_manager.update_test_run(
            run_id,
            status="failed",
            total_tests=1,
            passed=0,
            failed=1,
            skipped=0,
            duration_ms=duration_ms,
            tests=[error_result],
        )

        abort_with_error(
            "Test execution failed",
            f"Workpad: {pad_id}\n{exc}",
            title="Test Execution Failed",
            help_text="Retry the command once the underlying issue is resolved.",
            tip="Run with --sequential to simplify orchestration when debugging failures.",
            suggestions=[
                f"evogitctl test run {pad_id}",
                f"evogitctl test run {pad_id} --target {target}",
            ],
            docs_url="docs/TESTING.md#run-tests",
            docs_url="docs/TESTING_GUIDE.md",
            details=str(exc),
        )
        raise click.Abort()


# ============================================================================
# Phase 3: Auto-Merge and CI Integration Commands
# ============================================================================


@pad.command("auto-merge")
@click.argument("pad_id")
@click.option("--target", type=click.Choice(["fast", "full"]), default="fast", help="Test target")
@click.option("--no-auto-promote", is_flag=True, help="Disable automatic promotion")
@click.option(
    "--test",
    "test_overrides",
    multiple=True,
    help="Override tests as NAME=CMD[:TIMEOUT] (repeat for multiple tests)",
)
@click.pass_context
def pad_auto_merge(
    ctx: click.Context,
    pad_id: str,
    target: str,
    no_auto_promote: bool,
    test_overrides: Tuple[str, ...],
) -> None:
    """
    Run tests and auto-promote if they pass (Phase 3).

    This is the complete auto-merge workflow:
    1. Run tests
    2. Analyze results
    3. Evaluate promotion gate
    4. Auto-promote if approved
    """
    from sologit.workflows.auto_merge import AutoMergeWorkflow
    from sologit.workflows.promotion_gate import PromotionRules

    git_engine = get_git_engine()
    test_orchestrator = get_test_orchestrator()
    state_manager = StateManager()

    workpad = git_engine.get_workpad(pad_id)
    if workpad is None:
        abort_with_error(f"Workpad {pad_id} not found")

    config_manager: ConfigManager = ctx.obj.get("config") if ctx and ctx.obj else ConfigManager()
    config_manager: ConfigManager
    if ctx.obj and isinstance(ctx.obj, dict) and 'config' in ctx.obj:
        config_manager = cast(ConfigManager, ctx.obj['config'])
    else:
        config_manager = ConfigManager()
    config_tests = config_manager.config.tests
    default_timeout = config_tests.timeout_seconds

    if test_overrides:
        tests = [_parse_test_override(value, default_timeout) for value in test_overrides]
    else:
        suite_entries = config_tests.fast_tests if target == "fast" else config_tests.full_tests
        tests = _tests_from_config_entries(suite_entries, default_timeout)

        if not tests:
            if target == "fast":
                tests = [
                    TestConfig(name="unit-tests", cmd="python -m pytest tests/ -q", timeout=60),
                ]
            else:
                tests = [
                    TestConfig(name="unit-tests", cmd="python -m pytest tests/ -q", timeout=60),
                    TestConfig(
                        name="integration",
                        cmd="python -m pytest tests/integration/ -q",
                        timeout=120,
                    ),
                ]

    # Configure promotion rules (can be loaded from config in future)
    rules = PromotionRules(
        require_tests=True, require_all_tests_pass=True, require_fast_forward=True
    )

    smoke_tests = _tests_from_config_entries(config_tests.smoke_tests, default_timeout)
    ci_orchestrator = CIOrchestrator(git_engine, test_orchestrator)
    rollback_handler = RollbackHandler(git_engine)

    workflow = AutoMergeWorkflow(
        git_engine,
        test_orchestrator,
        rules,
        state_manager=state_manager,
        ci_orchestrator=ci_orchestrator,
        rollback_handler=rollback_handler,
        ci_smoke_tests=smoke_tests,
        ci_config=config_manager.config.ci,
        rollback_on_ci_red=config_manager.config.rollback_on_ci_red,
    )

    try:
        formatter.print_header("Auto-Merge Workflow")
        overview = formatter.table(headers=["Field", "Value"])
        overview.add_row("Workpad", f"[bold]{workpad.title}[/bold] ({workpad.id[:8]})")
        overview.add_row("Target", target)
        overview.add_row("Auto-promote", "Enabled" if not no_auto_promote else "Disabled")
        overview.add_row("Tests", str(len(tests)))
        formatter.console.print(overview)

        # Execute workflow
        result = workflow.execute(
            pad_id, tests, parallel=True, auto_promote=not no_auto_promote, target=target
        )


@click.group()
def ci() -> None:
    """Continuous integration orchestration commands."""


@ci.command("status")
@click.argument("repo_id")
def ci_status(repo_id: str) -> None:
    """Display CI status information for a repository."""

    formatter.print_header("CI Status")
    formatter.print_info(f"Repository: {repo_id}")
    formatter.print_info(
        "CI orchestration helpers are not fully configured in this testing build."
    )


def execute_pair_loop(
    *,
    ctx: click.Context,
    prompt: str,
    repo_id: Optional[str] = None,
    title: Optional[str] = None,
    no_test: bool = False,
    no_promote: bool = False,
    target: str = "fast",
) -> Dict[str, str]:
    """Placeholder AI pair programming loop used by the CLI."""

    logger.info(
        "execute_pair_loop invoked with prompt=%r repo_id=%r title=%r target=%s",
        prompt,
        repo_id,
        title,
        target,
    )

    formatter.print_warning(
        "AI pair programming automation is not enabled in this environment."
    )
    formatter.print_info(
        "Prompt recorded. Skipping automated implementation and returning control to the user."
    )

    return {
        "status": "skipped",
        "prompt": prompt,
        "repo_id": repo_id or "<default>",
        "target": target,
        "tests_run": "no" if no_test else "n/a",
        "promoted": "no" if no_promote else "n/a",
    }

