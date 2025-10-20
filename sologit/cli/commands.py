
"""
Command implementations for Solo Git CLI.

Phase 1: Repository and workpad management.
Phase 4: Heaven Interface integration with Rich formatting.
"""

import click
from pathlib import Path
from typing import List, Optional, Tuple

from sologit.config.manager import ConfigManager
from sologit.engines.git_engine import GitEngine, GitEngineError
from sologit.engines.patch_engine import PatchEngine
from sologit.engines.test_orchestrator import TestOrchestrator, TestConfig
from sologit.workflows.ci_orchestrator import CIOrchestrator
from sologit.workflows.rollback_handler import RollbackHandler
from sologit.state.manager import StateManager
from sologit.utils.logger import get_logger
from sologit.ui.formatter import RichFormatter

logger = get_logger(__name__)

# Initialize Rich formatter
formatter = RichFormatter()


# Initialize engines (singleton pattern)
_git_engine: Optional[GitEngine] = None
_patch_engine: Optional[PatchEngine] = None
_test_orchestrator: Optional[TestOrchestrator] = None


def _tests_from_config_entries(entries: List[dict], default_timeout: int) -> List[TestConfig]:
    """Convert config entries to TestConfig objects."""
    tests: List[TestConfig] = []

    for entry in entries or []:
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

        timeout = int(entry.get('timeout', default_timeout)) if entry.get('timeout') is not None else default_timeout
        depends_on = entry.get('depends_on', []) or []

        tests.append(TestConfig(name=name, cmd=cmd, timeout=timeout, depends_on=depends_on))

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
        _test_orchestrator = TestOrchestrator(get_git_engine())
    return _test_orchestrator


@click.group()
def repo():
    """Repository management commands."""
    pass


@repo.command('init')
@click.option('--zip', 'zip_file', type=click.Path(exists=True), help='Initialize from zip file')
@click.option('--git', 'git_url', type=str, help='Initialize from Git URL')
@click.option('--name', type=str, help='Repository name (optional)')
def repo_init(zip_file: Optional[str], git_url: Optional[str], name: Optional[str]):
    """Initialize a new repository from zip file or Git URL."""
    if not zip_file and not git_url:
        click.echo("❌ Error: Must provide either --zip or --git", err=True)
        raise click.Abort()
    
    if zip_file and git_url:
        click.echo("❌ Error: Cannot provide both --zip and --git", err=True)
        raise click.Abort()
    
    git_engine = get_git_engine()
    
    try:
        if zip_file:
            # Read zip file
            zip_path = Path(zip_file)
            zip_data = zip_path.read_bytes()
            
            # Derive name from filename if not provided
            if not name:
                name = zip_path.stem
            
            click.echo(f"🔄 Initializing repository from zip: {zip_path.name}")
            repo_id = git_engine.init_from_zip(zip_data, name)
            
        else:  # git_url
            # Derive name from URL if not provided
            if not name:
                name = Path(git_url).stem.replace('.git', '')
            
            click.echo(f"🔄 Cloning repository from: {git_url}")
            repo_id = git_engine.init_from_git(git_url, name)
        
        repo = git_engine.get_repo(repo_id)
        click.echo(f"\n✅ Repository initialized!")
        click.echo(f"   Repo ID: {repo.id}")
        click.echo(f"   Name: {repo.name}")
        click.echo(f"   Path: {repo.path}")
        click.echo(f"   Trunk: {repo.trunk_branch}")
        
    except GitEngineError as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@repo.command('list')
def repo_list():
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
def repo_info(repo_id: str):
    """Show repository information."""
    git_engine = get_git_engine()
    repo = git_engine.get_repo(repo_id)
    
    if not repo:
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
def pad():
    """Workpad management commands."""
    pass


@pad.command('create')
@click.argument('title')
@click.option('--repo', 'repo_id', type=str, help='Repository ID (required if multiple repos)')
def pad_create(title: str, repo_id: Optional[str]):
    """Create a new workpad."""
    git_engine = get_git_engine()
    
    # If no repo_id, try to auto-select
    if not repo_id:
        repos = git_engine.list_repos()
        if len(repos) == 0:
            click.echo("❌ No repositories found. Initialize a repository first.", err=True)
            raise click.Abort()
        elif len(repos) == 1:
            repo_id = repos[0].id
            click.echo(f"🔄 Using repository: {repos[0].name} ({repo_id})")
        else:
            click.echo("❌ Multiple repositories found. Please specify --repo", err=True)
            raise click.Abort()
    
    try:
        click.echo(f"🔄 Creating workpad: {title}")
        pad_id = git_engine.create_workpad(repo_id, title)
        
        workpad = git_engine.get_workpad(pad_id)
        click.echo(f"\n✅ Workpad created!")
        click.echo(f"   Pad ID: {workpad.id}")
        click.echo(f"   Title: {workpad.title}")
        click.echo(f"   Branch: {workpad.branch_name}")
        click.echo(f"   Base: main")
        
    except GitEngineError as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@pad.command('list')
@click.option('--repo', 'repo_id', type=str, help='Filter by repository ID')
def pad_list(repo_id: Optional[str]):
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
def pad_info(pad_id: str):
    """Show workpad information."""
    git_engine = get_git_engine()
    workpad = git_engine.get_workpad(pad_id)
    
    if not workpad:
        click.echo(f"❌ Workpad {pad_id} not found", err=True)
        raise click.Abort()
    
    click.echo(f"Workpad: {workpad.id}")
    click.echo(f"Title: {workpad.title}")
    click.echo(f"Repo: {workpad.repo_id}")
    click.echo(f"Branch: {workpad.branch_name}")
    click.echo(f"Status: {workpad.status}")
    click.echo(f"Created: {workpad.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    click.echo(f"Checkpoints: {len(workpad.checkpoints)}")
    
    if workpad.checkpoints:
        click.echo("\nCheckpoints:")
        for cp in workpad.checkpoints:
            click.echo(f"  - {cp}")
    
    if workpad.test_status:
        click.echo(f"\nLast Test: {workpad.test_status}")


@pad.command('promote')
@click.argument('pad_id')
def pad_promote(pad_id: str):
    """Promote workpad to trunk (fast-forward merge)."""
    git_engine = get_git_engine()
    
    workpad = git_engine.get_workpad(pad_id)
    if not workpad:
        click.echo(f"❌ Workpad {pad_id} not found", err=True)
        raise click.Abort()
    
    # Check if can promote
    if not git_engine.can_promote(pad_id):
        click.echo("❌ Cannot promote: not fast-forward-able", err=True)
        click.echo("   Trunk has diverged. Manual merge required.", err=True)
        raise click.Abort()
    
    try:
        click.echo(f"🔄 Promoting workpad: {workpad.title}")
        commit_hash = git_engine.promote_workpad(pad_id)
        
        click.echo(f"\n✅ Workpad promoted to trunk!")
        click.echo(f"   Commit: {commit_hash}")
        click.echo(f"   Branch deleted: {workpad.branch_name}")
        click.echo(f"   Trunk updated: main @ {commit_hash}")
        
    except GitEngineError as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@pad.command('diff')
@click.argument('pad_id')
def pad_diff(pad_id: str):
    """Show diff between workpad and trunk."""
    git_engine = get_git_engine()
    
    workpad = git_engine.get_workpad(pad_id)
    if not workpad:
        click.echo(f"❌ Workpad {pad_id} not found", err=True)
        raise click.Abort()
    
    try:
        diff = git_engine.get_diff(pad_id)
        if diff:
            click.echo(diff)
        else:
            click.echo("No changes.")
    except GitEngineError as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@click.group()
def test():
    """Test execution commands."""
    pass


@test.command('run')
@click.argument('pad_id')
@click.option('--target', type=click.Choice(['fast', 'full']), default='fast', help='Test target')
@click.option('--parallel/--sequential', default=True, help='Parallel execution')
def test_run(pad_id: str, target: str, parallel: bool):
    """Run tests in Docker sandbox."""
    git_engine = get_git_engine()
    test_orchestrator = get_test_orchestrator()
    
    workpad = git_engine.get_workpad(pad_id)
    if not workpad:
        click.echo(f"❌ Workpad {pad_id} not found", err=True)
        raise click.Abort()
    
    # Define test configurations (hardcoded for now, will load from evogit.yaml later)
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
        # Show test info panel
        info = f"""[bold]Workpad:[/bold] {workpad.title}
[bold]Tests:[/bold] {len(tests)}
[bold]Mode:[/bold] {'Parallel' if parallel else 'Sequential'}
[bold]Target:[/bold] {target}"""
        formatter.print_panel(info, title="🧪 Test Execution")
        
        # Run tests with progress indicator
        with formatter.create_progress() as progress:
            task = progress.add_task(f"Running {target} tests...", total=len(tests))
            
            # Note: We're using sync version here for simplicity
            # In production, we'd stream results and update progress
            results = test_orchestrator.run_tests_sync(pad_id, tests, parallel)
            progress.update(task, completed=len(tests))
        
        formatter.console.print()
        
        # Display results table
        table = formatter.table(headers=["Test", "Status", "Duration", "Output"])
        
        for result in results:
            status_icon = "✅" if result.status.value == "passed" else "❌" if result.status.value == "failed" else "⏭️"
            status_text = f"{status_icon} {result.status.value}"
            duration_s = result.duration_ms / 1000
            
            # Truncate output
            output = result.stdout[:50] + "..." if len(result.stdout) > 50 else result.stdout
            output = output.replace("\n", " ")
            
            table.add_row(
                result.name,
                status_text,
                f"{duration_s:.2f}s",
                output if result.status.value != "passed" else ""
            )
        
        formatter.console.print(table)
        
        # Summary panel
        summary = test_orchestrator.get_summary(results)
        status_color = "green" if summary['status'] == 'passed' else "red"
        summary_text = f"""[bold]Total:[/bold] {summary['total']}
[bold]Passed:[/bold] [green]{summary['passed']}[/green]
[bold]Failed:[/bold] [red]{summary['failed']}[/red]
[bold]Status:[/bold] [{status_color}]{summary['status'].upper()}[/{status_color}]"""
        
        formatter.print_panel(summary_text, title="📊 Test Summary")
        
        # Update workpad test status
        workpad.test_status = summary['status']
        
        if summary['status'] == 'passed':
            formatter.print_success("All tests passed! Ready to promote.")
        else:
            formatter.print_error("Some tests failed. Fix issues before promoting.")
        
    except Exception as e:
        formatter.print_error(f"Test execution failed: {e}")
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
def pad_auto_merge(ctx, pad_id: str, target: str, no_auto_promote: bool, test_overrides: Tuple[str, ...]):
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
    if not workpad:
        click.echo(f"❌ Workpad {pad_id} not found", err=True)
        raise click.Abort()

    config_manager: ConfigManager = ctx.obj.get('config') if ctx and ctx.obj else ConfigManager()
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
        click.echo(f"🚀 Starting auto-merge workflow for: {workpad.title}")
        click.echo(f"   Target: {target}")
        click.echo(f"   Auto-promote: {not no_auto_promote}\n")
        
        # Execute workflow
        result = workflow.execute(
            pad_id,
            tests,
            parallel=True,
            auto_promote=not no_auto_promote,
            target=target
        )
        
        # Display formatted result
        click.echo(workflow.format_result(result))
        
        # Exit with appropriate code
        if not result.success and result.promotion_decision and not result.promotion_decision.can_promote:
            raise click.Abort()
    
    except Exception as e:
        click.echo(f"❌ Auto-merge failed: {e}", err=True)
        raise click.Abort()


@pad.command('evaluate')
@click.argument('pad_id')
def pad_evaluate(pad_id: str):
    """
    Evaluate promotion gate without promoting (Phase 3).
    
    Shows whether a workpad is ready to be promoted based on configured rules.
    """
    from sologit.workflows.promotion_gate import PromotionGate, PromotionRules
    
    git_engine = get_git_engine()
    
    workpad = git_engine.get_workpad(pad_id)
    if not workpad:
        click.echo(f"❌ Workpad {pad_id} not found", err=True)
        raise click.Abort()
    
    # Configure rules
    rules = PromotionRules(
        require_tests=True,
        require_all_tests_pass=True,
        require_fast_forward=True
    )
    
    # Create gate
    gate = PromotionGate(git_engine, rules)
    
    try:
        click.echo(f"🚦 Evaluating promotion gate for: {workpad.title}\n")
        
        # Evaluate (without test results for now)
        # In full implementation, would load cached test results
        decision = gate.evaluate(pad_id, test_analysis=None)
        
        # Display decision
        click.echo(gate.format_decision(decision))
        
        # Exit code based on decision
        if not decision.can_promote:
            raise click.Abort()
    
    except Exception as e:
        click.echo(f"❌ Evaluation failed: {e}", err=True)
        raise click.Abort()


@click.group()
def ci():
    """CI and smoke test commands (Phase 3)."""
    pass


@ci.command('smoke')
@click.argument('repo_id')
@click.option('--commit', help='Commit hash to test (default: HEAD)')
def ci_smoke(repo_id: str, commit: Optional[str]):
    """
    Run smoke tests for a commit (Phase 3).
    
    This simulates post-merge CI smoke tests.
    """
    from sologit.workflows.ci_orchestrator import CIOrchestrator
    
    git_engine = get_git_engine()
    test_orchestrator = get_test_orchestrator()
    
    repo = git_engine.get_repo(repo_id)
    if not repo:
        click.echo(f"❌ Repository {repo_id} not found", err=True)
        raise click.Abort()
    
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
    
    def progress_callback(message: str):
        click.echo(f"   {message}")
    
    try:
        click.echo(f"🔬 Running smoke tests...")
        click.echo(f"   Repository: {repo_id}")
        click.echo(f"   Commit: {commit[:8]}\n")
        
        # Run smoke tests
        result = orchestrator.run_smoke_tests(
            repo_id,
            commit,
            smoke_tests,
            on_progress=progress_callback
        )
        
        # Display result
        click.echo("\n" + orchestrator.format_result(result))
        
        # Exit code based on result
        if result.is_red:
            raise click.Abort()
    
    except Exception as e:
        click.echo(f"❌ Smoke tests failed: {e}", err=True)
        raise click.Abort()


@ci.command('rollback')
@click.argument('repo_id')
@click.option('--commit', required=True, help='Commit hash to rollback')
@click.option('--recreate-pad/--no-recreate-pad', default=True, help='Recreate workpad for fixes')
def ci_rollback(repo_id: str, commit: str, recreate_pad: bool):
    """
    Manually rollback a commit (Phase 3).
    
    Reverts the specified commit and optionally recreates a workpad.
    """
    from sologit.workflows.rollback_handler import RollbackHandler
    from sologit.workflows.ci_orchestrator import CIResult, CIStatus
    
    git_engine = get_git_engine()
    
    repo = git_engine.get_repo(repo_id)
    if not repo:
        click.echo(f"❌ Repository {repo_id} not found", err=True)
        raise click.Abort()
    
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
        click.echo(f"🔄 Rolling back commit...")
        click.echo(f"   Repository: {repo_id}")
        click.echo(f"   Commit: {commit[:8]}")
        click.echo(f"   Recreate workpad: {recreate_pad}\n")
        
        # Perform rollback
        result = handler.handle_failed_ci(fake_ci_result, recreate_pad)
        
        # Display result
        click.echo(handler.format_result(result))
        
        # Exit code
        if not result.success:
            raise click.Abort()
    
    except Exception as e:
        click.echo(f"❌ Rollback failed: {e}", err=True)
        raise click.Abort()


@test.command('analyze')
@click.argument('pad_id')
def test_analyze(pad_id: str):
    """
    Analyze test failures for a workpad (Phase 3).
    
    Shows failure patterns and suggested fixes.
    """
    from sologit.analysis.test_analyzer import TestAnalyzer
    
    git_engine = get_git_engine()
    test_orchestrator = get_test_orchestrator()
    
    workpad = git_engine.get_workpad(pad_id)
    if not workpad:
        click.echo(f"❌ Workpad {pad_id} not found", err=True)
        raise click.Abort()
    
    # Check if tests have been run
    # In a full implementation, we'd cache test results
    # For now, prompt user to run tests first
    
    click.echo(f"⚠️ Test analysis requires recent test results")
    click.echo(f"   Run 'sologit test run {pad_id}' first")
    click.echo(f"\nNote: In Phase 3, test results will be cached and analyzed automatically")


# ============================================================================
# Phase 4: Complete Pair Loop Implementation
# ============================================================================

def execute_pair_loop(ctx, prompt: str, repo_id: Optional[str], title: Optional[str],
                      no_test: bool, no_promote: bool, target: str):
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
    config_manager = ctx.obj.get('config')
    
    # Step 1: Select repository
    if not repo_id:
        repos = git_engine.list_repos()
        if len(repos) == 0:
            click.echo("❌ No repositories found. Initialize a repository first:", err=True)
            click.echo("   evogitctl repo init --zip app.zip")
            raise click.Abort()
        elif len(repos) == 1:
            repo_id = repos[0].id
            click.echo(f"📦 Using repository: {repos[0].name} ({repo_id})")
        else:
            click.echo("❌ Multiple repositories found. Please specify --repo", err=True)
            click.echo("\nAvailable repositories:")
            for repo in repos:
                click.echo(f"  • {repo.id} - {repo.name}")
            raise click.Abort()
    
    # Validate repository exists
    repo = git_engine.get_repo(repo_id)
    if not repo:
        click.echo(f"❌ Repository {repo_id} not found", err=True)
        raise click.Abort()
    
    # Step 2: Create workpad
    if not title:
        # Derive title from prompt (first few words, sanitized)
        words = prompt.split()[:5]
        title = '-'.join(words).lower()
        # Remove special characters
        title = ''.join(c if c.isalnum() or c == '-' else '-' for c in title)
        title = '-'.join(filter(None, title.split('-')))  # Remove empty parts
    
    click.echo(f"\n🚀 Starting pair programming session")
    click.echo(f"   Repository: {repo.name}")
    click.echo(f"   Prompt: {prompt}")
    click.echo(f"   Title: {title}\n")
    
    try:
        click.echo("📝 Creating workpad...")
        pad_id = git_engine.create_workpad(repo_id, title)
        workpad = git_engine.get_workpad(pad_id)
        click.echo(f"✅ Workpad created: {pad_id}")
        
        # Step 3: AI Planning
        click.echo(f"\n🤖 AI Planning (using {config_manager.config.models.planning_model})...")
        start_time = time.time()
        
        orchestrator = AIOrchestrator(config_manager)
        
        # Get repo context (file tree)
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
        click.echo(f"✅ Plan generated in {planning_time:.1f}s (cost: ${plan_response.cost_usd:.4f})")
        click.echo(f"   Model: {plan_response.model_used}")
        click.echo(f"   Complexity: {plan_response.complexity.score:.2f}")
        
        # Display plan
        plan = plan_response.plan
        click.echo(f"\n📋 Implementation Plan:")
        click.echo(f"   Description: {plan.description}")
        click.echo(f"   Files to modify: {', '.join(plan.files_to_modify) if plan.files_to_modify else 'None'}")
        click.echo(f"   Files to create: {', '.join(plan.files_to_create) if plan.files_to_create else 'None'}")
        if plan.test_strategy:
            click.echo(f"   Test strategy: {plan.test_strategy}")
        
        # Step 4: Generate Patch
        click.echo(f"\n💻 Generating code (using {config_manager.config.models.coding_model})...")
        start_time = time.time()
        
        patch_response = orchestrator.generate_patch(
            plan=plan,
            repo_context=context
        )
        
        coding_time = time.time() - start_time
        click.echo(f"✅ Patch generated in {coding_time:.1f}s (cost: ${patch_response.cost_usd:.4f})")
        click.echo(f"   Model: {patch_response.model_used}")
        
        patch = patch_response.patch
        if patch.description:
            click.echo(f"   Description: {patch.description}")
        
        # Step 5: Apply Patch
        click.echo(f"\n📦 Applying patch to workpad...")
        patch_engine = get_patch_engine()
        
        try:
            result = patch_engine.apply_patch(pad_id, patch.diff)
            click.echo(f"✅ Patch applied successfully")
            click.echo(f"   Files changed: {result.files_changed}")
            click.echo(f"   Insertions: +{result.insertions}")
            click.echo(f"   Deletions: -{result.deletions}")
            
        except Exception as e:
            click.echo(f"❌ Failed to apply patch: {e}", err=True)
            click.echo(f"\n🔍 Workpad preserved for manual inspection: {pad_id}")
            raise click.Abort()
        
        # Step 6: Run Tests (optional)
        if not no_test:
            click.echo(f"\n🧪 Running {target} tests...")
            
            # Define test configurations
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
            
            # Display results
            click.echo(f"\n📊 Test Results:")
            all_passed = True
            for result in results:
                status_icon = "✅" if result.status.value == "passed" else "❌"
                duration_s = result.duration_ms / 1000
                click.echo(f"   {status_icon} {result.name} ({duration_s:.1f}s)")
                if result.status.value != "passed":
                    all_passed = False
                    # Show first few lines of error
                    error_lines = result.stdout.split('\n')[:5]
                    for line in error_lines:
                        if line.strip():
                            click.echo(f"      {line}")
            
            summary = test_orchestrator.get_summary(results)
            click.echo(f"\n   Summary: {summary['passed']}/{summary['total']} passed")
            
            # Step 7: Auto-promote (optional)
            if all_passed and not no_promote:
                click.echo(f"\n🎉 All tests passed! Auto-promoting to trunk...")
                
                try:
                    commit_hash = git_engine.promote_workpad(pad_id)
                    click.echo(f"✅ Workpad promoted to trunk!")
                    click.echo(f"   Commit: {commit_hash}")
                    click.echo(f"\n🏁 Pair session complete! Changes are now in {repo.trunk_branch}.")
                    
                    # Show total cost
                    total_cost = plan_response.cost_usd + patch_response.cost_usd
                    click.echo(f"\n💰 Total cost: ${total_cost:.4f}")
                    
                except Exception as e:
                    click.echo(f"❌ Promotion failed: {e}", err=True)
                    click.echo(f"\n🔍 Workpad preserved: {pad_id}")
                    click.echo(f"   Manually promote: evogitctl pad promote {pad_id}")
                    raise click.Abort()
            
            elif not all_passed:
                click.echo(f"\n⚠️  Tests failed. Workpad preserved for fixes: {pad_id}")
                click.echo(f"   View diff: evogitctl pad diff {pad_id}")
                click.echo(f"   Run tests: evogitctl test run {pad_id}")
                click.echo(f"   Promote manually: evogitctl pad promote {pad_id}")
                raise click.Abort()
            
            else:  # no_promote flag
                click.echo(f"\n✅ Tests passed but auto-promote disabled")
                click.echo(f"   Workpad: {pad_id}")
                click.echo(f"   Promote manually: evogitctl pad promote {pad_id}")
        
        else:  # no_test flag
            click.echo(f"\n⚠️  Tests skipped. Workpad ready for manual testing: {pad_id}")
            click.echo(f"   Run tests: evogitctl test run {pad_id}")
            click.echo(f"   View diff: evogitctl pad diff {pad_id}")
            if not no_promote:
                click.echo(f"   Promote: evogitctl pad promote {pad_id}")
        
    except click.Abort:
        # Re-raise abort to exit cleanly
        raise
    except Exception as e:
        click.echo(f"\n❌ Unexpected error: {e}", err=True)
        logger.exception("Pair loop failed")
        click.echo(f"\n🔍 Workpad may be in inconsistent state: {pad_id if 'pad_id' in locals() else 'N/A'}")
        raise click.Abort()
