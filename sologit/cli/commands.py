"""Command implementations for the Solo Git CLI."""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, NoReturn, Optional

import click
from rich.console import Console

from sologit.core.repository import Repository
from sologit.core.workpad import Workpad
from sologit.engines.git_engine import GitEngine, GitEngineError
from sologit.engines.patch_engine import PatchEngine
from sologit.engines.test_orchestrator import TestConfig, TestOrchestrator, TestStatus
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


_git_engine: Optional[GitEngine] = None
_patch_engine: Optional[PatchEngine] = None
_test_orchestrator: Optional[TestOrchestrator] = None
_git_state_sync: Optional[GitStateSync] = None
_ci_orchestrator: Optional[CIOrchestrator] = None
_rollback_handler: Optional[RollbackHandler] = None


_STATUS_ICONS = {
    TestStatus.PASSED: "✅",
    TestStatus.FAILED: "❌",
    TestStatus.TIMEOUT: "⏳",
    TestStatus.ERROR: "❌",
    TestStatus.SKIPPED: "⚪",
}


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
    """Display a formatted error with rich context and abort the command."""

    formatter.print_error(
        title or "Command Error",
        message,
        help_text=help_text or "Use the --help flag to review available options.",
        tip=tip or "Common fix: double-check CLI arguments and repository context.",
        suggestions=suggestions or [
            "evogitctl --help",
            "evogitctl history --recent",
        ],
        docs_url=docs_url,
        details=details,
    )
    raise click.Abort()


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


def _format_datetime(value: object) -> str:
    """Format a datetime-like object for output."""

    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    return str(value)


def _build_test_configs(target: str) -> List[TestConfig]:
    """Return default test configurations for the requested target."""

    if target == "full":
        return [
            TestConfig(name="lint", cmd="make lint", timeout=600),
            TestConfig(name="integration", cmd="pytest", timeout=1800),
        ]
    return [
        TestConfig(name="unit-tests", cmd="pytest -m fast", timeout=900),
    ]


@click.group()
def repo() -> None:
    """Repository management commands."""


@repo.command("init")
@click.option("--zip", "zip_file", type=click.Path(exists=True, path_type=Path), help="Initialize from zip file")
@click.option("--git", "git_url", type=str, help="Initialize from Git URL")
@click.option("--empty", is_flag=True, help="Initialize an empty repository managed by Solo Git")
@click.option(
    "--path",
    "target_path",
    type=click.Path(path_type=Path),
    help="Directory for empty repository (defaults to Solo Git data dir)",
)
@click.option("--name", type=str, help="Repository name (optional)")
def repo_init(
    zip_file: Optional[Path],
    git_url: Optional[str],
    empty: bool,
    target_path: Optional[Path],
    name: Optional[str],
) -> None:
    """Initialize a new repository from zip file, Git URL, or empty."""

    formatter.print_header("Repository Initialization")

    sources = {
        "zip": bool(zip_file),
        "git": bool(git_url),
        "empty": bool(empty),
    }
    provided_sources = [label for label, enabled in sources.items() if enabled]

    if len(provided_sources) != 1:
        abort_with_error(
            "Invalid Source Specification",
            "Please specify exactly one of --zip, --git, or --empty.",
            title="Repository Initialization Blocked",
            help_text="Choose one initialization method to continue.",
            suggestions=[
                "evogitctl repo init --zip app.zip",
                "evogitctl repo init --git https://github.com/user/repo.git",
                "evogitctl repo init --empty --name my-repo",
            ],
            docs_url="docs/SETUP.md#initialize-a-repository",
        )

    git_sync = get_git_sync()

    try:
        if zip_file:
            repo_name = name or zip_file.stem
            formatter.print_info(f"Initializing from zip: {zip_file.name}")
            repo_info = git_sync.init_repo_from_zip(zip_file.read_bytes(), repo_name)
        elif git_url:
            base = git_url.rstrip("/").split("/")[-1]
            if base.endswith(".git"):
                base = base[:-4]
            repo_name = name or base
            formatter.print_info(f"Cloning from: {git_url}")
            repo_info = git_sync.init_repo_from_git(git_url, repo_name)
        else:
            repo_name = name or (target_path.name if target_path else "solo-git-repo")
            formatter.print_info(f"Creating empty repository: {repo_name}")
            repo_info = git_sync.create_empty_repo(repo_name, str(target_path) if target_path else None)
    except GitEngineError as exc:
        abort_with_error(
            "Repository initialization failed",
            str(exc),
            title="Repository Initialization Failed",
            help_text="Confirm the source path or URL is reachable and credentials are valid.",
            tip="If cloning from a private remote, ensure SSH keys or tokens are configured.",
        )

    formatter.print_success("Repository initialized!")
    summary = formatter.table(headers=["Field", "Value"])
    summary.add_row("ID", f"[cyan]{repo_info['repo_id']}[/cyan]")
    summary.add_row("Name", f"[bold]{repo_info['name']}[/bold]")
    summary.add_row("Path", repo_info['path'])
    summary.add_row("Trunk", repo_info.get('trunk_branch', 'main'))
    formatter.console.print(summary)


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
        table.add_row(
            f"[cyan]{repo_obj.id}[/cyan]",
            f"[bold]{getattr(repo_obj, 'name', repo_obj.id)}[/bold]",
            getattr(repo_obj, 'trunk_branch', 'main'),
            str(getattr(repo_obj, 'workpad_count', 0)),
            _format_datetime(getattr(repo_obj, 'created_at', '')),
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
    except GitEngineError as exc:
        abort_with_error("Failed to delete repository", str(exc))


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

    panel_content = "\n".join(
        [
            f"[bold cyan]Repository:[/bold cyan] {repo_obj.id}",
            f"[bold]Name:[/bold] {repo_obj.name}",
            f"[bold]Path:[/bold] {repo_obj.path}",
            f"[bold]Trunk:[/bold] {repo_obj.trunk_branch}",
            f"[bold]Created:[/bold] {_format_datetime(repo_obj.created_at)}",
            f"[bold]Workpads:[/bold] {getattr(repo_obj, 'workpad_count', 0)} active",
            f"[bold]Source:[/bold] {getattr(repo_obj, 'source_type', 'unknown')}",
        ]
    )

    formatter.print_panel(panel_content, title=f"📦 Repository: {repo_obj.name}")

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
            repo = repos[0]
            repo_id = repo.id
            formatter.print_info(f"Using repository: {repo.name} ({repo_id})")
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

    assert repo_id is not None

    try:
        formatter.print_info(f"Creating workpad: {title}")
        pad_id = git_engine.create_workpad(repo_id, title)
        workpad = _require_workpad(git_engine.get_workpad(pad_id), pad_id)

        formatter.print_success("Workpad created!")
        formatter.print_info(f"Pad ID: {workpad.id}")
        formatter.print_info(f"Title: {workpad.title}")
        formatter.print_info(f"Branch: {workpad.branch_name}")

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
        status_display = f"[{status_color}]{status_icon} {status}[/{status_color}]"

        test_status = getattr(pad_obj, "test_status", None)
        if test_status:
            if test_status.lower() == "passed":
                test_display = "✅ passed"
            elif test_status.lower() == "failed":
                test_display = "❌ failed"
            else:
                test_display = "⏳ pending"
        else:
            test_display = "-"

        table.add_row(
            f"[cyan]{pad_obj.id[:8]}[/cyan]",
            f"[bold]{pad_obj.title}[/bold]",
            status_display,
            str(len(getattr(pad_obj, "checkpoints", []))),
            test_display,
            _format_datetime(getattr(pad_obj, "created_at", "")),
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
    formatter.print_info(f"Checkpoints: {len(getattr(workpad, 'checkpoints', []))}")
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
            f"[bold]Created:[/bold] {_format_datetime(getattr(workpad, 'created_at', ''))}",
            f"[bold]Checkpoints:[/bold] {len(getattr(workpad, 'checkpoints', []))}",
        ]
    )

    if getattr(workpad, "test_status", None):
        test_color = theme.get_status_color(workpad.test_status)
        test_icon = theme.get_status_icon(workpad.test_status)
        panel_content += f"\n[bold]Last Test:[/bold] [{test_color}]{test_icon} {workpad.test_status.upper()}[/{test_color}]"

    formatter.print_panel(panel_content, title="Workpad Summary")

    if getattr(workpad, "checkpoints", None):
        formatter.print_subheader("Checkpoints")
        formatter.print_bullet_list(list(workpad.checkpoints), icon=theme.icons.commit, style=theme.colors.blue)


@pad.command("promote")
@click.argument("pad_id")
def pad_promote(pad_id: str) -> None:
    """Promote a workpad to trunk via a fast-forward merge."""

    git_engine = get_git_engine()
    workpad = _require_workpad(git_engine.get_workpad(pad_id), pad_id)

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
    """Show the diff for a workpad."""

    git_engine = get_git_engine()
    workpad = git_engine.get_workpad(pad_id)
    if workpad is None:
        abort_with_error(f"Workpad {pad_id} not found")

    diff_text = git_engine.get_diff(pad_id)
    formatter.print_header("Workpad Diff")
    formatter.console.print(diff_text)


@click.group()
def test() -> None:
    """Test execution commands."""


@test.command("run")
@click.argument("pad_id")
@click.option("--target", type=click.Choice(["fast", "full"]), default="fast", show_default=True)
def test_run(pad_id: str, target: str) -> None:
    """Run tests for a workpad."""

    git_engine = get_git_engine()
    workpad = _require_workpad(git_engine.get_workpad(pad_id), pad_id)
    orchestrator = get_test_orchestrator()
    state_manager = StateManager()

    formatter.print_header("Test Execution")
    formatter.print_info(f"Workpad: {workpad.title}")

    test_configs = _build_test_configs(target)

    run_info = state_manager.create_test_run(pad_id, target)
    run_id = getattr(run_info, "run_id", None)
    if run_id is None:
        try:
            run_id = run_info["run_id"]
        except (TypeError, KeyError):
            abort_with_error("Could not determine run_id from test run info")
    state_manager.update_test_run(run_id, status="running")

    try:
        results = asyncio.run(orchestrator.run_tests(pad_id, tests=test_configs))
    except Exception as exc:  # pragma: no cover - exercised via tests with mocks
        logger.exception("Test execution failed for %s", pad_id)
        error_result = StateTestResult(
            test_id=f"{run_id}:orchestrator",
            name="orchestrator",
            status=TestStatus.ERROR.value,
            duration_ms=0,
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
            duration_ms=0,
            tests=[error_result],
        )
        abort_with_error(
            "Test execution failed",
            str(exc),
            title="Test Execution Failed",
            help_text=f"Workpad: {pad_id}",
            suggestions=[f"evogitctl test run {pad_id}"],
        )

    total = len(results)
    passed = sum(1 for result in results if result.status == TestStatus.PASSED)
    failed = sum(1 for result in results if result.status in {TestStatus.FAILED, TestStatus.ERROR, TestStatus.TIMEOUT})
    skipped = sum(1 for result in results if result.status == TestStatus.SKIPPED)
    duration_ms = sum(result.duration_ms for result in results)

    for result in results:
        icon = _STATUS_ICONS.get(result.status, theme.icons.info)
        formatter.print_info(f"{icon} {result.status.value} — {result.name}")

    formatter.print_subheader("Test Summary")

    if failed == 0:
        formatter.print_success("All tests passed!")
    else:
        formatter.print_warning("Tests Require Attention")
        formatter.print_info("Some tests failed or timed out. Review results below.")

    summary_table = formatter.table(headers=["Metric", "Value"])
    summary_table.add_row("Total", str(total))
    summary_table.add_row("Passed", str(passed))
    summary_table.add_row("Failed", str(failed))
    summary_table.add_row("Skipped", str(skipped))
    summary_table.add_row("Duration (ms)", str(duration_ms))
    formatter.console.print(summary_table)
    formatter.print_info(f"Passed: {passed}")
    formatter.print_info(f"Failed: {failed}")
    formatter.print_info(f"Skipped: {skipped}")

    state_results: List[StateTestResult] = []
    for result in results:
        state_results.append(
            StateTestResult(
                test_id=f"{run_id}:{result.name}",
                name=result.name,
                status=result.status.value,
                duration_ms=result.duration_ms,
                output=(result.stdout or result.stderr or ""),
                error=result.error,
            )
        )

    overall_status = "passed" if failed == 0 else "failed"

    state_manager.update_test_run(
        run_id,
        status=overall_status,
        total_tests=total,
        passed=passed,
        failed=failed,
        skipped=skipped,
        duration_ms=duration_ms,
        tests=state_results,
    )

    if failed == 0:
        formatter.print_success("Test run completed successfully.")
    else:
        formatter.print_warning("Test run completed with failures.")


@click.group()
def ci() -> None:
    """Continuous integration helper commands."""


@ci.command("trigger")
@click.argument("pipeline")
def ci_trigger(pipeline: str) -> None:
    """Trigger a CI pipeline (placeholder implementation)."""

    formatter.print_warning(
        "CI integration is not configured for this environment."
    )
    formatter.print_info(f"Requested pipeline: {pipeline}")


def execute_pair_loop(
    *,
    ctx: click.Context,
    prompt: str,
    repo_id: Optional[str] = None,
    title: Optional[str] = None,
    no_test: bool = False,
    no_promote: bool = False,
    target: str = "fast",
) -> None:
    """Placeholder pair-programming loop used by the CLI."""

    formatter.print_warning(
        "AI pair programming is not available in this build.",
    )
    formatter.print_info(
        "Requested prompt: %s" % prompt
    )
