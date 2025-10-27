
"""CI/CD commands for the Solo Git CLI."""

from __future__ import annotations

from typing import Optional

import click

from sologit.cli.commands import abort_with_error, formatter
from sologit.engines.git_engine import GitEngine
from sologit.engines.test_orchestrator import TestConfig, TestOrchestrator
from sologit.workflows.ci_orchestrator import CIOrchestrator
from sologit.workflows.rollback_handler import RollbackHandler


@click.group()
def ci() -> None:
    """Continuous integration orchestration commands."""


@ci.command('smoke')
@click.argument('repo_id')
@click.option('--commit', help='Commit hash to test (default: HEAD)')
def ci_smoke(repo_id: str, commit: Optional[str]) -> None:
    """
    Run smoke tests for a commit (Phase 3).

    This simulates post-merge CI smoke tests.
    """
    git_engine = GitEngine()
    test_orchestrator = TestOrchestrator(git_engine, formatter=formatter)

    repo = git_engine.get_repo(repo_id)
    if not repo:
        abort_with_error(f"Repository {repo_id} not found")

    if not commit:
        commit = git_engine.get_current_commit(repo_id)

    smoke_tests = [
        TestConfig(name="smoke-health", cmd="python -c 'print(\"Health check passed\")'", timeout=10),
        TestConfig(name="smoke-unit", cmd="python -m pytest tests/ -q --tb=no", timeout=60),
    ]

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

        result = orchestrator.run_smoke_tests(
            repo_id,
            commit,
            smoke_tests,
            on_progress=progress_callback
        )

        formatter.print_info_panel(orchestrator.format_result(result), title="Smoke Test Summary")

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
    from sologit.workflows.ci_orchestrator import CIResult, CIStatus

    git_engine = GitEngine()

    repo = git_engine.get_repo(repo_id)
    if not repo:
        abort_with_error(f"Repository {repo_id} not found")

    handler = RollbackHandler(git_engine)

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

        result = handler.handle_failed_ci(fake_ci_result, recreate_pad)

        formatter.print_info_panel(handler.format_result(result), title="Rollback Result")

        if not result.success:
            raise click.Abort()
    except Exception as e:
        abort_with_error("Rollback failed", str(e))


@ci.command("trigger")
@click.argument("pipeline")
def ci_trigger(pipeline: str) -> None:
    """Trigger a CI pipeline (placeholder implementation)."""
    formatter.print_header("CI Status")
    formatter.print_info(
        "CI orchestration helpers are not fully configured in this testing build."
    )
    formatter.print_info(f"Requested pipeline: {pipeline}")


@ci.command("status")
@click.argument("repo_id")
def ci_status(repo_id: str) -> None:
    """Display CI status information for a repository."""
    formatter.print_header("CI Status")
    formatter.print_info(f"Repository: {repo_id}")
    formatter.print_info(
        "CI orchestration helpers are not fully configured in this testing build."
    )
