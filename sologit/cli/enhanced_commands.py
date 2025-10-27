"""Enhanced command helpers that wrap core CLI operations with Rich output."""

from __future__ import annotations

from pathlib import Path
from typing import Optional
from datetime import datetime
import uuid
from typing import Callable, Optional, TypeVar

import click

from sologit.engines.git_engine import GitEngine, GitEngineError
from sologit.engines.patch_engine import PatchEngine
from sologit.engines.test_orchestrator import TestOrchestrator
from sologit.state.manager import StateManager
from sologit.ui.formatter import RichFormatter
from sologit.utils.logger import get_logger

logger = get_logger(__name__)


class EnhancedCLI:
    """Enhanced CLI with Rich formatting and state management helpers."""

    def __init__(self, formatter: Optional[RichFormatter] = None) -> None:
        self.formatter = formatter or RichFormatter()
        self.state_manager = StateManager()
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
    
    # Repository Commands
    
    def repo_init(self, zip_file: Optional[str] = None, git_url: Optional[str] = None, 
                  name: Optional[str] = None) -> None:
        """Initialize a new repository."""
        with self.formatter.create_progress() as progress:
            task = progress.add_task("[cyan]Initializing repository...", total=100)
            
            try:
                if zip_file:
                    zip_path = Path(zip_file)
                    zip_data = zip_path.read_bytes()
                    if not name:
                        name = zip_path.stem
                    
                    progress.update(task, advance=30, description="[cyan]Extracting zip...")
                    repo_id = self.git_engine.init_from_zip(zip_data, name)
                    
                else:  # git_url
                    if not name:
                        name = Path(git_url).stem.replace('.git', '')
                    
                    progress.update(task, advance=30, description="[cyan]Cloning repository...")
                    repo_id = self.git_engine.init_from_git(git_url, name)
                
                progress.update(task, advance=40, description="[cyan]Initializing state...")
                
                # Get repo info
                repo = self.git_engine.get_repo(repo_id)
                
                # Create state entry
                self.state_manager.create_repository(
                    repo_id=repo.id,
                    name=repo.name,
                    path=str(repo.path)
                )
                
                # Set as active
                self.state_manager.set_active_context(repo_id=repo.id)
                
                # Get initial commits
                try:
                    import git
                    git_repo = git.Repo(repo.path)
                    for i, commit in enumerate(list(git_repo.iter_commits())[:20]):
                        commit_node = CommitNode(
                            sha=commit.hexsha,
                            short_sha=commit.hexsha[:8],
                            message=commit.message,
                            author=commit.author.name,
                            timestamp=datetime.fromtimestamp(commit.committed_date).isoformat(),
                            parent_sha=commit.parents[0].hexsha if commit.parents else None,
                            is_trunk=True
                        )
                        self.state_manager.add_commit(repo.id, commit_node)
                except Exception as e:
                    logger.warning(f"Could not load commit history: {e}")
                
                progress.update(task, advance=30, description="[green]Complete!")
            
            except GitEngineError as e:
                progress.stop()
                self.formatter.print_error(f"Failed to initialize repository: {e}")
                raise click.Abort()
        
        # Print success summary
        self.formatter.print_success("Repository initialized successfully!")
        
        content = f"""[bold]Repository ID:[/bold] {repo.id}
[bold]Name:[/bold] {repo.name}
[bold]Path:[/bold] {repo.path}
[bold]Trunk Branch:[/bold] {repo.trunk_branch}"""
        
        self.formatter.print_panel(content, title="Repository Details")
        
        self.formatter.print_info("\nNext steps:")
        self.formatter.console.print("  1. Create a workpad: [cyan]evogitctl pad create \"<title>\"[/cyan]")
        self.formatter.console.print("  2. Or start AI pairing: [cyan]evogitctl pair \"<task>\"[/cyan]")
    

    def _run_stage(self, description: str, operation: Callable[[], StageResult]) -> StageResult:
        """Run a stage while emitting progress output."""

        self.formatter.print_info(description)
        return operation()

    def repo_init(
        self,
        zip_file: Optional[str] = None,
        git_url: Optional[str] = None,
        name: Optional[str] = None,
    ) -> None:
        """Initialize a new repository with simple progress output."""

        if not zip_file and not git_url:
            raise click.BadParameter("Provide either zip_file or git_url")

        self.formatter.print_header("Enhanced Repository Initialization")
        repo_id: Optional[str] = None

        try:
            if zip_file:
                zip_path = Path(zip_file)
                if not name:
                    name = zip_path.stem
                archive_bytes = self._run_stage(
                    "Loading archive",
                    lambda: zip_path.read_bytes(),
                )
                repo_id = self._run_stage(
                    "Importing repository contents",
                    lambda: self.git_engine.init_from_zip(archive_bytes, name),
                )
            else:
                if not git_url:
                    raise click.BadParameter("git_url is required when no zip file is provided")
                if not name:
                    base = git_url.rstrip("/").split("/")[-1]
                    if base.endswith(".git"):
                        base = base[:-4]
                    name = base
                repo_id = self._run_stage(
                    "Cloning remote repository",
                    lambda: self.git_engine.init_from_git(git_url, name),
                )

            repo = self._run_stage(
                "Fetching repository metadata",
                lambda: self.git_engine.get_repo(repo_id),
            )
            if repo is None:
                raise GitEngineError("Repository initialization did not return metadata")

            self.state_manager.set_active_context(repo_id=repo.id)
            self.formatter.print_success(
                f"Repository {repo.name} ({repo.id}) initialized at {repo.path}"
            )
        except GitEngineError as exc:
            self.formatter.print_error(
                "Repository Initialization Failed",
                "Solo Git could not complete the initialization process.",
                help_text="Confirm the source path or Git URL is accessible and that you have the necessary credentials.",
                tip="Run the command again with --verbose to inspect git output.",
                details=str(exc),
            )
            raise click.Abort()

    def repo_list(self) -> None:
        """Render repositories tracked by the Git engine."""

        repos = self.git_engine.list_repos()
        if not repos:
            self.formatter.print_info("No repositories available.")
            return

        table = self.formatter.table(headers=["ID", "Name", "Trunk"])
        for repo in repos:
            table.add_row(repo.id, getattr(repo, "name", repo.id), getattr(repo, "trunk_branch", "main"))
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

    def workpad_diff(self, pad_id: str) -> None:
        """Display the diff for a given workpad."""

        workpad = self.git_engine.get_workpad(pad_id)
        if workpad is None:
            self.formatter.print_error("Workpad not found", f"Workpad {pad_id} could not be located.")
            raise click.Abort()

        diff_text = self.git_engine.get_diff(pad_id)
        self.formatter.print_header(f"Diff for {workpad.title}")
        self.formatter.console.print(diff_text)


enhanced_cli = EnhancedCLI()
