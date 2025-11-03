from __future__ import annotations

import asyncio
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, List, Optional, Sequence, Tuple

import click
from rich.console import Console

from sologit.config.manager import ConfigManager
from sologit.engines.git_engine import (
    GitEngine,
    GitEngineError,
)
from sologit.engines.patch_engine import PatchEngine
from sologit.engines.test_orchestrator import (
    TestConfig as OrchestratorTestConfig,
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
from sologit.analysis.test_analyzer import TestAnalyzer
from sologit.workflows.auto_merge import AutoMergeWorkflow
from sologit.workflows.promotion_gate import PromotionGate, PromotionRules

logger = get_logger(__name__)

formatter = RichFormatter()


# -- testing shim -------------------------------------------------------------------------

# -- helpers -----------------------------------------------------------------------------

def set_formatter_console(console: Console) -> None:
    """Allow external modules to override the formatter console."""

    formatter.set_console(console)


def abort_with_error(
    message: str,
    details: Optional[str] = None,
    *,
    title: Optional[str] = None,
    help_text: Optional[str] = None,
    tip: Optional[str] = None,
    suggestions: Optional[List[str]] = None,
    docs_url: Optional[str] = None,
) -> None:
    """Display a contextual error message and abort the current command."""

    default_help = help_text or "Use the --help flag to review available options."
    default_tip = tip or "Common fix: double-check CLI arguments and repository context."
    default_suggestions: Iterable[str] = suggestions or (
        "evogitctl --help",
        "evogitctl history --recent",
    )

    formatter.print_error(
        title or "Command Error",
        message,
        help_text=default_help,
        tip=default_tip,
        suggestions=list(default_suggestions),
        docs_url=docs_url or "docs/SETUP.md",
        details=details,
    )
    raise click.Abort()


def _require_workpad(workpad: Any, pad_id: str):
    """Ensure a workpad exists; abort with a descriptive error otherwise."""

    if workpad is None:
        abort_with_error(
            f"Workpad {pad_id} not found",
            title="Workpad Not Found",
            suggestions=[
                "evogitctl pad list",
                f"evogitctl pad create 'new task' --repo <repo-id>",
            ],
        )
    return workpad


_git_engine: Optional[GitEngine] = None
_patch_engine: Optional[PatchEngine] = None
_test_orchestrator: Optional[TestOrchestrator] = None
_config_manager: Optional[ConfigManager] = None
_git_state_sync: Optional[GitStateSync] = None


def _resolve_path_from_env(var_name: str) -> Optional[Path]:
    value = os.environ.get(var_name)
    if not value:
        return None
    return Path(value).expanduser()


def get_config_manager() -> ConfigManager:
    """Return a cached ``ConfigManager`` instance."""

    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_git_engine() -> GitEngine:
    """Return the shared ``GitEngine`` instance respecting environment overrides."""

    global _git_engine
    if _git_engine is None:
        data_dir = _resolve_path_from_env("SOLOGIT_DATA_PATH")
        _git_engine = GitEngine(data_dir=data_dir)
    return _git_engine


def get_patch_engine() -> PatchEngine:
    """Return the singleton ``PatchEngine`` instance."""

    global _patch_engine
    if _patch_engine is None:
        _patch_engine = PatchEngine(get_git_engine())
    return _patch_engine


def get_test_orchestrator() -> TestOrchestrator:
    """Return a configured ``TestOrchestrator`` instance."""

    global _test_orchestrator
    if _test_orchestrator is None:
        config = get_config_manager().config.tests
        log_dir = Path(getattr(config, "log_dir", "~/.sologit/data/test_runs")).expanduser()
        _test_orchestrator = TestOrchestrator(
            get_git_engine(),
            sandbox_image=getattr(config, "sandbox_image", "python:3.11-slim"),
            execution_mode=getattr(config, "execution_mode", "subprocess"),
            log_dir=log_dir,
            formatter=formatter,
        )
    return _test_orchestrator


def get_git_sync() -> GitStateSync:
    """Return the shared ``GitStateSync`` instance."""

    global _git_state_sync
    if _git_state_sync is None:
        state_dir = _resolve_path_from_env("SOLOGIT_STATE_PATH")
        data_dir = _resolve_path_from_env("SOLOGIT_DATA_PATH")
        _git_state_sync = GitStateSync(state_dir=state_dir, data_dir=data_dir)
    return _git_state_sync


def _tests_from_config_entries(
    entries: Optional[Sequence[Any]],
    default_timeout: int,
) -> List[OrchestratorTestConfig]:
    """Convert configuration objects/dicts to orchestrator ``TestConfig`` instances."""

    tests: List[OrchestratorTestConfig] = []
    if not entries:
        return tests

    for entry in entries:
        if isinstance(entry, OrchestratorTestConfig):
            tests.append(entry)
            continue
        if not isinstance(entry, dict):
            logger.warning("Ignoring invalid test entry: %s", entry)
            continue
        name = entry.get("name")
        cmd = entry.get("cmd")
        if not name or not cmd:
            logger.warning("Test entry missing name/cmd: %s", entry)
            continue
        timeout = entry.get("timeout", default_timeout)
        try:
            timeout_value = int(timeout) if timeout is not None else default_timeout
        except (TypeError, ValueError):
            timeout_value = default_timeout
        depends_on = entry.get("depends_on", []) or []
        if not isinstance(depends_on, Iterable) or isinstance(depends_on, (str, bytes)):
            depends_on = []
        tests.append(
            OrchestratorTestConfig(
                name=name,
                cmd=cmd,
                timeout=timeout_value,
                depends_on=list(depends_on),
            )
        )
    return tests


def _parse_test_override(value: str, default_timeout: int) -> OrchestratorTestConfig:
    """Parse the ``NAME=CMD[:TIMEOUT]`` syntax used by ``--test`` overrides."""

    if "=" not in value:
        raise click.BadParameter("Must be in NAME=CMD[:TIMEOUT] format")

    name, remainder = value.split("=", 1)
    name = name.strip()
    remainder = remainder.strip()
    if not name or not remainder:
        raise click.BadParameter("Both name and command must be provided")

    timeout = default_timeout
    cmd = remainder
    if ":" in remainder:
        cmd, timeout_str = remainder.rsplit(":", 1)
        cmd = cmd.strip()
        try:
            timeout = int(timeout_str.strip())
        except ValueError as exc:  # pragma: no cover - defensive, validated above
            raise click.BadParameter("Timeout must be an integer") from exc
    if not cmd:
        raise click.BadParameter("Command cannot be empty")

    return OrchestratorTestConfig(name=name, cmd=cmd, timeout=timeout)


def _format_datetime(value: Any) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    return str(value) if value is not None else "-"


def _status_icon(status: str) -> Tuple[str, str]:
    icons = {
        "active": (theme.icons.success, theme.colors.success),
        "pending": (theme.icons.warning, theme.colors.warning),
        "completed": (theme.icons.success, theme.colors.success),
        "failed": (theme.icons.error, theme.colors.error),
        "archived": (theme.icons.info, theme.colors.text_secondary),
    }
    return icons.get(status.lower(), (theme.icons.info, theme.colors.text_secondary))


def _format_test_status(status: TestStatus) -> str:
    mapping = {
        TestStatus.PASSED: "✅ passed",
        TestStatus.FAILED: "❌ failed",
        TestStatus.ERROR: "⚠️ error",
        TestStatus.TIMEOUT: "⏱️ timeout",
        TestStatus.SKIPPED: "⏭️ skipped",
    }
    return mapping.get(status, f"ℹ {status.value}")


def _fallback_tests(target: str, default_timeout: int) -> List[OrchestratorTestConfig]:
    if target == "fast":
        return [
            OrchestratorTestConfig("unit-tests", "python -m pytest tests/ -q", timeout=default_timeout),
        ]
    return [
        OrchestratorTestConfig("unit-tests", "python -m pytest tests/ -q", timeout=default_timeout),
        OrchestratorTestConfig("integration", "python -m pytest tests/integration/ -q", timeout=default_timeout * 2),
    ]


def _state_result_from_test_result(run_id: str, result: TestResult) -> StateTestResult:
    output = result.stdout or result.stderr or ""
    return StateTestResult(
        test_id=f"{run_id}:{result.name}",
        name=result.name,
        status=result.status.value,
        duration_ms=result.duration_ms,
        output=output,
        error=result.error,
    )


def _extract_run_id(entry: Any) -> str:
    for attr in ("run_id", "id"):
        value = getattr(entry, attr, None)
        if value:
            return str(value)
    return str(entry)


# -- Repository commands ----------------------------------------------------------------


@click.group()
def repo() -> None:
    """Repository management commands."""


@repo.command(
    "init",
    help="Initialize a repository from a zip file, git URL, or create an empty repo.",
)
@click.option("--zip", "zip_file", type=click.Path(exists=True, path_type=Path), help="Initialize from a zip archive")
@click.option("--git", "git_url", type=str, help="Clone from a Git repository URL")
@click.option("--empty", is_flag=True, help="Create an empty repository managed by Solo Git")
@click.option("--path", "target_path", type=click.Path(path_type=Path), help="Target directory when using --empty")
@click.option("--name", type=str, help="Override the detected repository name")
def repo_init(
    zip_file: Optional[Path],
    git_url: Optional[str],
    empty: bool,
    target_path: Optional[Path],
    name: Optional[str],
) -> None:
    formatter.print_header("Repository Initialization")

    sources = [bool(zip_file), bool(git_url), bool(empty)]
    if sum(sources) != 1:
        provided = [flag for flag, is_set in zip(["--zip", "--git", "--empty"], sources) if is_set]
        abort_with_error(
            "Invalid Source Specification",
            f"Please specify exactly one of --zip, --git, or --empty. Provided: {', '.join(provided) or 'None'}",
            title="Repository Initialization Blocked",
            help_text="Choose one initialization method.",
            suggestions=[
                "evogitctl repo init --zip app.zip",
                "evogitctl repo init --git https://github.com/user/repo.git",
                "evogitctl repo init --empty --path ./new-repo",
            ],
        )

    git_sync = get_git_sync()

    try:
        if empty:
            repo_name = name or (target_path.name if target_path else "solo-git-repo")
            formatter.print_info(f"Creating empty repository: {repo_name}")
            repo_info = git_sync.create_empty_repo(repo_name, str(target_path) if target_path else None)
        elif zip_file:
            repo_name = name or zip_file.stem
            formatter.print_info(f"Initializing from zip: {zip_file.name}")
            repo_info = git_sync.init_repo_from_zip(zip_file.read_bytes(), repo_name)
        else:
            repo_name = name or Path(git_url or "repo").stem.replace(".git", "")
            formatter.print_info(f"Cloning from: {git_url}")
            repo_info = git_sync.init_repo_from_git(git_url, repo_name)

        formatter.print_success("Repository initialized!")
        table = formatter.table(headers=["Field", "Value"])
        table.add_row("ID", f"[cyan]{repo_info.get('repo_id', repo_info.get('id', '-'))}[/cyan]")
        table.add_row("Name", f"[bold]{repo_info.get('name', repo_name)}[/bold]")
        table.add_row("Path", repo_info.get("path", "-"))
        table.add_row("Trunk", repo_info.get("trunk_branch", "main"))
        formatter.console.print(table)
    except GitEngineError as exc:
        abort_with_error(
            "Repository initialization failed",
            str(exc),
            title="Repository Initialization Blocked",
            help_text="Confirm the source path or URL is reachable and that credentials are valid.",
            tip="If cloning from a private remote, ensure authentication is configured.",
            suggestions=["Retry with --verbose", "Check git remote access manually"],
            docs_url="docs/SETUP.md#initialize-a-repository",
        )


@repo.command(
    "list",
    help=(
        "List all registered repositories.\n\n"
        "Displays each repository's ID, name, trunk branch, number of workpads, and creation date."
    ),
)
def repo_list() -> None:
    git_engine = get_git_engine()
    repos = git_engine.list_repos()

    if not repos:
        formatter.print_info("No repositories found.")
        formatter.print("\n💡 Create a repository with: evogitctl repo init --zip app.zip")
        return

    formatter.print_header(f"Repositories ({len(repos)})")
    table = formatter.table(headers=["ID", "Name", "Trunk", "Workpads", "Created"])
    for repo in repos:
        repo_id = getattr(repo, "id", "-")
        repo_name = getattr(repo, "name", repo_id)
        trunk = getattr(repo, "trunk_branch", "main")
        workpad_count = getattr(repo, "workpad_count", 0)
        created = _format_datetime(getattr(repo, "created_at", "-"))
        table.add_row(
            f"[cyan]{repo_id}[/cyan]",
            f"[bold]{repo_name}[/bold]",
            trunk,
            str(workpad_count),
            created,
        )
    formatter.console.print(table)


@repo.command("delete")
@click.argument("repo_id")
@click.option("--keep-files", is_flag=True, help="Retain repository files on disk")
def repo_delete(repo_id: str, keep_files: bool) -> None:
    git_sync = get_git_sync()

    try:
        repo = git_sync.git_engine.get_repo(repo_id)
        if not repo:
            abort_with_error(f"Repository {repo_id} not found")
        formatter.print_info(f"Deleting repository {getattr(repo, 'name', repo_id)} ({repo_id})")
        git_sync.delete_repository(repo_id, remove_files=not keep_files)
        formatter.print_success("Repository deleted")
        if keep_files:
            formatter.print_info("Repository files retained on disk")
    except GitEngineError as exc:
        abort_with_error("Failed to delete repository", str(exc))


@repo.command("info")
@click.argument("repo_id")
def repo_info(repo_id: str) -> None:
    git_engine = get_git_engine()
    repo = git_engine.get_repo(repo_id)

    if not repo:
        available = [f"{r.id} • {getattr(r, 'name', r.id)}" for r in git_engine.list_repos()]
        formatter.print_error(
            "Repository Not Found",
            f"Repository '{repo_id}' is not registered with Solo Git.",
            help_text="Select one of the available repository IDs or initialize a new repository before retrying.",
            tip="Run 'evogitctl repo list' to review active repositories before invoking repo info.",
            suggestions=["evogitctl repo list"] + available[:5],
            docs_url="docs/SETUP.md#initialize-a-repository",
        )
        raise click.Abort()

    details = formatter.table(headers=["Field", "Value"])
    details.add_row("ID", f"[cyan]{repo.id}[/cyan]")
    details.add_row("Name", f"[bold]{getattr(repo, 'name', repo.id)}[/bold]")
    details.add_row("Path", getattr(repo, "path", "-"))
    details.add_row("Trunk", getattr(repo, "trunk_branch", "main"))
    details.add_row("Workpads", f"{getattr(repo, 'workpad_count', 0)} active")
    source_type = getattr(repo, "source_type", "-")
    details.add_row("Source", source_type)
    source_url = getattr(repo, "source_url", None)
    if source_url:
        details.add_row("URL", source_url)
    details.add_row("Created", _format_datetime(getattr(repo, "created_at", "-")))

    summary = "\n".join(
        [
            f"Repository: {getattr(repo, 'name', repo.id)}",
            f"Name: {getattr(repo, 'name', repo.id)}",
            f"Path: {getattr(repo, 'path', '-')}",
            f"Trunk: {getattr(repo, 'trunk_branch', 'main')}",
            f"Workpads: {getattr(repo, 'workpad_count', 0)} active",
            f"Source: {source_type}",
        ]
    )
    formatter.print_panel(summary, title="📦 Repository")
    formatter.console.print(details)


# -- Workpad commands -------------------------------------------------------------------


@click.group()
def pad() -> None:
    """Workpad management commands."""


@pad.command("create")
@click.argument("title")
@click.option("--repo", "repo_id", type=str, help="Repository ID (required if multiple repos exist)")
def pad_create(title: str, repo_id: Optional[str]) -> None:
    git_engine = get_git_engine()

    formatter.print_header("Workpad Creation")

    if not repo_id:
        repos = git_engine.list_repos()
        if not repos:
            abort_with_error(
                "No repositories found",
                "Initialize a repository first: evogitctl repo init --zip app.zip",
            )
        if len(repos) == 1:
            repo = repos[0]
            repo_id = getattr(repo, "id", None)
            formatter.print_info(f"Using repository: {getattr(repo, 'name', repo_id)} ({repo_id})")
        else:
            formatter.print_warning("Multiple repositories found. Use --repo to specify an ID.")
            table = formatter.table(headers=["ID", "Name"])
            for repo in repos:
                repo_identifier = getattr(repo, "id", "<unknown>")
                repo_name = getattr(repo, "name", repo_identifier)
                table.add_row(f"[cyan]{repo_identifier}[/cyan]", str(repo_name))
            formatter.console.print(table)
            abort_with_error(
                "Multiple repositories found",
                "Please rerun the command with --repo <ID>.",
            )

    try:
        formatter.print_info(f"Creating workpad: {title}")
        pad_id = git_engine.create_workpad(repo_id, title)
        workpad = _require_workpad(git_engine.get_workpad(pad_id), pad_id)
        formatter.print_success("Workpad created!")
        formatter.print_info(f"Pad ID: {getattr(workpad, 'id', pad_id)}")
        formatter.print_info(f"Title: {getattr(workpad, 'title', title)}")
        formatter.print_info(f"Branch: {getattr(workpad, 'branch_name', '-')}")
        formatter.print_info("Base: main")
        details = formatter.table(headers=["Field", "Value"])
        details.add_row("Pad ID", f"[cyan]{str(getattr(workpad, 'id', pad_id))}[/cyan]")
        details.add_row("Title", f"[bold]{str(getattr(workpad, 'title', title))}[/bold]")
        details.add_row("Branch", str(getattr(workpad, "branch_name", "-")))
        details.add_row("Base", str(getattr(workpad, "base_branch", "main")))
        formatter.console.print(details)
    except GitEngineError as exc:
        abort_with_error("Failed to create workpad", str(exc))


@pad.command("list")
@click.option("--repo", "repo_id", type=str, help="Filter workpads by repository ID")
def pad_list(repo_id: Optional[str]) -> None:
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
        status_value = getattr(pad_obj, "status", "unknown")
        icon, color = _status_icon(status_value)
        status_display = f"[{color}]{icon} {status_value}[/{color}]"
        checkpoints = len(getattr(pad_obj, "checkpoints", []) or [])
        test_status = getattr(pad_obj, "test_status", None)
        if test_status:
            tests_display = {
                "passed": "✅ passed",
                "failed": "❌ failed",
                "pending": "⏳ pending",
            }.get(str(test_status).lower(), str(test_status))
        else:
            tests_display = "-"
        created = _format_datetime(getattr(pad_obj, "created_at", "-"))
        table.add_row(
            getattr(pad_obj, "id", "-"),
            getattr(pad_obj, "title", "-"),
            status_display,
            str(checkpoints),
            tests_display,
            created,
        )
    formatter.console.print(table)


@pad.command("info")
@click.argument("pad_id")
def pad_info(pad_id: str) -> None:
    git_engine = get_git_engine()
    workpad = git_engine.get_workpad(pad_id)
    workpad = _require_workpad(workpad, pad_id)

    checkpoints = getattr(workpad, "checkpoints", []) or []
    summary = "\n".join(
        [
            f"Workpad: {getattr(workpad, 'id', pad_id)}",
            f"Title: {getattr(workpad, 'title', '-')}",
            f"Repo: {getattr(workpad, 'repo_id', '-')}",
            f"Branch: {getattr(workpad, 'branch_name', '-')}",
            f"Status: {getattr(workpad, 'status', '-')}",
            f"Checkpoints: {len(checkpoints)}",
            f"Last Test: {getattr(workpad, 'test_status', '-')}",
        ]
    )
    formatter.print_panel(summary, title="🗒️ Workpad")

    details = formatter.table(headers=["Field", "Value"])
    details.add_row("Workpad", str(getattr(workpad, "id", pad_id)))
    details.add_row("Title", str(getattr(workpad, "title", "-")))
    details.add_row("Repo", str(getattr(workpad, "repo_id", "-")))
    details.add_row("Branch", str(getattr(workpad, "branch_name", "-")))
    details.add_row("Status", str(getattr(workpad, "status", "-")))
    details.add_row("Checkpoints", str(len(checkpoints)))
    details.add_row("Last Test", str(getattr(workpad, "test_status", "-")))
    details.add_row("Created", _format_datetime(getattr(workpad, "created_at", "-")))
    formatter.console.print(details)


@pad.command("diff")
@click.argument("pad_id")
def pad_diff(pad_id: str) -> None:
    git_engine = get_git_engine()
    workpad = _require_workpad(git_engine.get_workpad(pad_id), pad_id)
    diff = git_engine.get_diff(pad_id)
    formatter.print_header(f"Diff for {getattr(workpad, 'title', pad_id)}")
    formatter.console.print(diff or "No changes detected.")


@pad.command("promote")
@click.argument("pad_id")
@click.option("--force", is_flag=True, help="Force promotion even if not fast-forward")
def pad_promote(pad_id: str, force: bool) -> None:
    git_engine = get_git_engine()
    workpad = git_engine.get_workpad(pad_id)
    _require_workpad(workpad, pad_id)

    if not force and not git_engine.can_promote(pad_id):
        abort_with_error(
            "Cannot promote: not fast-forward-able",
            "Trunk has diverged; rebase or use --force to override.",
        )

    try:
        formatter.print_header("Promoting workpad")
        commit_hash = git_engine.promote_workpad(pad_id, force=force)
        formatter.print_success("Workpad promoted to trunk!")
        if commit_hash:
            formatter.print_info(f"Commit: {commit_hash}")
    except GitEngineError as exc:
        abort_with_error("Promotion failed", str(exc))


@pad.command("auto-merge")
@click.argument("pad_id")
@click.option("--target", type=click.Choice(["fast", "full"]), default="fast", help="Test target to run")
@click.option("--no-auto-promote", is_flag=True, help="Don't auto-promote if tests pass")
def pad_auto_merge(pad_id: str, target: str, no_auto_promote: bool) -> None:
    """
    Execute complete auto-merge workflow.
    
    Runs tests, analyzes results, evaluates promotion gate, and optionally
    promotes to trunk if all checks pass.
    """
    git_engine = get_git_engine()
    test_orchestrator = get_test_orchestrator()
    workpad = git_engine.get_workpad(pad_id)
    _require_workpad(workpad, pad_id)

    formatter.print_header("Auto-Merge Workflow")
    formatter.print_info(f"Workpad: {getattr(workpad, 'title', pad_id)}")
    formatter.print_info(f"Target: {target}")
    formatter.print_info(f"Auto-promote: {'disabled' if no_auto_promote else 'enabled'}")

    # Get test configuration
    config_manager = get_config_manager()
    tests_config = getattr(config_manager.config, "tests", None)
    default_timeout = getattr(tests_config, "timeout_seconds", 300) if tests_config else 300

    tests: List[OrchestratorTestConfig]
    if tests_config:
        config_entries = tests_config.fast_tests if target == "fast" else tests_config.full_tests
        tests = _tests_from_config_entries(config_entries, default_timeout)
    else:
        tests = []

    if not tests:
        tests = _fallback_tests(target, default_timeout)

    # Initialize workflow
    try:
        workflow = AutoMergeWorkflow(
            git_engine,
            test_orchestrator,
            state_manager=StateManager(),
        )
    except Exception as exc:
        abort_with_error("Failed to initialize auto-merge workflow", str(exc))

    # Execute workflow
    try:
        result = workflow.execute(
            pad_id,
            tests,
            parallel=True,
            auto_promote=not no_auto_promote,
            target=target,
        )
    except Exception as exc:
        logger.error(f"Auto-merge workflow failed: {exc}", exc_info=True)
        abort_with_error("Auto-merge workflow failed", str(exc))

    # Display results
    formatted_result = workflow.format_result(result)
    formatter.console.print(formatted_result)

    if not result.success:
        raise click.Abort()


@pad.command("evaluate")
@click.argument("pad_id")
def pad_evaluate(pad_id: str) -> None:
    """
    Evaluate promotion readiness without promoting.
    
    Checks if the workpad can be promoted to trunk based on promotion
    gate rules without actually performing the promotion.
    """
    git_engine = get_git_engine()
    workpad = git_engine.get_workpad(pad_id)
    _require_workpad(workpad, pad_id)

    formatter.print_header("Promotion Gate Evaluation")
    formatter.print_info(f"Workpad: {getattr(workpad, 'title', pad_id)}")

    # Initialize promotion gate
    promotion_gate = PromotionGate(git_engine)

    # Evaluate without test analysis (checks structural requirements only)
    try:
        decision = promotion_gate.evaluate(pad_id, test_analysis=None)
    except Exception as exc:
        abort_with_error("Promotion gate evaluation failed", str(exc))

    # Display decision
    formatter.print_subheader("Decision")
    if decision.can_promote:
        formatter.print_success(f"✅ {decision.decision.value.upper()}: Ready to promote")
    else:
        formatter.print_warning(f"❌ {decision.decision.value.upper()}: Cannot promote")

    # Display reasons
    if decision.reasons:
        formatter.print_subheader("Reasons")
        for reason in decision.reasons:
            formatter.print_info(f"  {reason}")

    # Display warnings
    if decision.warnings:
        formatter.print_subheader("Warnings")
        for warning in decision.warnings:
            formatter.print_warning(f"  {warning}")

    # Show next steps
    if decision.can_promote:
        formatter.print_info("\nNext steps:")
        formatter.print_bullet_list([
            f"evogitctl pad promote {pad_id}",
            f"evogitctl pad auto-merge {pad_id}",
        ])
    else:
        formatter.print_info("\nFix the issues and try again:")
        formatter.print_bullet_list([
            f"evogitctl test run {pad_id}",
            f"evogitctl pad evaluate {pad_id}",
        ])


@pad.command("patch")
@click.argument("pad_id")
@click.argument("patch_file", type=click.Path(exists=True, path_type=Path))
@click.option("--message", "-m", default="", help="Commit message for the patch")
@click.option("--no-validate", is_flag=True, help="Skip patch validation")
def pad_patch(pad_id: str, patch_file: Path, message: str, no_validate: bool) -> None:
    """
    Apply a patch file to a workpad.
    
    Reads a unified diff patch from a file and applies it to the specified workpad.
    """
    git_engine = get_git_engine()
    patch_engine = get_patch_engine()
    workpad = git_engine.get_workpad(pad_id)
    _require_workpad(workpad, pad_id)

    formatter.print_header("Apply Patch")
    formatter.print_info(f"Workpad: {getattr(workpad, 'title', pad_id)}")
    formatter.print_info(f"Patch file: {patch_file}")

    # Read patch content
    try:
        patch_content = patch_file.read_text()
    except Exception as exc:
        abort_with_error("Failed to read patch file", str(exc))

    if not patch_content.strip():
        abort_with_error("Patch file is empty", f"File: {patch_file}")

    # Apply patch
    try:
        checkpoint_id = patch_engine.apply_patch(
            pad_id,
            patch_content,
            message=message or f"Applied patch from {patch_file.name}",
            validate=not no_validate,
        )
        formatter.print_success("Patch applied successfully!")
        formatter.print_info(f"Checkpoint ID: {checkpoint_id}")
    except Exception as exc:
        logger.error(f"Failed to apply patch: {exc}", exc_info=True)
        abort_with_error("Failed to apply patch", str(exc))


@pad.command("rebase")
@click.argument("pad_id")
@click.option("--force", is_flag=True, help="Force rebase even if conflicts detected")
def pad_rebase(pad_id: str, force: bool) -> None:
    """
    Rebase workpad against trunk.
    
    Updates the workpad's base to the latest trunk commit.
    """
    git_engine = get_git_engine()
    workpad = git_engine.get_workpad(pad_id)
    _require_workpad(workpad, pad_id)

    formatter.print_header("Rebase Workpad")
    formatter.print_info(f"Workpad: {getattr(workpad, 'title', pad_id)}")

    # Check if rebase is needed
    try:
        can_ff = git_engine.can_promote(pad_id)
        if can_ff:
            formatter.print_info("Workpad is already up-to-date with trunk")
            formatter.print_success("No rebase needed")
            return
    except Exception as exc:
        logger.warning(f"Could not check fast-forward status: {exc}")

    # Perform rebase
    try:
        formatter.print_info("Rebasing against trunk...")
        git_engine.rebase_workpad(pad_id)
        formatter.print_success("Rebase completed successfully!")
        formatter.print_info(f"Workpad {pad_id} is now up-to-date with trunk")
    except GitEngineError as exc:
        error_msg = str(exc)
        if "conflict" in error_msg.lower() and not force:
            abort_with_error(
                "Rebase failed due to conflicts",
                error_msg,
                suggestions=[
                    f"evogitctl pad diff {pad_id}",
                    f"evogitctl pad rebase {pad_id} --force",
                    "Manually resolve conflicts in the repository",
                ],
            )
        abort_with_error("Rebase failed", error_msg)


# -- Test commands ----------------------------------------------------------------------


@click.group()
def test() -> None:
    """Run automated test suites."""


@test.command("run")
@click.argument("pad_id")
@click.option("--target", type=click.Choice(["fast", "full"]), default="fast", help="Test target")
@click.option("--parallel/--sequential", default=True, help="Execute tests in parallel")
def test_run(pad_id: str, target: str, parallel: bool) -> None:
    git_engine = get_git_engine()
    test_orchestrator = get_test_orchestrator()

    workpad = git_engine.get_workpad(pad_id)
    workpad = _require_workpad(workpad, pad_id)

    state_manager = StateManager()
    run_entry = state_manager.create_test_run(pad_id, target)
    run_id = _extract_run_id(run_entry)
    state_manager.update_test_run(run_id, status="running")

    config_manager = get_config_manager()
    tests_config = getattr(config_manager.config, "tests", None)
    default_timeout = getattr(tests_config, "timeout_seconds", 300) if tests_config else 300

    tests: List[OrchestratorTestConfig]
    if tests_config:
        config_entries = tests_config.fast_tests if target == "fast" else tests_config.full_tests
        tests = _tests_from_config_entries(config_entries, default_timeout)
    else:
        tests = []

    if not tests:
        tests = _fallback_tests(target, default_timeout)

    try:
        results: List[TestResult] = asyncio.run(
            test_orchestrator.run_tests(pad_id, tests=tests, parallel=parallel)
        )
    except Exception as exc:  # pragma: no cover - exercised via tests
        error_message = str(exc)
        state_result = StateTestResult(
            test_id=f"{run_id}:orchestrator",
            name="orchestrator",
            status="error",
            duration_ms=0,
            output="",
            error=error_message,
        )
        state_manager.update_test_run(
            run_id,
            status="failed",
            total_tests=1,
            passed=0,
            failed=1,
            skipped=0,
            duration_ms=0,
            tests=[state_result],
        )
        abort_with_error(
            "Test execution failed",
            details=f"Workpad: {pad_id}\n{error_message}",
            title="Test Execution Failed",
            suggestions=[
                f"evogitctl test run {pad_id}",
                f"evogitctl pad info {pad_id}",
            ],
        )

    passed = sum(1 for result in results if result.status == TestStatus.PASSED)
    failed = sum(
        1
        for result in results
        if result.status in {TestStatus.FAILED, TestStatus.ERROR, TestStatus.TIMEOUT}
    )
    skipped = sum(1 for result in results if result.status == TestStatus.SKIPPED)
    total = len(results)
    duration_ms = sum(result.duration_ms for result in results)

    formatter.print_header("🧪 Test Execution")
    formatter.print_info(f"Workpad: {getattr(workpad, 'title', pad_id)}")
    formatter.print_info(f"Mode: {getattr(test_orchestrator, 'mode', 'subprocess')}")
    formatter.print_info(f"Target: {target}")

    table = formatter.table(headers=["Test", "Status", "Duration", "Log"])
    state_results: List[StateTestResult] = []
    for result in results:
        status_text = _format_test_status(result.status)
        duration_s = result.duration_ms / 1000 if result.duration_ms else 0
        log_name = result.log_path.name if result.log_path else "-"
        table.add_row(result.name, status_text, f"{duration_s:.2f}s", log_name)
        state_results.append(_state_result_from_test_result(run_id, result))
    formatter.console.print(table)

    summary_table = formatter.table(headers=["Metric", "Value"])
    summary_table.add_row("Total", str(total))
    summary_table.add_row("Passed", str(passed))
    summary_table.add_row("Failed", str(failed))
    summary_table.add_row("Skipped", str(skipped))
    summary_table.add_row("Duration (ms)", str(duration_ms))

    formatter.print_header("Test Summary")
    formatter.console.print(summary_table)
    formatter.print_info(f"Passed: {passed}")
    formatter.print_info(f"Failed: {failed}")
    formatter.print_info(f"Skipped: {skipped}")

    summary = test_orchestrator.get_summary(results)
    if summary.get("status") == "green":
        formatter.print_success("All tests passed!")
    else:
        formatter.print_warning("Tests Require Attention")
        formatter.print_info("Some tests failed or timed out. Review results below.")

    state_manager.update_test_run(
        run_id,
        status="passed" if failed == 0 else "failed",
        total_tests=total,
        passed=passed,
        failed=failed,
        skipped=skipped,
        duration_ms=duration_ms,
        tests=state_results,
    )


@test.command("analyze")
@click.argument("pad_id")
def test_analyze(pad_id: str) -> None:
    """
    Analyze test failures and suggest fixes.
    
    Examines test results to identify failure patterns, categorize errors,
    and provide actionable suggestions for fixing issues.
    """
    git_engine = get_git_engine()
    workpad = git_engine.get_workpad(pad_id)
    _require_workpad(workpad, pad_id)

    formatter.print_header("Test Failure Analysis")
    formatter.print_info(f"Workpad: {getattr(workpad, 'title', pad_id)}")

    # Get recent test run
    state_manager = StateManager()
    try:
        test_runs = state_manager.get_test_runs(pad_id)
        if not test_runs:
            formatter.print_warning("No test runs found for this workpad")
            formatter.print_info(f"Run tests first: evogitctl test run {pad_id}")
            return

        # Use most recent test run
        latest_run = test_runs[0] if isinstance(test_runs, list) else test_runs
        run_id = _extract_run_id(latest_run)
    except Exception as exc:
        logger.warning(f"Could not retrieve test runs: {exc}")
        formatter.print_warning("Could not retrieve test history")
        formatter.print_info(f"Run tests first: evogitctl test run {pad_id}")
        return

    # Get test results for analysis
    try:
        test_run_data = state_manager.get_test_run(run_id)
        if not test_run_data:
            formatter.print_warning("No test data found")
            return

        state_results = getattr(test_run_data, "tests", [])
        if not state_results:
            formatter.print_warning("No test results to analyze")
            return

        # Convert state results to engine results for analyzer
        from sologit.engines.test_orchestrator import TestResult as EngineTestResult
        
        engine_results: List[EngineTestResult] = []
        for state_result in state_results:
            status_map = {
                "passed": TestStatus.PASSED,
                "failed": TestStatus.FAILED,
                "error": TestStatus.ERROR,
                "timeout": TestStatus.TIMEOUT,
                "skipped": TestStatus.SKIPPED,
            }
            status = status_map.get(
                getattr(state_result, "status", "failed").lower(),
                TestStatus.FAILED,
            )
            engine_results.append(
                EngineTestResult(
                    name=getattr(state_result, "name", "unknown"),
                    status=status,
                    duration_ms=getattr(state_result, "duration_ms", 0),
                    stdout=getattr(state_result, "output", ""),
                    stderr="",
                    error=getattr(state_result, "error", None),
                    log_path=None,
                )
            )

    except Exception as exc:
        logger.error(f"Failed to load test results: {exc}", exc_info=True)
        abort_with_error("Failed to load test results", str(exc))

    # Analyze test results
    try:
        analyzer = TestAnalyzer()
        analysis = analyzer.analyze(engine_results)
    except Exception as exc:
        logger.error(f"Test analysis failed: {exc}", exc_info=True)
        abort_with_error("Test analysis failed", str(exc))

    # Display analysis results
    formatter.print_subheader("Test Summary")
    table = formatter.table(headers=["Metric", "Value"])
    table.add_row("Total Tests", str(analysis.total_tests))
    table.add_row("Passed", f"[green]{analysis.passed}[/green]")
    table.add_row("Failed", f"[red]{analysis.failed}[/red]")
    table.add_row("Timeout", f"[yellow]{analysis.timeout}[/yellow]")
    table.add_row("Error", f"[red]{analysis.error}[/red]")
    table.add_row("Status", f"[bold]{analysis.status.upper()}[/bold]")
    table.add_row("Fix Complexity", analysis.estimated_fix_complexity)
    formatter.console.print(table)

    # Display failure patterns
    if analysis.failure_patterns:
        formatter.print_subheader("Failure Patterns")
        pattern_table = formatter.table(headers=["Category", "Message", "Count"])
        for pattern in analysis.failure_patterns[:10]:  # Show top 10
            pattern_table.add_row(
                pattern.category.value,
                pattern.message[:80] + ("..." if len(pattern.message) > 80 else ""),
                str(pattern.count),
            )
        formatter.console.print(pattern_table)

    # Display suggested actions
    if analysis.suggested_actions:
        formatter.print_subheader("Suggested Actions")
        for i, action in enumerate(analysis.suggested_actions, 1):
            formatter.print_info(f"{i}. {action}")

    # Show next steps
    formatter.print_info("\nNext steps:")
    if analysis.status == "green":
        formatter.print_bullet_list([
            f"evogitctl pad promote {pad_id}",
            f"evogitctl pad auto-merge {pad_id}",
        ])
    else:
        formatter.print_bullet_list([
            "Fix the identified issues",
            f"evogitctl test run {pad_id}",
            f"evogitctl test analyze {pad_id}",
        ])


def execute_pair_loop(
    ctx: click.Context,
    prompt: str,
    repo_id: Optional[str] = None,
    title: Optional[str] = None,
    no_test: bool = False,
    no_promote: bool = False,
    target: str = "fast",
) -> None:
    """
    Execute AI pair programming workflow.
    
    This is a simplified implementation that creates a workpad and runs
    the auto-merge workflow. A full AI integration would involve:
    - AI planning and code generation
    - Patch generation
    - Interactive refinement
    
    Args:
        ctx: Click context
        prompt: Natural language task description
        repo_id: Repository ID (auto-selected if only one exists)
        title: Workpad title (derived from prompt if not provided)
        no_test: Skip test execution
        no_promote: Disable automatic promotion
        target: Test target (fast/full)
    """
    git_engine = get_git_engine()
    
    # Auto-select repository if not provided
    if not repo_id:
        repos = git_engine.list_repos()
        if not repos:
            abort_with_error(
                "No repositories found",
                "Initialize a repository first: evogitctl repo init --zip app.zip",
            )
        if len(repos) == 1:
            repo = repos[0]
            repo_id = getattr(repo, "id", None)
            formatter.print_info(f"Using repository: {getattr(repo, 'name', repo_id)}")
        else:
            abort_with_error(
                "Multiple repositories found",
                "Please specify --repo <ID>",
                suggestions=[f"--repo {getattr(r, 'id', 'unknown')}" for r in repos[:5]],
            )
    
    # Create workpad
    workpad_title = title or prompt[:50]
    formatter.print_info(f"Creating workpad: {workpad_title}")
    
    try:
        pad_id = git_engine.create_workpad(repo_id, workpad_title)
        formatter.print_success(f"Created workpad: {pad_id}")
    except Exception as exc:
        abort_with_error("Failed to create workpad", str(exc))
    
    # NOTE: Full AI integration would go here:
    # 1. Call AI to analyze prompt and plan implementation
    # 2. Generate code patch
    # 3. Apply patch to workpad
    # 4. Run tests and refine if needed
    
    formatter.print_warning(
        "AI pair programming is a work in progress. "
        "The workpad has been created but AI code generation is not yet implemented."
    )
    formatter.print_info(f"Workpad ID: {pad_id}")
    formatter.print_info("\nNext steps:")
    formatter.print_bullet_list([
        f"Manually make changes in the workpad",
        f"evogitctl test run {pad_id}",
        f"evogitctl pad auto-merge {pad_id}" if not no_promote else f"evogitctl pad promote {pad_id}",
    ])


__all__ = [
    "repo",
    "pad",
    "test",
    "set_formatter_console",
    "abort_with_error",
    "get_config_manager",
    "get_git_engine",
    "get_patch_engine",
    "get_test_orchestrator",
    "get_git_sync",
    "_tests_from_config_entries",
    "_parse_test_override",
    "execute_pair_loop",
]
