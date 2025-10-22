
"""Command implementations for Solo Git CLI."""

import asyncio
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, NoReturn, Optional, Sequence, Tuple, TypeVar, Union, cast

import click
from rich.console import Console

from sologit.config.manager import ConfigManager
from sologit.engines.git_engine import GitEngine, GitEngineError
from sologit.engines.patch_engine import PatchEngine
from sologit.engines.test_orchestrator import (
    TestConfig,
    TestOrchestrator,
    TestResult,
    TestStatus,
)
from sologit.state.manager import StateManager
from sologit.utils.logger import get_logger
from sologit.ui.formatter import RichFormatter
from sologit.ui.theme import theme
from sologit.workflows.ci_orchestrator import CIOrchestrator
from sologit.workflows.rollback_handler import RollbackHandler

logger = get_logger(__name__)

StageResult = TypeVar("StageResult")

# Initialize Rich formatter
formatter = RichFormatter()


def set_formatter_console(console: Console) -> None:
    """Allow external modules to configure the console used by the formatter."""
    formatter.set_console(console)


def abort_with_error(message: str, details: Optional[str] = None) -> NoReturn:
    """Display a formatted error and abort the command."""
    plain_message = f"Error: {message}"
    formatter.print_error(plain_message)

    content = f"[bold]{plain_message}[/bold]"
    if details:
        content += f"\n\n{details}"
    formatter.print_error_panel(content)
    raise click.Abort()


# Initialize engines (singleton pattern)
_git_engine: Optional[GitEngine] = None
_patch_engine: Optional[PatchEngine] = None
_test_orchestrator: Optional[TestOrchestrator] = None
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get or create ConfigManager instance."""

    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


TestEntry = Union[TestConfig, Dict[str, Any]]


def _tests_from_config_entries(
    entries: Optional[Sequence[TestEntry]],
    default_timeout: int,
) -> List[TestConfig]:
    """Convert config entries to TestConfig objects."""
    tests: List[TestConfig] = []

    if not entries:
        return tests

    for entry in entries:
        if isinstance(entry, TestConfig):
            tests.append(entry)
            continue

        if not isinstance(entry, dict):
            logger.warning(f"Ignoring invalid test entry: {entry}")
            continue

        name = entry.get('name')
        cmd = entry.get('cmd')
        if not name or not cmd:
            logger.warning(f"Test entry missing name/cmd: {entry}")
            continue

        timeout_value = entry.get('timeout', default_timeout)
        timeout = int(timeout_value) if timeout_value is not None else default_timeout
        depends_on_raw = entry.get('depends_on', []) or []
        if isinstance(depends_on_raw, list):
            depends_on_list = depends_on_raw
        elif not depends_on_raw:
            depends_on_list = []
        else:
            logger.warning("Ignoring non-list depends_on value for test '%s'", name)
            depends_on_list = []
        tests.append(
            TestConfig(
                name=name,
                cmd=cmd,
                timeout=timeout,
                depends_on=list(depends_on_list),
            )
        )

    return tests


def _parse_test_override(value: str, default_timeout: int) -> TestConfig:
    """Parse CLI test override in the form NAME=CMD[:TIMEOUT]."""
    if '=' not in value:
        raise click.BadParameter("Must be in NAME=CMD[:TIMEOUT] format")

    name, remainder = value.split('=', 1)
    name = name.strip()
    remainder = remainder.strip()

    if not name or not remainder:
        raise click.BadParameter("Both name and command must be provided")

    timeout = default_timeout
    if ':' in remainder:
        cmd, timeout_str = remainder.rsplit(':', 1)
        cmd = cmd.strip()
        try:
            timeout = int(timeout_str.strip())
        except ValueError as exc:
            raise click.BadParameter("Timeout must be an integer") from exc
    else:
        cmd = remainder

    if not cmd:
        raise click.BadParameter("Command cannot be empty")

    return TestConfig(name=name, cmd=cmd, timeout=timeout)


def get_git_engine() -> GitEngine:
    """Get or create GitEngine instance."""
    global _git_engine
    if _git_engine is None:
        _git_engine = GitEngine()
    return _git_engine


def get_patch_engine() -> PatchEngine:
    """Get or create PatchEngine instance."""
    global _patch_engine
    if _patch_engine is None:
        _patch_engine = PatchEngine(get_git_engine())
    return _patch_engine


def get_test_orchestrator() -> TestOrchestrator:
    """Get or create TestOrchestrator instance."""
    global _test_orchestrator
    if _test_orchestrator is None:
        config = get_config_manager().config.tests
        log_dir = Path(config.log_dir).expanduser()
        _test_orchestrator = TestOrchestrator(
            get_git_engine(),
            sandbox_image=config.sandbox_image,
            execution_mode=config.execution_mode,
            log_dir=log_dir,
            formatter=formatter,
        )
    return _test_orchestrator


@click.group()
def repo() -> None:
    """Repository management commands."""
    pass


@repo.command('init')
@click.option('--zip', 'zip_file', type=click.Path(exists=True), help='Initialize from zip file')
@click.option('--git', 'git_url', type=str, help='Initialize from Git URL')
@click.option('--name', type=str, help='Repository name (optional)')
def repo_init(zip_file: Optional[str], git_url: Optional[str], name: Optional[str]) -> None:
    """Initialize a new repository from zip file or Git URL."""
    formatter.print_header("Repository Initialization")

    if not zip_file and not git_url:
        abort_with_error("Must provide either --zip or --git")

    if zip_file and git_url:
        abort_with_error("Cannot provide both --zip and --git")

    git_engine = get_git_engine()

    try:
        if zip_file:
            if zip_file is None:
                abort_with_error("Internal error: zip_file is unexpectedly None")
            zip_path = Path(zip_file)
            formatter.print_info(f"Initializing repository from zip: {zip_path.name}")
        else:
            assert git_url is not None
            if not name:
                name = Path(git_url).stem.replace('.git', '')
            formatter.print_info(f"Cloning repository from: {git_url}")

        with formatter.progress("Setting up repository") as progress:
            total_steps = 3
            overall_task = progress.add_task("Repository initialization", total=total_steps)

            def run_stage(description: str, operation: Callable[[], StageResult]) -> StageResult:
                stage_task = progress.add_task(description, total=None)
                progress.update(overall_task, description=description)
                success = False
                start = time.perf_counter()
                try:
                    result = operation()
                    success = True
                    return result
                finally:
                    progress.remove_task(stage_task)
                    if success:
                        progress.advance(overall_task, 1)
                        duration = time.perf_counter() - start
                        logger.debug("Stage '%s' completed in %.2fs", description, duration)

            if zip_file:
                zip_data = run_stage("Loading archive from disk", lambda: zip_path.read_bytes())

                if not name:
                    name = zip_path.stem

                repo_id = run_stage(
                    "Importing files & creating initial commit",
                    lambda: git_engine.init_from_zip(zip_data, name),
                )
            else:  # git_url
                run_stage("Preparing clone parameters", lambda: None)

                repo_id = run_stage(
                    "Cloning remote repository",
                    lambda: git_engine.init_from_git(git_url, name),
                )

            final_stage_label = (
                "Verifying initial commit & metadata"
                if zip_file
                else "Recording repository metadata"
            )
            repo = run_stage(
                final_stage_label,
                lambda: git_engine.get_repo(repo_id),
            )

            progress.update(
                overall_task,
                description="Repository ready",
                completed=total_steps,
            )

        formatter.print_success("Repository initialized!")
        formatter.print_info(f"Repo ID: {repo.id}")
        formatter.print_info(f"Name: {repo.name}")
        formatter.print_info(f"Path: {repo.path}")
        formatter.print_info(f"Trunk: {repo.trunk_branch}")

        summary_table = formatter.table(headers=["Field", "Value"])
        summary_table.add_row("ID", f"[cyan]{repo.id}[/cyan]")
        summary_table.add_row("Name", f"[bold]{repo.name}[/bold]")
        summary_table.add_row("Path", f"{repo.path}")
        summary_table.add_row("Trunk", f"[cyan]{repo.trunk_branch}[/cyan]")

        formatter.console.print(summary_table)

    except GitEngineError as e:
        abort_with_error(str(e), "Repository initialization failed")


@repo.command('list')
def repo_list() -> None:
    """List all repositories."""
    git_engine = get_git_engine()
    repos = git_engine.list_repos()
    
    if not repos:
        formatter.print_info("No repositories found.")
        formatter.print("\n💡 Create a repository with: evogitctl repo init --zip app.zip")
        return
    
    # Create a Rich table
    formatter.print_header(f"Repositories ({len(repos)})")
    table = formatter.table(headers=["ID", "Name", "Trunk", "Workpads", "Created"])
    
    for repo in repos:
        table.add_row(
            f"[cyan]{repo.id}[/cyan]",
            f"[bold]{repo.name}[/bold]",
            repo.trunk_branch,
            str(repo.workpad_count),
            repo.created_at.strftime('%Y-%m-%d %H:%M')
        )
    
    formatter.console.print(table)
    formatter.console.print()


@repo.command('info')
@click.argument('repo_id')
def repo_info(repo_id: str) -> None:
    """Show repository information."""
    git_engine = get_git_engine()
    repo = git_engine.get_repo(repo_id)

    if repo is None:
        formatter.print_error(f"Repository {repo_id} not found")
        raise click.Abort()
    
    # Create formatted info panel
    info = f"""[bold cyan]Repository:[/bold cyan] {repo.id}
[bold]Name:[/bold] {repo.name}
[bold]Path:[/bold] {repo.path}
[bold]Trunk:[/bold] {repo.trunk_branch}
[bold]Created:[/bold] {repo.created_at.strftime('%Y-%m-%d %H:%M:%S')}
[bold]Workpads:[/bold] {repo.workpad_count} active
[bold]Source:[/bold] {repo.source_type}"""
    
    if repo.source_url:
        info += f"\n[bold]URL:[/bold] {repo.source_url}"
    
    formatter.print_panel(info, title=f"📦 Repository: {repo.name}")


@click.group()
def pad() -> None:
    """Workpad management commands."""
    pass


@pad.command('create')
@click.argument('title')
@click.option('--repo', 'repo_id', type=str, help='Repository ID (required if multiple repos)')
def pad_create(title: str, repo_id: Optional[str]) -> None:
    """Create a new workpad."""
    git_engine = get_git_engine()

    formatter.print_header("Workpad Creation")

    # If no repo_id, try to auto-select
    if not repo_id:
        repos = git_engine.list_repos()
        if len(repos) == 0:
            abort_with_error("No repositories found", "Initialize a repository first: evogitctl repo init --zip app.zip")
        elif len(repos) == 1:
            repo_id = repos[0].id
            formatter.print_info(f"Using repository: {repos[0].name} ({repo_id})")
        else:
            formatter.print_warning("Multiple repositories found. Use --repo to specify an ID.")
            repo_table = formatter.table(headers=["ID", "Name"])
            for repo in repos:
                repo_identifier = getattr(repo, "id", "<unknown>")
                repo_name = getattr(repo, "name", repo_identifier)
                repo_table.add_row(f"[cyan]{repo_identifier}[/cyan]", str(repo_name))
            formatter.print_info_panel(
                "Multiple repositories detected. Please rerun with --repo <ID>.",
                title="Repository Selection Required"
            )
            formatter.console.print(repo_table)
            raise click.Abort()

    try:
        formatter.print_info(f"Creating workpad: {title}")
        pad_id = git_engine.create_workpad(repo_id, title)

        workpad = git_engine.get_workpad(pad_id)
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

    except GitEngineError as e:
        abort_with_error("Failed to create workpad", str(e))


@pad.command('list')
@click.option('--repo', 'repo_id', type=str, help='Filter by repository ID')
def pad_list(repo_id: Optional[str]) -> None:
    """List all workpads."""
    git_engine = get_git_engine()
    workpads = git_engine.list_workpads(repo_id)
    
    if not workpads:
        formatter.print_info("No workpads found.")
        formatter.print("\n💡 Create a workpad with: evogitctl pad create \"add feature\"")
        return
    
    # Create a Rich table
    title = f"Workpads ({len(workpads)})"
    if repo_id:
        title += f" for repo {repo_id}"
    
    formatter.print_header(title)
    table = formatter.table(headers=["ID", "Title", "Status", "Checkpoints", "Tests", "Created"])
    
    for pad in workpads:
        # Color-code status
        status_color = "green" if pad.status == "active" else "yellow" if pad.status == "pending" else "red"
        status_display = f"[{status_color}]{pad.status}[/{status_color}]"
        
        # Test status with icon
        test_display = ""
        if pad.test_status:
            test_icon = "✅" if pad.test_status == "passed" else "❌" if pad.test_status == "failed" else "⏳"
            test_display = f"{test_icon} {pad.test_status}"
        
        table.add_row(
            f"[cyan]{pad.id[:8]}[/cyan]",
            f"[bold]{pad.title}[/bold]",
            status_display,
            str(len(pad.checkpoints)),
            test_display,
            pad.created_at.strftime('%Y-%m-%d %H:%M')
        )
    
    formatter.console.print(table)
    formatter.console.print()


@pad.command('info')
@click.argument('pad_id')
def pad_info(pad_id: str) -> None:
    """Show workpad information."""
    git_engine = get_git_engine()
    workpad = git_engine.get_workpad(pad_id)

    if not workpad:
        abort_with_error(f"Workpad {pad_id} not found")

    formatter.print_header(f"Workpad Details: {workpad.title}")

    formatter.print_info(f"Workpad: {workpad.id}")
    formatter.print_info(f"Title: {workpad.title}")
    formatter.print_info(f"Repo: {workpad.repo_id}")
    formatter.print_info(f"Branch: {workpad.branch_name}")
    formatter.print_info(f"Status: {workpad.status}")
    formatter.print_info(f"Checkpoints: {len(workpad.checkpoints)}")
    if workpad.test_status:
        formatter.print_info(f"Last Test: {workpad.test_status}")

    status_color = theme.get_status_color(workpad.status)
    status_icon = theme.get_status_icon(workpad.status)
    panel_content = f"""[bold]Workpad ID:[/bold] [cyan]{workpad.id}[/cyan]
[bold]Repository:[/bold] {workpad.repo_id}
[bold]Branch:[/bold] {workpad.branch_name}
[bold]Status:[/bold] [{status_color}]{status_icon} {workpad.status.upper()}[/{status_color}]
[bold]Created:[/bold] {workpad.created_at.strftime('%Y-%m-%d %H:%M:%S')}
[bold]Checkpoints:[/bold] {len(workpad.checkpoints)}"""

    if workpad.test_status:
        test_color = theme.get_status_color(workpad.test_status)
        test_icon = theme.get_status_icon(workpad.test_status)
        panel_content += f"\n[bold]Last Test:[/bold] [{test_color}]{test_icon} {workpad.test_status.upper()}[/{test_color}]"

    formatter.print_info_panel(panel_content, title="Workpad Summary")

    if workpad.checkpoints:
        formatter.print_subheader("Checkpoints")
        formatter.print_bullet_list(workpad.checkpoints, icon=theme.icons.commit, style=theme.colors.blue)


@pad.command('promote')
@click.argument('pad_id')
def pad_promote(pad_id: str) -> None:
    """Promote workpad to trunk (fast-forward merge)."""
    git_engine = get_git_engine()

    workpad = git_engine.get_workpad(pad_id)
    if workpad is None:
        abort_with_error(f"Workpad {pad_id} not found")

    # Check if can promote
    if not git_engine.can_promote(pad_id):
        abort_with_error(
            "Cannot promote: not fast-forward-able",
            "Trunk has diverged. Manual merge required before promotion."
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

    except GitEngineError as e:
        abort_with_error("Promotion failed", str(e))


@pad.command('diff')
@click.argument('pad_id')
def pad_diff(pad_id: str) -> None:
    """Show diff between workpad and trunk."""
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
    except GitEngineError as e:
        abort_with_error("Failed to generate diff", str(e))


@click.group()
def test() -> None:
    """Test execution commands."""
    pass


@test.command('run')
@click.argument('pad_id')
@click.option('--target', type=click.Choice(['fast', 'full']), default='fast', help='Test target')
@click.option('--parallel/--sequential', default=True, help='Parallel execution')
def test_run(pad_id: str, target: str, parallel: bool) -> None:
    """Run tests for a workpad with live output streaming."""

    git_engine = get_git_engine()
    test_orchestrator = get_test_orchestrator()

    workpad = git_engine.get_workpad(pad_id)
    if workpad is None:
        abort_with_error(f"Workpad {pad_id} not found")

    if target == 'fast':
        tests = [
            TestConfig(name="unit-tests", cmd="python -m pytest tests/ -q", timeout=60),
        ]
    else:
        tests = [
            TestConfig(name="unit-tests", cmd="python -m pytest tests/ -q", timeout=60),
            TestConfig(name="integration", cmd="python -m pytest tests/integration/ -q", timeout=120),
        ]

    try:
        info = f"""[bold]Workpad:[/bold] {workpad.title}
[bold]Tests:[/bold] {len(tests)}
[bold]Execution:[/bold] {'Parallel' if parallel else 'Sequential'}
[bold]Mode:[/bold] {test_orchestrator.mode.value}
[bold]Target:[/bold] {target}"""
        formatter.print_panel(info, title="🧪 Test Execution")

        with formatter.create_progress() as progress:
            task = progress.add_task(f"Running {target} tests...", total=len(tests))

            def handle_output(test_name: str, stream: str, line: str) -> None:
                style = "cyan" if stream == "stdout" else "red"
                prefix = "stdout" if stream == "stdout" else "stderr"
                formatter.console.print(
                    f"[{prefix}] {test_name}: {line}",
                    style=style,
                )

            def handle_complete(result: TestResult) -> None:
                progress.advance(task)

            results: List[TestResult] = asyncio.run(
                test_orchestrator.run_tests(
                    pad_id,
                    tests,
                    parallel=parallel,
                    on_output=handle_output,
                    on_test_complete=handle_complete,
                )
            )

        formatter.console.print()

        table = formatter.table(headers=["Test", "Status", "Duration", "Mode", "Notes", "Log"])

        for result in results:
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
            notes = result.error or result.stderr or ""
            notes = notes.replace("\n", " ")
            if len(notes) > 80:
                notes = notes[:77] + "..."
            log_display = result.log_path.name if result.log_path else "-"

            table.add_row(
                result.name,
                status_text,
                f"{duration_s:.2f}s",
                result.mode,
                notes,
                log_display,
            )

        formatter.console.print(table)

        summary: Dict[str, Any] = test_orchestrator.get_summary(results)
        status_color = "green" if summary['status'] == 'green' else "red"
        summary_text = f"""[bold]Total:[/bold] {summary['total']}
[bold]Passed:[/bold] [green]{summary['passed']}[/green]
[bold]Failed:[/bold] [red]{summary['failed']}[/red]
[bold]Timeout:[/bold] {summary['timeout']}
[bold]Skipped:[/bold] {summary['skipped']}
[bold]Status:[/bold] [{status_color}]{summary['status'].upper()}[/{status_color}]"""

        formatter.print_panel(summary_text, title="📊 Test Summary")

        workpad.test_status = summary['status']

        if summary['status'] == 'green':
            formatter.print_success("All tests passed! Ready to promote.")
        else:
            formatter.print_error("Some tests require attention before promoting.")

        log_paths = [res.log_path for res in results if res.log_path]
        if log_paths:
            formatter.print_info(
                f"Detailed logs saved to {log_paths[0].parent}"
            )

    except Exception as exc:
        formatter.print_error(f"Test execution failed: {exc}")
        raise click.Abort()





# ============================================================================
# Phase 3: Auto-Merge and CI Integration Commands
# ============================================================================

@pad.command('auto-merge')
@click.argument('pad_id')
@click.option('--target', type=click.Choice(['fast', 'full']), default='fast', help='Test target')
@click.option('--no-auto-promote', is_flag=True, help='Disable automatic promotion')
@click.option(
    '--test', 'test_overrides', multiple=True,
    help='Override tests as NAME=CMD[:TIMEOUT] (repeat for multiple tests)'
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
        suite_entries = config_tests.fast_tests if target == 'fast' else config_tests.full_tests
        tests = _tests_from_config_entries(suite_entries, default_timeout)

        if not tests:
            if target == 'fast':
                tests = [
                    TestConfig(name="unit-tests", cmd="python -m pytest tests/ -q", timeout=60),
                ]
            else:
                tests = [
                    TestConfig(name="unit-tests", cmd="python -m pytest tests/ -q", timeout=60),
                    TestConfig(name="integration", cmd="python -m pytest tests/integration/ -q", timeout=120),
                ]

    # Configure promotion rules (can be loaded from config in future)
    rules = PromotionRules(
        require_tests=True,
        require_all_tests_pass=True,
        require_fast_forward=True
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
        rollback_on_ci_red=config_manager.config.rollback_on_ci_red
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
            pad_id,
            tests,
            parallel=True,
            auto_promote=not no_auto_promote,
            target=target
        )

        # Display formatted result
        formatter.print_info_panel(workflow.format_result(result), title="Auto-Merge Result")

        # Exit with appropriate code
        if not result.success and result.promotion_decision and not result.promotion_decision.can_promote:
            raise click.Abort()

    except Exception as e:
        abort_with_error("Auto-merge failed", str(e))


@pad.command('evaluate')
@click.argument('pad_id')
def pad_evaluate(pad_id: str) -> None:
    """
    Evaluate promotion gate without promoting (Phase 3).
    
    Shows whether a workpad is ready to be promoted based on configured rules.
    """
    from sologit.workflows.promotion_gate import PromotionGate, PromotionRules
    
    git_engine = get_git_engine()

    workpad = git_engine.get_workpad(pad_id)
    if workpad is None:
        abort_with_error(f"Workpad {pad_id} not found")
    
    # Configure rules
    rules = PromotionRules(
        require_tests=True,
        require_all_tests_pass=True,
        require_fast_forward=True
    )
    
    # Create gate
    gate = PromotionGate(git_engine, rules)
    
    try:
        formatter.print_header("Promotion Gate Evaluation")
        formatter.print_info(f"Evaluating workpad: {workpad.title}")

        # Evaluate (without test results for now)
        # In full implementation, would load cached test results
        decision = gate.evaluate(pad_id, test_analysis=None)

        # Display decision
        formatter.print_info_panel(gate.format_decision(decision), title="Promotion Decision")

        # Exit code based on decision
        if not decision.can_promote:
            raise click.Abort()

    except Exception as e:
        abort_with_error("Evaluation failed", str(e))


@click.group()
def ci() -> None:
    """CI and smoke test commands (Phase 3)."""
    pass


@ci.command('smoke')
@click.argument('repo_id')
@click.option('--commit', help='Commit hash to test (default: HEAD)')
def ci_smoke(repo_id: str, commit: Optional[str]) -> None:
    """
    Run smoke tests for a commit (Phase 3).
    
    This simulates post-merge CI smoke tests.
    """
    from sologit.workflows.ci_orchestrator import CIOrchestrator
    
    git_engine = get_git_engine()
    test_orchestrator = get_test_orchestrator()

    repo = git_engine.get_repo(repo_id)
    if not repo:
        abort_with_error(f"Repository {repo_id} not found")
    
    # Get commit hash
    if not commit:
        # Get HEAD commit
        commit = git_engine.get_current_commit(repo_id)
    
    # Define smoke tests
    smoke_tests = [
        TestConfig(name="smoke-health", cmd="python -c 'print(\"Health check passed\")'", timeout=10),
        TestConfig(name="smoke-unit", cmd="python -m pytest tests/ -q --tb=no", timeout=60),
    ]
    
    # Create orchestrator
    orchestrator = CIOrchestrator(git_engine, test_orchestrator)
    
    def progress_callback(message: str) -> None:
        formatter.print(f"   {message}")

    try:
        formatter.print_header("CI Smoke Tests")
        info_table = formatter.table(headers=["Field", "Value"])
        info_table.add_row("Repository", f"{repo.name} ({repo_id})")
        info_table.add_row("Commit", commit[:8])
        info_table.add_row("Tests", str(len(smoke_tests)))
        formatter.console.print(info_table)

        # Run smoke tests
        result = orchestrator.run_smoke_tests(
            repo_id,
            commit,
            smoke_tests,
            on_progress=progress_callback
        )

        # Display result
        formatter.print_info_panel(orchestrator.format_result(result), title="Smoke Test Summary")

        # Exit code based on result
        if result.is_red:
            raise click.Abort()

    except Exception as e:
        abort_with_error("Smoke tests failed", str(e))


@ci.command('rollback')
@click.argument('repo_id')
@click.option('--commit', required=True, help='Commit hash to rollback')
@click.option('--recreate-pad/--no-recreate-pad', default=True, help='Recreate workpad for fixes')
def ci_rollback(repo_id: str, commit: str, recreate_pad: bool) -> None:
    """
    Manually rollback a commit (Phase 3).
    
    Reverts the specified commit and optionally recreates a workpad.
    """
    from sologit.workflows.rollback_handler import RollbackHandler
    from sologit.workflows.ci_orchestrator import CIResult, CIStatus
    
    git_engine = get_git_engine()

    repo = git_engine.get_repo(repo_id)
    if not repo:
        abort_with_error(f"Repository {repo_id} not found")
    
    # Create handler
    handler = RollbackHandler(git_engine)
    
    # Create a fake CI result for the rollback
    fake_ci_result = CIResult(
        repo_id=repo_id,
        commit_hash=commit,
        status=CIStatus.FAILURE,
        duration_ms=0,
        test_results=[],
        message="Manual rollback"
    )
    
    try:
        formatter.print_header("CI Rollback")
        info_table = formatter.table(headers=["Field", "Value"])
        info_table.add_row("Repository", f"{repo.name} ({repo_id})")
        info_table.add_row("Commit", commit[:8])
        info_table.add_row("Recreate Workpad", "Yes" if recreate_pad else "No")
        formatter.console.print(info_table)

        # Perform rollback
        result = handler.handle_failed_ci(fake_ci_result, recreate_pad)

        # Display result
        formatter.print_info_panel(handler.format_result(result), title="Rollback Result")

        # Exit code
        if not result.success:
            raise click.Abort()

    except Exception as e:
        abort_with_error("Rollback failed", str(e))


@test.command('analyze')
@click.argument('pad_id')
def test_analyze(pad_id: str) -> None:
    """
    Analyze test failures for a workpad (Phase 3).
    
    Shows failure patterns and suggested fixes.
    """
    from sologit.analysis.test_analyzer import TestAnalyzer
    
    git_engine = get_git_engine()
    test_orchestrator = get_test_orchestrator()
    
    workpad = git_engine.get_workpad(pad_id)
    if not workpad:
        abort_with_error(f"Workpad {pad_id} not found")
    
    # Check if tests have been run
    # In a full implementation, we'd cache test results
    # For now, prompt user to run tests first
    
    formatter.print_header("Test Failure Analysis")
    formatter.print_warning("Test analysis requires recent test results.")
    formatter.print_info(f"Run: [bold]evogitctl test run {pad_id}[/bold] before analyzing.")
    formatter.print_info_panel(
        "In Phase 3, test results will be cached and analyzed automatically.",
        title="Coming Soon"
    )


# ============================================================================
# Phase 4: Complete Pair Loop Implementation
# ============================================================================

def execute_pair_loop(
    ctx: click.Context,
    prompt: str,
    repo_id: Optional[str],
    title: Optional[str],
    no_test: bool,
    no_promote: bool,
    target: str,
) -> None:
    """
    Execute the complete AI pair programming loop.
    
    This is the core workflow of Solo Git:
    1. Select/validate repository
    2. Create ephemeral workpad
    3. AI plans implementation
    4. AI generates patch
    5. Apply patch to workpad
    6. Run tests (optional)
    7. Auto-promote if green (optional)
    
    Args:
        ctx: Click context
        prompt: Natural language task description
        repo_id: Repository ID (auto-selected if None)
        title: Workpad title (derived from prompt if None)
        no_test: Skip test execution
        no_promote: Disable automatic promotion
        target: Test target (fast/full)
    """
    from sologit.orchestration.ai_orchestrator import AIOrchestrator
    from sologit.engines.patch_engine import PatchEngine
    from sologit.workflows.auto_merge import AutoMergeWorkflow
    from sologit.workflows.promotion_gate import PromotionRules
    
    import time
    
    git_engine = get_git_engine()
    if ctx.obj and isinstance(ctx.obj, dict) and 'config' in ctx.obj:
        config_manager = cast(ConfigManager, ctx.obj['config'])
    else:
        config_manager = ConfigManager()

    formatter.print_header("AI Pair Programming Session")

    # Step 1: Select repository
    if not repo_id:
        repos = git_engine.list_repos()
        if len(repos) == 0:
            abort_with_error(
                "No repositories found",
                "Initialize a repository first: evogitctl repo init --zip app.zip"
            )
        elif len(repos) == 1:
            repo_id = repos[0].id
            formatter.print_info(f"Using repository: {repos[0].name} ({repo_id})")
        else:
            repo_table = formatter.table(headers=["ID", "Name", "Trunk"])
            for repo in repos:
                repo_table.add_row(f"[cyan]{repo.id}[/cyan]", repo.name, repo.trunk_branch)
            formatter.print_info_panel(
                "Multiple repositories detected. Re-run with --repo <ID> to specify the target.",
                title="Repository Selection Required"
            )
            formatter.console.print(repo_table)
            raise click.Abort()

    # Validate repository exists
    repo = git_engine.get_repo(repo_id)
    if not repo:
        abort_with_error(f"Repository {repo_id} not found")

    # Step 2: Create workpad title if missing
    if not title:
        words = prompt.split()[:5]
        title = '-'.join(words).lower()
        title = ''.join(c if c.isalnum() or c == '-' else '-' for c in title)
        title = '-'.join(filter(None, title.split('-')))

    overview = formatter.table(headers=["Field", "Value"])
    overview.add_row("Repository", f"{repo.name} ({repo_id})")
    overview.add_row("Prompt", prompt)
    overview.add_row("Workpad Title", title)
    overview.add_row("Tests", "Skipped" if no_test else target)
    overview.add_row("Auto-Promote", "Disabled" if no_promote else "Enabled")
    formatter.console.print(overview)

    pad_id: Optional[str] = None

    try:
        formatter.print_subheader("Workpad Setup")
        formatter.print_info("Creating ephemeral workpad...")
        pad_id = git_engine.create_workpad(repo_id, title)
        workpad = git_engine.get_workpad(pad_id)
        formatter.print_success("Workpad created")

        workpad_table = formatter.table(headers=["Field", "Value"])
        workpad_table.add_row("Workpad ID", f"[cyan]{pad_id}[/cyan]")
        workpad_table.add_row("Branch", workpad.branch_name)
        workpad_table.add_row("Base", repo.trunk_branch)
        formatter.console.print(workpad_table)

        # Step 3: AI Planning
        formatter.print_subheader("AI Planning")
        formatter.print_info(f"Model: {config_manager.config.models.planning_model}")
        start_time = time.time()

        orchestrator = AIOrchestrator(config_manager, formatter=formatter)

        repo_map = git_engine.get_repo_map(repo_id)
        context = {
            'repo_id': repo_id,
            'repo_name': repo.name,
            'file_tree': repo_map,
            'trunk_branch': repo.trunk_branch
        }

        plan_response = orchestrator.plan(
            prompt=prompt,
            repo_context=context
        )

        planning_time = time.time() - start_time
        plan_panel = f"""[bold]Model:[/bold] {plan_response.model_used}
[bold]Duration:[/bold] {planning_time:.1f}s
[bold]Cost:[/bold] ${plan_response.cost_usd:.4f}
[bold]Complexity:[/bold] {plan_response.complexity.score:.2f}"""
        formatter.print_info_panel(plan_panel, title="Plan Generation")

        plan = plan_response.plan
        plan_table = formatter.table(headers=["Aspect", "Details"])
        plan_table.add_row("Description", plan.description or "-")
        plan_table.add_row(
            "Modify",
            ', '.join(plan.files_to_modify) if plan.files_to_modify else "None"
        )
        plan_table.add_row(
            "Create",
            ', '.join(plan.files_to_create) if plan.files_to_create else "None"
        )
        plan_table.add_row("Test Strategy", plan.test_strategy or "None")
        formatter.console.print(plan_table)

        # Step 4: Generate Patch
        formatter.print_subheader("Code Generation")
        formatter.print_info(f"Model: {config_manager.config.models.coding_model}")
        start_time = time.time()

        patch_response = orchestrator.generate_patch(
            plan=plan,
            repo_context=context
        )

        coding_time = time.time() - start_time
        patch_panel = f"""[bold]Model:[/bold] {patch_response.model_used}
[bold]Duration:[/bold] {coding_time:.1f}s
[bold]Cost:[/bold] ${patch_response.cost_usd:.4f}"""
        formatter.print_info_panel(patch_panel, title="Patch Generation")

        patch = patch_response.patch
        if patch.description:
            formatter.print_info(f"Patch notes: {patch.description}")

        # Step 5: Apply Patch
        formatter.print_subheader("Applying Patch")
        patch_engine = get_patch_engine()

        try:
            result = patch_engine.apply_patch(pad_id, patch.diff)
            formatter.print_success("Patch applied successfully")
            diff_table = formatter.table(headers=["Metric", "Value"])
            diff_table.add_row("Files Changed", str(result.files_changed))
            diff_table.add_row("Insertions", f"+{result.insertions}")
            diff_table.add_row("Deletions", f"-{result.deletions}")
            formatter.console.print(diff_table)

        except Exception as e:
            abort_with_error(
                "Failed to apply patch",
                f"Workpad preserved for manual inspection: {pad_id}\n{e}"
            )

        # Step 6: Run Tests (optional)
        if not no_test:
            formatter.print_subheader("Test Execution")
            formatter.print_info(f"Running {target} test suite")

            if target == 'fast':
                tests = [
                    TestConfig(name="unit-tests", cmd="python -m pytest tests/ -q --tb=short", timeout=60),
                ]
            else:
                tests = [
                    TestConfig(name="unit-tests", cmd="python -m pytest tests/ -q --tb=short", timeout=60),
                    TestConfig(name="integration", cmd="python -m pytest tests/integration/ -q --tb=short", timeout=120),
                ]

            test_orchestrator = get_test_orchestrator()
            results = test_orchestrator.run_tests_sync(pad_id, tests, parallel=True)

            results_table = formatter.table(headers=["Test", "Status", "Duration", "Notes"])
            all_passed = True
            for result in results:
                is_passed = result.status.value == "passed"
                status_color = theme.get_status_color(result.status.value)
                status_icon = theme.get_status_icon(result.status.value)
                duration_s = result.duration_ms / 1000
                notes = (result.stdout or result.stderr or "").split('\n')
                summary_note = next((line for line in notes if line.strip()), "")
                results_table.add_row(
                    result.name,
                    f"[{status_color}]{status_icon} {result.status.value.upper()}[/{status_color}]",
                    f"{duration_s:.1f}s",
                    summary_note[:80]
                )
                if not is_passed:
                    all_passed = False

            formatter.console.print(results_table)

            summary = test_orchestrator.get_summary(results)
            status_color = theme.get_status_color(summary['status'])
            summary_panel = f"""[bold]Total:[/bold] {summary['total']}
[bold]Passed:[/bold] [green]{summary['passed']}[/green]
[bold]Failed:[/bold] [red]{summary['failed']}[/red]
[bold]Skipped:[/bold] {summary['skipped']}
[bold]Status:[/bold] [{status_color}]{summary['status'].upper()}[/{status_color}]"""
            formatter.print_info_panel(summary_panel, title="Test Summary")

            if all_passed and not no_promote:
                formatter.print_success("All tests passed! Promoting to trunk...")

                try:
                    commit_hash = git_engine.promote_workpad(pad_id)
                    formatter.print_success_panel(
                        f"Commit: {commit_hash}\nBranch: {repo.trunk_branch}",
                        title="Promotion Complete"
                    )

                    total_cost = plan_response.cost_usd + patch_response.cost_usd
                    formatter.print_info(f"Total AI cost: ${total_cost:.4f}")

                except Exception as e:
                    abort_with_error(
                        "Promotion failed",
                        f"Workpad preserved: {pad_id}\nManually promote with: evogitctl pad promote {pad_id}\n{e}"
                    )

            elif not all_passed:
                formatter.print_warning(
                    f"Tests failed. Workpad preserved for fixes: {pad_id}"
                )
                formatter.print_info(f"View diff: evogitctl pad diff {pad_id}")
                formatter.print_info(f"Run tests: evogitctl test run {pad_id}")
                formatter.print_info(f"Promote manually: evogitctl pad promote {pad_id}")
                raise click.Abort()

            else:
                formatter.print_success(
                    "Tests passed but auto-promote disabled. Promote manually when ready."
                )
                formatter.print_info(f"Workpad: {pad_id}")
                formatter.print_info(f"Promote manually: evogitctl pad promote {pad_id}")

        else:
            formatter.print_warning(
                f"Tests skipped. Workpad ready for manual testing: {pad_id}"
            )
            formatter.print_info(f"Run tests: evogitctl test run {pad_id}")
            formatter.print_info(f"View diff: evogitctl pad diff {pad_id}")
            if not no_promote:
                formatter.print_info(f"Promote: evogitctl pad promote {pad_id}")

    except click.Abort:
        raise
    except Exception as e:
        logger.exception("Pair loop failed")
        abort_with_error(
            "Unexpected error during pair session",
            f"Workpad may be in inconsistent state: {pad_id if 'pad_id' in locals() else 'N/A'}\n{e}"
        )
