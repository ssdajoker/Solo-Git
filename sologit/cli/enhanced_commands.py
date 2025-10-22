"""Enhanced command helpers that wrap core CLI operations with Rich output."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional, TypeVar

import click

from sologit.engines.git_engine import GitEngine, GitEngineError
from sologit.engines.patch_engine import PatchEngine
from sologit.engines.test_orchestrator import TestOrchestrator
from sologit.state.manager import StateManager
from sologit.ui.formatter import RichFormatter
from sologit.utils.logger import get_logger

logger = get_logger(__name__)

StageResult = TypeVar("StageResult")


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
