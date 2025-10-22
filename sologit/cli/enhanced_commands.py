"""
Enhanced CLI commands with Heaven Interface formatting and state management.

Wraps existing commands with Rich formatting and StateManager integration.
"""

import click
from pathlib import Path
from typing import Optional, Callable, TypeVar
from datetime import datetime
import uuid

from sologit.engines.git_engine import GitEngine, GitEngineError
from sologit.engines.patch_engine import PatchEngine
from sologit.engines.test_orchestrator import TestOrchestrator
from sologit.ui.formatter import RichFormatter
from sologit.ui.graph import CommitGraphRenderer
from sologit.state.manager import StateManager
from sologit.state.schema import CommitNode
from sologit.utils.logger import get_logger

logger = get_logger(__name__)

StageResult = TypeVar("StageResult")


class EnhancedCLI:
    """Enhanced CLI with Rich formatting and state management."""
    
    def __init__(self):
        self.formatter = RichFormatter()
        self.state_manager = StateManager()
        self.graph_renderer = CommitGraphRenderer(self.formatter.console)
        
        # Engines
        self._git_engine: Optional[GitEngine] = None
        self._patch_engine: Optional[PatchEngine] = None
        self._test_orchestrator: Optional[TestOrchestrator] = None
    
    @property
    def git_engine(self) -> GitEngine:
        if self._git_engine is None:
            self._git_engine = GitEngine()
        return self._git_engine
    
    @property
    def patch_engine(self) -> PatchEngine:
        if self._patch_engine is None:
            self._patch_engine = PatchEngine(self.git_engine)
        return self._patch_engine
    
    @property
    def test_orchestrator(self) -> TestOrchestrator:
        if self._test_orchestrator is None:
            self._test_orchestrator = TestOrchestrator(self.git_engine)
        return self._test_orchestrator

    def _initialize_repository_state(self, repo) -> None:
        """Persist repository metadata and set active context."""

        self.state_manager.create_repository(
            repo_id=repo.id,
            name=repo.name,
            path=str(repo.path)
        )
        self.state_manager.set_active_context(repo_id=repo.id)

    def _load_initial_commit_history(self, repo) -> None:
        """Load initial commit history into the state manager."""

        try:
            import git

            git_repo = git.Repo(repo.path)
            for commit in list(git_repo.iter_commits())[:20]:
                commit_node = CommitNode(
                    sha=commit.hexsha,
                    short_sha=commit.hexsha[:8],
                    message=commit.message,
                    author=commit.author.name,
                    timestamp=datetime.fromtimestamp(commit.committed_date).isoformat(),
                    parent_sha=commit.parents[0].hexsha if commit.parents else None,
                    is_trunk=True,
                )
                self.state_manager.add_commit(repo.id, commit_node)
        except Exception as exc:  # pragma: no cover - best effort
            logger.warning(f"Could not load commit history: {exc}")

    # Repository Commands

    def repo_init(self, zip_file: Optional[str] = None, git_url: Optional[str] = None,
                  name: Optional[str] = None) -> None:
        """Initialize a new repository with progress feedback."""

        repo = None
        progress = None
        overall_task: Optional[int] = None

        try:
            with self.formatter.progress("Repository initialization") as progress_ctx:
                progress = progress_ctx
                overall_task = progress.add_task("Repository setup", total=100)

                def run_stage(description: str, advance: int, operation: Callable[[], StageResult]) -> StageResult:
                    stage_task = progress.add_task(description, total=None)
                    progress.update(overall_task, description=description)
                    success = False
                    try:
                        result = operation()
                        success = True
                        return result
                    finally:
                        progress.remove_task(stage_task)
                        if success and advance:
                            progress.advance(overall_task, advance)

                if zip_file:
                    zip_path = Path(zip_file)
                    zip_data = run_stage(
                        "Loading archive from disk",
                        25,
                        lambda: zip_path.read_bytes(),
                    )

                    if not name:
                        name = zip_path.stem

                    repo_id = run_stage(
                        "Importing files & creating initial commit",
                        35,
                        lambda: self.git_engine.init_from_zip(zip_data, name),
                    )
                else:
                    if not name:
                        name = Path(git_url).stem.replace('.git', '')

                    repo_id = run_stage(
                        "Cloning remote repository",
                        60,
                        lambda: self.git_engine.init_from_git(git_url, name),
                    )

                repo = run_stage(
                    "Fetching repository metadata",
                    15,
                    lambda: self.git_engine.get_repo(repo_id),
                )

                run_stage(
                    "Recording repository in state store",
                    15,
                    lambda: self._initialize_repository_state(repo),
                )

                run_stage(
                    "Loading recent commit history",
                    10,
                    lambda: self._load_initial_commit_history(repo),
                )

                progress.update(
                    overall_task,
                    description="[green]Repository ready",
                    completed=100,
                )

        except GitEngineError as exc:
            if progress is not None and overall_task is not None:
                progress.update(overall_task, description="[red]Initialization failed")
            self.formatter.print_error(f"Failed to initialize repository: {exc}")
            raise click.Abort()

        # Print success summary
        if repo is None:
            return

        self.formatter.print_success("Repository initialized successfully!")

        content = f"""[bold]Repository ID:[/bold] {repo.id}
[bold]Name:[/bold] {repo.name}
[bold]Path:[/bold] {repo.path}
[bold]Trunk Branch:[/bold] {repo.trunk_branch}"""
        
        self.formatter.print_panel(content, title="Repository Details")
        
        self.formatter.print_info("\nNext steps:")
        self.formatter.console.print("  1. Create a workpad: [cyan]evogitctl pad create \"<title>\"[/cyan]")
        self.formatter.console.print("  2. Or start AI pairing: [cyan]evogitctl pair \"<task>\"[/cyan]")
    
    def repo_list(self) -> None:
        """List all repositories."""
        repos = self.state_manager.list_repositories()
        
        if not repos:
            self.formatter.print_warning("No repositories found.")
            self.formatter.print_info("Initialize one with: evogitctl repo init --zip <file>")
            return
        
        table = self.formatter.table(title="📁 Repositories", headers=["ID", "Name", "Path", "Workpads", "Created"])
        
        active_repo = self.state_manager.get_active_context()['repo_id']
        
        for repo in repos:
            is_active = repo.repo_id == active_repo
            repo_id_display = f"[bold]{repo.repo_id}[/bold]" if is_active else repo.repo_id
            if is_active:
                repo_id_display += " *"
            
            table.add_row(
                repo_id_display,
                repo.name,
                repo.path,
                str(len(repo.workpads)),
                self.formatter.format_timestamp(repo.created_at)
            )
        
        self.formatter.console.print(table)
        
        if active_repo:
            self.formatter.console.print(f"\n* Active repository: [bold]{active_repo}[/bold]")
    
    def repo_info(self, repo_id: str) -> None:
        """Show detailed repository information."""
        repo = self.state_manager.get_repository(repo_id)
        
        if not repo:
            self.formatter.print_error(f"Repository not found: {repo_id}")
            raise click.Abort()
        
        # Repository details panel
        content = f"""[bold]Repository ID:[/bold] {repo.repo_id}
[bold]Name:[/bold] {repo.name}
[bold]Path:[/bold] {repo.path}
[bold]Trunk Branch:[/bold] {repo.trunk_branch}
[bold]Total Workpads:[/bold] {len(repo.workpads)}
[bold]Total Commits:[/bold] {repo.total_commits}
[bold]Created:[/bold] {self.formatter.format_timestamp(repo.created_at)}
[bold]Updated:[/bold] {self.formatter.format_timestamp(repo.updated_at)}"""
        
        self.formatter.print_panel(content, title=f"Repository: {repo.name}")
        
        # Show commit graph
        commits = self.state_manager.get_commits(repo_id, limit=10)
        if commits:
            self.formatter.print("\n")
            self.formatter.print_header("Recent Commits")
            self.graph_renderer.render_graph(commits, max_lines=10)
        
        # Show active workpads
        workpads = self.state_manager.list_workpads(repo_id)
        active_workpads = [w for w in workpads if w.status in ['active', 'testing']]
        
        if active_workpads:
            self.formatter.print("\n")
            self.formatter.print_header(f"Active Workpads ({len(active_workpads)})")
            
            table = self.formatter.table(headers=["ID", "Title", "Status", "Tests", "Created"])
            for wp in active_workpads[:5]:
                status_icon = self.formatter.theme_obj.get_status_icon(wp.status)
                status_color = self.formatter.theme_obj.get_status_color(wp.status)
                
                table.add_row(
                    wp.workpad_id[:8],
                    wp.title,
                    f"[{status_color}]{status_icon} {wp.status}[/{status_color}]",
                    str(len(wp.test_runs)),
                    self.formatter.format_timestamp(wp.created_at)
                )
            
            self.formatter.console.print(table)
    
    # Workpad Commands
    
    def pad_create(self, title: str, repo_id: Optional[str] = None) -> None:
        """Create a new workpad."""
        # Determine repo_id
        if not repo_id:
            context = self.state_manager.get_active_context()
            repo_id = context['repo_id']
            
            if not repo_id:
                repos = self.state_manager.list_repositories()
                if len(repos) == 1:
                    repo_id = repos[0].repo_id
                else:
                    self.formatter.print_error("No active repository. Specify with --repo or set active repo.")
                    raise click.Abort()
        
        with self.formatter.create_progress() as progress:
            task = progress.add_task("[cyan]Creating workpad...", total=100)
            
            try:
                # Create workpad in git engine
                progress.update(task, advance=50)
                workpad = self.git_engine.create_workpad(repo_id, title)
                
                # Create state entry
                progress.update(task, advance=25, description="[cyan]Updating state...")
                self.state_manager.create_workpad(
                    workpad_id=workpad.id,
                    repo_id=repo_id,
                    title=title,
                    branch_name=workpad.branch_name,
                    base_commit=workpad.base_commit_sha
                )
                
                # Set as active
                self.state_manager.set_active_context(workpad_id=workpad.id)
                
                progress.update(task, advance=25, description="[green]Complete!")
            
            except Exception as e:
                progress.stop()
                self.formatter.print_error(f"Failed to create workpad: {e}")
                raise click.Abort()
        
        # Show success
        self.formatter.print_success(f"Workpad created: {title}")
        
        content = f"""[bold]Workpad ID:[/bold] {workpad.id}
[bold]Title:[/bold] {title}
[bold]Branch:[/bold] {workpad.branch_name}
[bold]Base Commit:[/bold] {workpad.base_commit_sha[:8]}
[bold]Status:[/bold] Active"""
        
        self.formatter.print_panel(content, title="Workpad Details")
        
        self.formatter.print_info("\nNext steps:")
        self.formatter.console.print("  1. Apply patches: [cyan]evogitctl pad apply-patch[/cyan]")
        self.formatter.console.print("  2. Run tests: [cyan]evogitctl test run[/cyan]")
        self.formatter.console.print("  3. Or use AI: [cyan]evogitctl pair \"<task>\"[/cyan]")
    
    def pad_list(self, repo_id: Optional[str] = None) -> None:
        """List workpads."""
        if not repo_id:
            context = self.state_manager.get_active_context()
            repo_id = context['repo_id']
        
        workpads = self.state_manager.list_workpads(repo_id)
        
        if not workpads:
            self.formatter.print_warning("No workpads found.")
            self.formatter.print_info("Create one with: evogitctl pad create \"<title>\"")
            return
        
        table = self.formatter.table(
            title="Workpads", 
            headers=["ID", "Title", "Status", "Branch", "Patches", "Tests", "Created"]
        )
        
        active_workpad = self.state_manager.get_active_context()['workpad_id']
        
        for wp in workpads[:20]:  # Limit display
            is_active = wp.workpad_id == active_workpad
            wp_id_display = f"[bold]{wp.workpad_id[:8]}[/bold]" if is_active else wp.workpad_id[:8]
            if is_active:
                wp_id_display += " *"
            
            status_icon = self.formatter.theme_obj.get_status_icon(wp.status)
            status_color = self.formatter.theme_obj.get_status_color(wp.status)
            
            table.add_row(
                wp_id_display,
                wp.title[:30],
                f"[{status_color}]{status_icon} {wp.status}[/{status_color}]",
                wp.branch_name,
                str(wp.patches_applied),
                str(len(wp.test_runs)),
                self.formatter.format_timestamp(wp.created_at)
            )
        
        self.formatter.console.print(table)
        
        if active_workpad:
            self.formatter.console.print(f"\n* Active workpad: [bold]{active_workpad[:8]}[/bold]")
    
    def pad_info(self, workpad_id: str) -> None:
        """Show detailed workpad information."""
        workpad = self.state_manager.get_workpad(workpad_id)
        
        if not workpad:
            self.formatter.print_error(f"Workpad not found: {workpad_id}")
            raise click.Abort()
        
        # Print workpad summary
        self.formatter.print_workpad_summary(workpad.__dict__)
        
        # Show test runs
        test_runs = self.state_manager.list_test_runs(workpad_id)
        if test_runs:
            self.formatter.print("\n")
            self.formatter.print_header("Test Runs")
            
            table = self.formatter.table(headers=["ID", "Target", "Status", "Pass/Fail", "Duration", "Started"])
            for run in test_runs[:5]:
                status_icon = self.formatter.theme_obj.get_status_icon(run.status)
                status_color = self.formatter.theme_obj.get_status_color(run.status)
                
                table.add_row(
                    run.run_id[:8],
                    run.target,
                    f"[{status_color}]{status_icon} {run.status}[/{status_color}]",
                    f"{run.passed}/{run.total_tests}",
                    self.formatter.format_duration(run.duration_ms),
                    self.formatter.format_timestamp(run.started_at)
                )
            
            self.formatter.console.print(table)
        
        # Show AI operations
        ai_ops = self.state_manager.list_ai_operations(workpad_id)
        if ai_ops:
            self.formatter.print("\n")
            self.formatter.print_header("AI Operations")
            
            table = self.formatter.table(headers=["ID", "Type", "Model", "Status", "Cost", "Started"])
            for op in ai_ops[:5]:
                status_icon = self.formatter.theme_obj.get_status_icon(op.status)
                status_color = self.formatter.theme_obj.get_status_color(op.status)
                
                table.add_row(
                    op.operation_id[:8],
                    op.operation_type,
                    op.model,
                    f"[{status_color}]{status_icon} {op.status}[/{status_color}]",
                    f"${op.cost_usd:.4f}",
                    self.formatter.format_timestamp(op.started_at)
                )
            
            self.formatter.console.print(table)


# Global CLI instance
enhanced_cli = EnhancedCLI()
