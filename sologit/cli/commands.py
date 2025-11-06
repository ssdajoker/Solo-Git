"""Headless-backed command implementations for Solo Git CLI."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union

import click
from rich.console import Console

from sologit.api.service import SoloGitService
from sologit.cli.headless_client import HeadlessClient, HeadlessServiceError
from sologit.config.manager import ConfigManager
from sologit.engines.git_engine import GitEngine
from sologit.engines.patch_engine import PatchEngine
from sologit.engines.test_orchestrator import TestConfig, TestOrchestrator
from sologit.state.git_sync import GitStateSync
from sologit.ui.formatter import RichFormatter
from sologit.ui.theme import theme
from sologit.utils.logger import get_logger

logger = get_logger(__name__)

formatter = RichFormatter()
_client: Optional[HeadlessClient] = None
_service: Optional[SoloGitService] = None
_git_sync: Optional[GitStateSync] = None
_patch_engine: Optional[PatchEngine] = None
_test_orchestrator: Optional[TestOrchestrator] = None

TestEntry = Union[TestConfig, Dict[str, Any]]


def set_formatter_console(console: Console) -> None:
    """Allow the CLI entrypoint to reuse its Rich console instance."""

    formatter.set_console(console)


class _LegacyHeadlessAdapter:
    """Adapter that mimics HeadlessClient using local service/engines.

    Enables tests to patch legacy helpers while commands call a headless-like interface.
    """

    def __init__(self, service: SoloGitService) -> None:
        self.service = service

    def list_repositories(self) -> Iterable[Dict[str, Any]]:
        return self.service.list_repositories(include_state=True)

    def get_repository(self, repo_id: str) -> Optional[Dict[str, Any]]:
        return self.service.get_repository(repo_id, include_state=True)

    def create_repository(
        self,
        *,
        source: str,
        name: Optional[str] = None,
        target_path: Optional[str] = None,
        git_url: Optional[str] = None,
        zip_bytes: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        return self.service.initialize_repository(
            empty=(source == "empty"),
            name=name,
            target_path=Path(target_path).expanduser() if target_path else None,
            git_url=git_url,
            zip_bytes=zip_bytes,
        )

    def delete_repository(self, repo_id: str, *, keep_files: bool = False) -> None:
        self.service.delete_repository(repo_id, keep_files=keep_files)

    def list_workpads(self, repo_id: str) -> Iterable[Dict[str, Any]]:
        return self.service.list_workpads(repo_id)

    def create_workpad(self, repo_id: str, title: str) -> Dict[str, Any]:
        return self.service.create_workpad(repo_id, title)

    def get_workpad(self, pad_id: str) -> Optional[Dict[str, Any]]:
        return self.service.get_workpad(pad_id)

    def get_workpad_diff(self, pad_id: str) -> Dict[str, Any]:
        return self.service.get_workpad_diff(pad_id)

    def get_workpad_promotion(self, pad_id: str) -> Dict[str, Any]:
        return {"workpad_id": pad_id, "can_promote": self.service.can_promote(pad_id)}

    def promote_workpad(self, pad_id: str) -> Dict[str, Any]:
        return self.service.promote_workpad(pad_id)

    def checkpoint_workpad(self, pad_id: str, message: str) -> Dict[str, Any]:
        return self.service.checkpoint_workpad(pad_id, message)

    def run_tests(self, pad_id: str, *, target: str, parallel: bool) -> Dict[str, Any]:
        outcome = self.service.run_tests_sync(pad_id, target=target, parallel=parallel)
        return outcome.to_dict()

    def generate_commit_message(self, pad_id: str, *, conventional: bool) -> Dict[str, Any]:
        return self.service.generate_commit_message_sync(pad_id, conventional=conventional)

    def get_telemetry_summary(self, *, days: int) -> Dict[str, Any]:
        return self.service.get_telemetry_summary(days=days)


def get_client() -> HeadlessClient:
    """Return a singleton HeadlessClient or a legacy adapter when enabled."""

    if os.getenv("SOLOGIT_CLI_USE_LEGACY_ENGINE") == "1":
        return _LegacyHeadlessAdapter(get_service())  # type: ignore[return-value]

    global _client
    if _client is None:
        _client = HeadlessClient()
    return _client


def get_service() -> SoloGitService:
    """Return a singleton SoloGitService for legacy helpers."""

    global _service
    if _service is None:
        _service = SoloGitService()
    return _service


def get_config_manager() -> ConfigManager:
    """Expose the shared ConfigManager instance."""

    return get_service().config_manager


def get_git_engine() -> GitEngine:
    """Expose the GitEngine for compatibility with helper utilities."""

    return get_service().git_engine


def get_git_sync() -> GitStateSync:
    """Return the shared GitStateSync instance."""

    global _git_sync
    if _git_sync is None:
        _git_sync = get_service().git_state_sync
    return _git_sync


def get_patch_engine() -> PatchEngine:
    """Return the shared PatchEngine instance."""

    global _patch_engine
    if _patch_engine is None:
        _patch_engine = get_service().patch_engine
    return _patch_engine


def get_test_orchestrator() -> TestOrchestrator:
    """Return the shared TestOrchestrator instance."""

    global _test_orchestrator
    if _test_orchestrator is None:
        _test_orchestrator = get_service().test_orchestrator
    return _test_orchestrator


def abort_with_error(
    message: str,
    details: Optional[str] = None,
    *,
    title: Optional[str] = None,
    help_text: Optional[str] = None,
    tip: Optional[str] = None,
    suggestions: Optional[Iterable[str]] = None,
    docs_url: Optional[str] = None,
) -> None:
    """Render a consistent Rich error panel and abort the command."""

    formatter.print_error(
        title or "Command Error",
        message,
        help_text=help_text or "Use --help to review supported options.",
        tip=tip or "Verify CLI arguments and repository context.",
        suggestions=suggestions or ["evogitctl --help", "evogitctl repo list"],
        docs_url=docs_url or "docs/SETUP.md",
        details=details,
    )
    raise click.Abort()


def _emit_json(payload: Dict[str, Any]) -> None:
    print(json.dumps(payload))


def _handle_service_error(error: HeadlessServiceError, *, json_output: bool = False) -> None:
    if json_output:
        payload = error.payload if isinstance(error.payload, dict) else {"error": str(error)}
        payload.setdefault("success", False)
        _emit_json(payload)
        raise SystemExit(1)
    abort_with_error(
        str(error),
        title="Headless Service Error",
        details=json.dumps(error.payload, indent=2) if error.payload else None,
    )


def _parse_test_override(value: str, default_timeout: int) -> TestConfig:
    """Parse CLI override string into a TestConfig instance."""

    if "=" not in value:
        raise click.BadParameter("Override must be NAME=CMD[:TIMEOUT]")

    name, remainder = value.split("=", 1)
    name = name.strip()
    remainder = remainder.strip()
    if not name or not remainder:
        raise click.BadParameter("Both test name and command are required")

    timeout = default_timeout
    if ":" in remainder:
        cmd, timeout_str = remainder.rsplit(":", 1)
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


def _tests_from_config_entries(
    entries: Optional[Sequence[TestEntry]],
    default_timeout: int,
) -> List[TestConfig]:
    """Convert configuration entries to TestConfig objects."""

    if not entries:
        return []

    tests: List[TestConfig] = []
    for entry in entries:
        if isinstance(entry, TestConfig):
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

        timeout_value = entry.get("timeout", default_timeout)
        try:
            timeout = int(timeout_value) if timeout_value is not None else default_timeout
        except (TypeError, ValueError):
            logger.warning("Invalid timeout for test entry: %s", entry)
            timeout = default_timeout

        depends_raw = entry.get("depends_on") or []
        if isinstance(depends_raw, (list, tuple)):
            depends_on = [str(item) for item in depends_raw if item]
        elif isinstance(depends_raw, str):
            depends_on = [depends_raw]
        else:
            depends_on = []

        tests.append(
            TestConfig(
                name=name,
                cmd=cmd,
                timeout=timeout,
                depends_on=depends_on,
            )
        )

    return tests


def _format_duration_ms(value: Optional[int]) -> str:
    if value is None:
        return "—"
    if value < 1000:
        return f"{value}ms"
    return f"{value / 1000:.1f}s"


def _resolve_repo_id(provided_repo_id: Optional[str], client: HeadlessClient) -> str:
    """Resolve a repository identifier when not explicitly provided."""

    if provided_repo_id:
        return provided_repo_id

    repositories = list(client.list_repositories())
    if not repositories:
        abort_with_error(
            "No repositories found",
            "Initialize one with: evogitctl repo init --zip app.zip",
            title="Repository Required",
        )

    if len(repositories) > 1:
        table = formatter.table(headers=["ID", "Name", "Trunk"])
        for repo_item in repositories:
            table.add_row(
                str(repo_item.get("id") or repo_item.get("repo_id")),
                repo_item.get("name", "—"),
                repo_item.get("trunk_branch", "main"),
            )
        formatter.print_info_panel(
            "Multiple repositories detected. Re-run with --repo <ID> to select one.",
            title="Repository Selection Needed",
        )
        formatter.console.print(table)
        raise click.Abort()

    primary = repositories[0]
    return primary.get("id") or primary.get("repo_id")


@click.group()
def repo() -> None:
    """Repository management commands."""


@repo.command("list")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def repo_list(output_json: bool) -> None:
    client = get_client()
    try:
        repositories = list(client.list_repositories())
    except HeadlessServiceError as exc:
        _handle_service_error(exc, json_output=output_json)
        return

    if output_json:
        _emit_json({"success": True, "repositories": repositories})
        return

    if not repositories:
        formatter.print_info("No repositories found.")
        formatter.console.print("\nHint: Create one with: evogitctl repo init --zip app.zip")
        return

    formatter.print_header(f"Repositories ({len(repositories)})")
    table = formatter.table(headers=["ID", "Name", "Trunk", "Workpads", "Created"])
    for repo_item in repositories:
        repo_id = repo_item.get("id") or repo_item.get("repo_id") or "<unknown>"
        name = repo_item.get("name", repo_id)
        trunk = repo_item.get("trunk_branch", "main")
        workpads = str(repo_item.get("workpad_count", repo_item.get("workpads", 0)))
        created_at = repo_item.get("created_at", "—")
        table.add_row(
            f"[cyan]{repo_id}[/cyan]",
            f"[bold]{name}[/bold]",
            trunk,
            workpads,
            str(created_at),
        )
    formatter.console.print(table)


@repo.command("info")
@click.argument("repo_id")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def repo_info(repo_id: str, output_json: bool) -> None:
    client = get_client()
    try:
        repository = client.get_repository(repo_id)
    except HeadlessServiceError as exc:
        _handle_service_error(exc, json_output=output_json)
        return

    if output_json:
        _emit_json({"success": True, "repository": repository})
        return

    if not repository:
        abort_with_error(f"Repository {repo_id} not found")

    details_lines = [
        f"[bold cyan]Repository:[/bold cyan] {repository.get('id', repo_id)}",
        f"[bold]Name:[/bold] {repository.get('name', repo_id)}",
        f"[bold]Path:[/bold] {repository.get('path', '—')}",
        f"[bold]Trunk:[/bold] {repository.get('trunk_branch', 'main')}",
    ]
    if "workpad_count" in repository:
        details_lines.append(f"[bold]Workpads:[/bold] {repository.get('workpad_count')} active")
    source = repository.get("source_type") or repository.get("source")
    if source:
        details_lines.append(f"[bold]Source:[/bold] {source}")
    details_lines.append(f"[bold]Created:[/bold] {repository.get('created_at', '—')}")

    formatter.print_panel("\n".join(details_lines), title=f"Repository: {repository.get('name', repo_id)}")


@repo.command("init")
@click.option("--zip", "zip_path", type=click.Path(exists=True), help="Initialize from a zip archive")
@click.option("--git", "git_url", type=str, help="Initialize from a Git URL")
@click.option("--empty", is_flag=True, help="Create an empty repository")
@click.option("--path", "target_path", type=click.Path(), help="Target path for an empty repo")
@click.option("--name", type=str, help="Repository name")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def repo_init(
    zip_path: Optional[str],
    git_url: Optional[str],
    empty: bool,
    target_path: Optional[str],
    name: Optional[str],
    output_json: bool,
) -> None:
    provided = [label for label, value in (("zip", zip_path), ("git", git_url), ("empty", empty)) if value]
    if len(provided) != 1:
        abort_with_error(
            "Invalid source selection",
            f"Provide exactly one of --zip, --git, or --empty. Provided: {', '.join(provided) or 'None'}",
        )

    client = get_client()
    try:
        if zip_path:
            data = Path(zip_path).read_bytes()
            repository = client.create_repository(source="zip", name=name, zip_bytes=data)
        elif git_url:
            repository = client.create_repository(source="git", name=name, git_url=git_url)
        else:
            repository = client.create_repository(source="empty", name=name, target_path=target_path)
    except HeadlessServiceError as exc:
        _handle_service_error(exc, json_output=output_json)
        return

    if output_json:
        _emit_json({"success": True, "repository": repository})
        return

    formatter.print_success("Repository initialized")
    formatter.print_info(f"Repo ID: {repository.get('repo_id')}")
    formatter.print_info(f"Name: {repository.get('name')}")
    formatter.print_info(f"Path: {repository.get('path')}")
    formatter.print_info(f"Trunk: {repository.get('trunk_branch', 'main')}")


@repo.command("delete")
@click.argument("repo_id")
@click.option("--keep-files", is_flag=True, help="Retain the repository directory on disk")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def repo_delete(repo_id: str, keep_files: bool, output_json: bool) -> None:
    client = get_client()
    try:
        client.delete_repository(repo_id, keep_files=keep_files)
    except HeadlessServiceError as exc:
        _handle_service_error(exc, json_output=output_json)
        return

    if output_json:
        _emit_json({"success": True, "repo_id": repo_id, "keep_files": keep_files})
        return

    formatter.print_success("Repository deleted")
    if keep_files:
        formatter.print_info("Repository files retained on disk")


@click.group()
def pad() -> None:
    """Workpad management commands."""


@pad.command("create")
@click.argument("title")
@click.option("--repo", "repo_id", type=str, help="Repository ID (required if multiple repos)")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def pad_create(title: str, repo_id: Optional[str], output_json: bool) -> None:
    client = get_client()
    try:
        resolved_repo = _resolve_repo_id(repo_id, client)
        repo_meta = client.get_repository(resolved_repo) or {}
        repo_name = repo_meta.get("name", resolved_repo)
        formatter.print_info(f"Using repository: {repo_name} ({resolved_repo})")
        formatter.print_info(f"Creating workpad: {title}")
        workpad = client.create_workpad(resolved_repo, title)
    except HeadlessServiceError as exc:
        _handle_service_error(exc, json_output=output_json)
        return

    if output_json:
        _emit_json({"success": True, "workpad": workpad})
        return

    formatter.print_success("Workpad created!")
    formatter.print_info(f"Pad ID: {workpad.get('workpad_id', 'unknown')}")
    formatter.print_info(f"Repository: {workpad.get('repo_id')}")
    formatter.print_info(f"Branch: {workpad.get('branch_name')}")


@pad.command("list")
@click.option("--repo", "repo_id", type=str, help="Repository ID (auto-selects if only one)")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def pad_list(repo_id: Optional[str], output_json: bool) -> None:
    client = get_client()
    try:
        resolved_repo = _resolve_repo_id(repo_id, client)
        workpads = list(client.list_workpads(resolved_repo))
    except HeadlessServiceError as exc:
        _handle_service_error(exc, json_output=output_json)
        return

    if output_json:
        _emit_json({"success": True, "repo_id": resolved_repo, "workpads": workpads})
        return

    if not workpads:
        formatter.print_info("No workpads found.")
        return

    formatter.print_header(f"Workpads for {resolved_repo}")
    table = formatter.table(headers=["ID", "Title", "Status", "Updated"])
    for pad_item in workpads:
        pad_id = pad_item.get("workpad_id") or pad_item.get("id")
        title = pad_item.get("title", pad_id)
        status = pad_item.get("status", "unknown")
        updated = pad_item.get("updated_at", "—")
        table.add_row(f"[cyan]{pad_id}[/cyan]", f"[bold]{title}[/bold]", status, str(updated))
    formatter.console.print(table)


@pad.command("info")
@click.argument("pad_id")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def pad_info(pad_id: str, output_json: bool) -> None:
    client = get_client()
    try:
        workpad = client.get_workpad(pad_id)
    except HeadlessServiceError as exc:
        _handle_service_error(exc, json_output=output_json)
        return

    if output_json:
        _emit_json({"success": True, "workpad": workpad})
        return

    if not workpad:
        abort_with_error(f"Workpad {pad_id} not found")

    status = str(workpad.get("status", "unknown")).lower()
    status_color = theme.get_status_color(status)
    status_icon = theme.get_status_icon(status)
    formatter.print_info_panel(
        """[bold]Workpad ID:[/bold] [cyan]{identifier}[/cyan]
[bold]Repository:[/bold] {repo}
[bold]Branch:[/bold] {branch}
[bold]Status:[/bold] [{color}]{icon} {status}[/]{color}
[bold]Created:[/bold] {created}
[bold]Updated:[/bold] {updated}
[bold]Can Promote:[/bold] {can_promote}
""".format(
            identifier=workpad.get("workpad_id", pad_id),
            repo=workpad.get("repo_id", "—"),
            branch=workpad.get("branch_name", "—"),
            color=status_color,
            icon=status_icon,
            status=status.upper(),
            created=workpad.get("created_at", "—"),
            updated=workpad.get("updated_at", "—"),
            can_promote=workpad.get("can_promote", False),
        ),
        title="Workpad Summary",
    )

    checkpoints = workpad.get("checkpoints") or workpad.get("state", {}).get("checkpoints", [])
    if checkpoints:
        formatter.print_subheader("Checkpoints")
        formatter.print_bullet_list(checkpoints, icon=theme.icons.commit, style=theme.colors.blue)


@pad.command("diff")
@click.argument("pad_id")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def pad_diff(pad_id: str, output_json: bool) -> None:
    client = get_client()
    try:
        diff_payload = client.get_workpad_diff(pad_id)
    except HeadlessServiceError as exc:
        _handle_service_error(exc, json_output=output_json)
        return

    if output_json:
        payload = {"success": True, "workpad_id": pad_id}
        if isinstance(diff_payload, dict):
            payload.update(diff_payload)
        _emit_json(payload)
        return

    diff_text = ""
    summary: Dict[str, Any] = {}
    if isinstance(diff_payload, dict):
        diff_text = diff_payload.get("diff", "") or ""
        summary = diff_payload.get("summary") or {}

    formatter.print_header(f"Diff for {pad_id}")

    if summary:
        summary_table = formatter.table(headers=["Metric", "Value"])
        summary_table.add_row("Base", summary.get("base_branch", "trunk"))
        summary_table.add_row("Compare", summary.get("compare_branch", "workpad"))
        summary_table.add_row("Files", str(summary.get("files_changed", 0)))
        summary_table.add_row("Lines Added", f"+{summary.get('lines_added', 0)}")
        summary_table.add_row("Lines Deleted", f"-{summary.get('lines_deleted', 0)}")
        summary_table.add_row("Lines Changed", str(summary.get("lines_changed", 0)))
        formatter.console.print(summary_table)

    if diff_text.strip():
        formatter.print_code(diff_text, language="diff")
    else:
        formatter.print_info("No changes detected for this workpad.")


@pad.command("checkpoint")
@click.argument("pad_id")
@click.option("-m", "--message", help="Checkpoint message")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def pad_checkpoint(pad_id: str, message: Optional[str], output_json: bool) -> None:
    if not message and output_json:
        _emit_json({"success": False, "error": "Checkpoint message is required"})
        return
    if not message:
        message = click.prompt("Checkpoint message", type=str)

    client = get_client()
    try:
        result = client.checkpoint_workpad(pad_id, message)
    except HeadlessServiceError as exc:
        _handle_service_error(exc, json_output=output_json)
        return

    if output_json:
        payload = {"success": True}
        if isinstance(result, dict):
            payload.update(result)
        _emit_json(payload)
        return

    formatter.print_success("Checkpoint created")
    formatter.print_info(f"Workpad: {result.get('workpad_id', pad_id)}")
    formatter.print_info(f"Commit: {result.get('commit_hash', '—')}")
    formatter.print_info(f"Message: {result.get('message', message)}")


@pad.command("promotion")
@click.argument("pad_id")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def pad_promotion(pad_id: str, output_json: bool) -> None:
    client = get_client()
    try:
        status_payload = client.get_workpad_promotion(pad_id)
    except HeadlessServiceError as exc:
        _handle_service_error(exc, json_output=output_json)
        return

    if output_json:
        payload = {"success": True, "workpad_id": pad_id}
        if isinstance(status_payload, dict):
            payload.update(status_payload)
        _emit_json(payload)
        return

    can_promote = bool(status_payload.get("can_promote")) if isinstance(status_payload, dict) else False
    if can_promote:
        formatter.print_success("Workpad passes promotion checks")
    else:
        formatter.print_warning("Promotion rules not satisfied. Resolve outstanding checks before promoting.")
    formatter.print_info(f"Workpad: {pad_id}")


@pad.command("promote")
@click.argument("pad_id")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def pad_promote(pad_id: str, output_json: bool) -> None:
    client = get_client()
    try:
        # Pre-check fast-forward eligibility
        try:
            status_payload = client.get_workpad_promotion(pad_id)
        except Exception:
            status_payload = {}
        if isinstance(status_payload, dict) and not status_payload.get("can_promote", True):
            if output_json:
                _emit_json({"success": False, "error": "not_fast_forwardable", "workpad_id": pad_id})
                return
            abort_with_error(
                "Cannot promote: not fast-forward-able",
                details="Trunk has diverged; rebase or update your workpad to the latest trunk.",
                title="Promotion Blocked",
            )
        result = client.promote_workpad(pad_id)
    except HeadlessServiceError as exc:
        _handle_service_error(exc, json_output=output_json)
        return

    if output_json:
        payload = {"success": True}
        payload.update(result)
        _emit_json(payload)
        return

    formatter.print_success("Workpad promoted to trunk")
    formatter.print_info(f"Commit: {result.get('commit_hash')}")
    formatter.print_info(f"Branch Removed: {result.get('branch_removed')}")


@pad.command("delete")
@click.argument("pad_id")
@click.option("--force", is_flag=True, help="Force deletion even if tests failed")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def pad_delete(pad_id: str, force: bool, output_json: bool) -> None:
    client = get_client()
    try:
        client.delete_workpad(pad_id, force=force)
    except HeadlessServiceError as exc:
        _handle_service_error(exc, json_output=output_json)
        return

    if output_json:
        _emit_json({"success": True, "workpad_id": pad_id, "force": force})
        return

    formatter.print_success("Workpad deleted")


@click.group()
def test() -> None:
    """Test orchestration commands."""


@test.command("run")
@click.argument("pad_id")
@click.option(
    "--target",
    type=click.Choice(["fast", "full"], case_sensitive=False),
    default="fast",
    show_default=True,
    help="Test target defined by Solo Git configuration",
)
@click.option("--serial", is_flag=True, help="Run tests sequentially instead of in parallel")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def test_run(pad_id: str, target: str, serial: bool, output_json: bool) -> None:
    client = get_client()
    try:
        result = client.run_tests(pad_id, target=target, parallel=not serial)
    except HeadlessServiceError as exc:
        _handle_service_error(exc, json_output=output_json)
        return

    if output_json:
        payload = {"success": True, "workpad_id": pad_id}
        if isinstance(result, dict):
            payload.update(result)
        _emit_json(payload)
        return

    if not isinstance(result, dict):
        formatter.print_warning("Unexpected response from headless service")
        return

    formatter.print_header(f"Test Execution: {pad_id}")
    formatter.print_info(f"Target: {target}")
    formatter.print_info(f"Run Mode: {'Serial' if serial else 'Parallel'}")

    results = result.get("results", []) or []
    summary = result.get("summary", {}) or {}
    status = str(summary.get("status", "unknown")).lower()
    status_color = theme.get_status_color(status)
    status_icon = theme.get_status_icon(status)

    if results:
        table = formatter.table(headers=["Test", "Status", "Duration", "Notes"])
        for test_result in results:
            name = test_result.get("name", "unknown")
            result_status = str(test_result.get("status", "unknown")).lower()
            row_color = theme.get_status_color(result_status)
            row_icon = theme.get_status_icon(result_status)
            duration = _format_duration_ms(test_result.get("duration_ms"))
            notes = test_result.get("error") or test_result.get("stderr") or test_result.get("stdout") or ""
            if isinstance(notes, str):
                notes = notes.strip().splitlines()[0] if notes.strip() else ""
            table.add_row(
                name,
                f"[{row_color}]{row_icon} {result_status.upper()}[/{row_color}]",
                duration,
                notes,
            )
        formatter.console.print(table)
    else:
        formatter.print_warning("No individual test results returned")

    total_duration = _format_duration_ms(result.get("duration_ms"))
    summary_panel = (
        f"[bold]Total:[/bold] {summary.get('total', len(results))}\n"
        f"[bold]Passed:[/bold] {summary.get('passed', 0)}\n"
        f"[bold]Failed:[/bold] {summary.get('failed', 0)}\n"
        f"[bold]Skipped:[/bold] {summary.get('skipped', 0)}\n"
        f"[bold]Duration:[/bold] {total_duration}\n"
        f"[bold]Status:[/bold] [{status_color}]{status_icon} {status.upper()}[/{status_color}]"
    )
    if result.get("run_id"):
        summary_panel += f"\n[bold]Run ID:[/bold] {result['run_id']}"

    panel_title = "All Tests Passed" if status in {"green", "passed"} else "Tests Require Attention"
    formatter.print_info_panel(summary_panel, title=panel_title)

    if status not in {"green", "passed"}:
        formatter.print_warning("Some tests failed or require attention. Inspect the notes above and rerun after fixes.")


@click.group()
def ci() -> None:
    """Continuous integration helper commands."""


@ci.command("smoke")
@click.argument("repo_id")
@click.option("--commit", help="Commit hash to evaluate (defaults to trunk HEAD)")
def ci_smoke(repo_id: str, commit: Optional[str]) -> None:
    abort_with_error(
        "CI smoke tests are not yet available in headless CLI mode",
        details=f"Repository: {repo_id}\nCommit: {commit or 'HEAD'}",
        title="CI Smoke Tests Unavailable",
        help_text="Run smoke tests via the legacy CLI or integrate them into your CI pipeline.",
        suggestions=["evogitctl test run <workpad-id>", "evogitctl pad promote <workpad-id>"],
    )


@ci.command("rollback")
@click.argument("repo_id")
@click.option("--commit", required=True, help="Commit hash to rollback")
@click.option("--recreate-pad/--no-recreate-pad", default=True, show_default=True)
def ci_rollback(repo_id: str, commit: str, recreate_pad: bool) -> None:
    abort_with_error(
        "Rollback automation is not exposed via the headless CLI yet.",
        details=f"Repository: {repo_id}\nCommit: {commit}\nRecreate Pad: {'yes' if recreate_pad else 'no'}",
        title="Rollback Unsupported",
        help_text="Manually revert the commit or use the legacy workflows.",
    suggestions=[f"git revert {commit}", f"evogitctl pad create rollback-{commit[:8]}"],
    )


def _edit_commit_message(initial: str) -> str:
    """Open the user's editor to refine a commit message."""

    editor = os.getenv("EDITOR")
    if not editor:
        editor = "notepad" if os.name == "nt" else "vim"

    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt", encoding="utf-8") as handle:
        handle.write(initial)
        temp_path = Path(handle.name)

    try:
        subprocess.run([editor, str(temp_path)], check=True)
        return temp_path.read_text(encoding="utf-8").strip()
    finally:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass


@click.command("commit-msg")
@click.option("--workpad", "pad_id", required=True, help="Workpad ID")
@click.option("--edit/--no-edit", default=True, show_default=True, help="Edit message before checkpointing")
@click.option("--conventional/--free-form", default=True, show_default=True, help="Use conventional commit style")
@click.option("--checkpoint/--no-checkpoint", default=True, show_default=True, help="Checkpoint the workpad with the generated message")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def generate_commit_message(
    pad_id: str,
    edit: bool,
    conventional: bool,
    checkpoint: bool,
    output_json: bool,
) -> None:
    client = get_client()
    try:
        payload = client.generate_commit_message(pad_id, conventional=conventional)
    except HeadlessServiceError as exc:
        _handle_service_error(exc, json_output=output_json)
        return

    if output_json:
        data = dict(payload)
        data["success"] = True
        _emit_json(data)
        return

    commit_message = payload.get("message", "")
    formatter.print_info_panel(
        commit_message or "No commit message generated.",
        title="Generated Commit Message",
    )
    formatter.print_info(
        "Provider: {provider} • Model: {model} • Latency: {latency:.0f}ms • Cost: ${cost:.4f}".format(
            provider=payload.get("provider", "unknown"),
            model=payload.get("model", "unknown"),
            latency=payload.get("latency_ms", 0.0),
            cost=payload.get("cost_usd", 0.0),
        )
    )
    if payload.get("fallback_used"):
        formatter.print_warning("Primary provider failed; fallback was used.")

    final_message = commit_message
    if edit:
        edited_message = _edit_commit_message(commit_message)
        if not edited_message:
            abort_with_error("Commit message cannot be empty after editing.")
        final_message = edited_message

    if not checkpoint:
        formatter.print_info("Checkpoint skipped; use evogitctl pad checkpoint to save later.")
        return

    try:
        client.checkpoint_workpad(pad_id, final_message)
    except HeadlessServiceError as exc:
        _handle_service_error(exc, json_output=False)
        return

    formatter.print_success(f"Checkpointed workpad '{pad_id}' with AI-generated message")


@click.command("telemetry")
@click.option("--days", default=30, show_default=True, help="Number of days to analyze")
def show_telemetry(days: int) -> None:
    client = get_client()
    try:
        summary = client.get_telemetry_summary(days=days)
    except HeadlessServiceError as exc:
        _handle_service_error(exc, json_output=False)
        return

    formatter.print_header(f"AI Provider Usage (Last {days} days)")

    if not summary or summary.get("total_events", 0) == 0:
        formatter.print_warning("No telemetry data available")
        return

    formatter.print_info(f"Total Requests: {summary.get('total_events', 0)}")
    formatter.print_info(f"Total Cost: ${summary.get('total_cost_usd', 0.0):.4f}")
    formatter.print_info(f"Average Latency: {summary.get('avg_latency_ms', 0.0):.0f}ms")
    formatter.print_info(f"Fallback Rate: {summary.get('fallback_rate', 0.0):.1%}")
    formatter.print_info(f"Success Rate: {summary.get('success_rate', 0.0):.1%}")

    provider_usage = summary.get("provider_usage", {})
    if provider_usage:
        table = formatter.table(headers=["Provider", "Requests", "Percentage"])
        total_events = max(summary.get("total_events", 0), 1)
        for provider, count in provider_usage.items():
            percentage = (count / total_events) * 100
            table.add_row(provider, str(count), f"{percentage:.1f}%")
        formatter.console.print(table)


def execute_pair_loop(
    ctx: click.Context,
    prompt: str,
    repo_id: Optional[str],
    title: Optional[str],
    no_test: bool,
    no_promote: bool,
    target: str,
) -> None:
    abort_with_error(
        "The pair workflow is currently available via the Heaven GUI or automation APIs.",
        details="CLI-based pair programming is temporarily disabled while the headless service is finalized.",
        suggestions=["Launch the GUI: evogitctl gui", "Manually create a workpad: evogitctl pad create <title>"],
    )


__all__ = [
    "set_formatter_console",
    "abort_with_error",
    "repo",
    "pad",
    "test",
    "ci",
    "generate_commit_message",
    "show_telemetry",
    "execute_pair_loop",
    "_parse_test_override",
    "_tests_from_config_entries",
    "get_config_manager",
    "get_git_engine",
    "get_git_sync",
    "get_patch_engine",
    "get_test_orchestrator",
]
