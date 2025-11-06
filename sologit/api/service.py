"""Headless service layer for Solo Git operations."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple, Union

from sologit.config.manager import ConfigManager
from sologit.engines.git_engine import GitEngine, GitEngineError, WorkpadNotFoundError
from sologit.engines.patch_engine import PatchEngine
from sologit.engines.test_orchestrator import (
    TestConfig as EngineTestConfig,
    TestOrchestrator,
    TestResult as EngineTestResult,
)
from sologit.orchestration.ai_orchestrator import AIOrchestrator
from sologit.orchestration.commit_message_generator import (
    CommitMessageGenerator,
    CommitMessageRequest,
)
from sologit.orchestration.providers import ProviderConfig, ProviderType
from sologit.orchestration.providers.abacus_adapter import AbacusAdapter
from sologit.orchestration.providers.anthropic_adapter import AnthropicAdapter
from sologit.orchestration.providers.openai_adapter import OpenAIAdapter
from sologit.orchestration.routing_policy import PolicyEngine, RoutingPolicy
from sologit.orchestration.telemetry import TelemetryCollector
from sologit.state.git_sync import GitStateSync
from sologit.state.manager import StateManager
from sologit.state.schema import TestResult as StateTestResult
from sologit.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TestRunOutcome:
    """Container for test run results."""

    run_id: str
    summary: Dict[str, Any]
    results: List[Dict[str, Any]]
    duration_ms: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""

        return {
            "run_id": self.run_id,
            "summary": self.summary,
            "results": self.results,
            "duration_ms": self.duration_ms,
        }


class SoloGitService:
    """Unified service layer that powers all Solo Git interfaces."""

    def __init__(
        self,
        *,
        config_manager: Optional[ConfigManager] = None,
        git_state_sync: Optional[GitStateSync] = None,
        patch_engine: Optional[PatchEngine] = None,
        test_orchestrator: Optional[TestOrchestrator] = None,
        ai_orchestrator: Optional[AIOrchestrator] = None,
    ) -> None:
        self.config_manager = config_manager or ConfigManager()
        self.git_state_sync = git_state_sync or GitStateSync()
        self.git_engine: GitEngine = self.git_state_sync.git_engine
        self.state_manager: StateManager = self.git_state_sync.state_manager
        self.patch_engine = patch_engine or PatchEngine(self.git_engine)

        tests_config = self.config_manager.config.tests
        log_dir = Path(tests_config.log_dir).expanduser() if tests_config.log_dir else None
        self.test_orchestrator = test_orchestrator or TestOrchestrator(
            self.git_engine,
            sandbox_image=tests_config.sandbox_image,
            execution_mode=tests_config.execution_mode,
            log_dir=log_dir,
            formatter=None,
        )

        self.ai_orchestrator = ai_orchestrator or AIOrchestrator(self.config_manager)
        self._commit_message_generator: Optional[CommitMessageGenerator] = None
        self._telemetry_collector = TelemetryCollector()

    # ------------------------------------------------------------------
    # Repository operations
    # ------------------------------------------------------------------
    def list_repositories(self, include_state: bool = True) -> List[Dict[str, Any]]:
        """Return repositories tracked by Solo Git."""

        if include_state:
            repos = self.git_state_sync.list_repos()
            return [repo for repo in repos if repo]

        return [repo.to_dict() for repo in self.git_engine.list_repos()]

    def get_global_state(self) -> Dict[str, Any]:
        """Return the global Solo Git state."""

        state = self.state_manager.get_global_state()
        if hasattr(state, "to_dict"):
            return state.to_dict()
        return {
            "version": getattr(state, "version", "unknown"),
            "last_updated": getattr(state, "last_updated", datetime.utcnow().isoformat()),
            "active_repo": getattr(state, "active_repo", None),
            "active_workpad": getattr(state, "active_workpad", None),
            "session_start": getattr(state, "session_start", datetime.utcnow().isoformat()),
            "total_operations": getattr(state, "total_operations", 0),
            "total_cost_usd": getattr(state, "total_cost_usd", 0.0),
        }

    def get_repository(self, repo_id: str, include_state: bool = True) -> Optional[Dict[str, Any]]:
        """Retrieve repository metadata."""

        if include_state:
            return self.git_state_sync.get_repo(repo_id)

        repo = self.git_engine.get_repo(repo_id)
        return repo.to_dict() if repo else None

    def initialize_repository(
        self,
        *,
        zip_bytes: Optional[bytes] = None,
        git_url: Optional[str] = None,
        empty: bool = False,
        name: Optional[str] = None,
        target_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Initialize a repository from zip, git, or create an empty repo."""

        sources = {
            "zip": zip_bytes is not None,
            "git": git_url is not None,
            "empty": empty,
        }
        provided = [source for source, enabled in sources.items() if enabled]
        if len(provided) != 1:
            raise GitEngineError(
                "Please specify exactly one source: zip_bytes, git_url, or empty"
            )

        if empty:
            repo_name = name or (target_path.name if target_path else "solo-git-repo")
            return self.git_state_sync.create_empty_repo(
                repo_name,
                str(target_path) if target_path else None,
            )

        if zip_bytes is not None:
            if not name:
                raise GitEngineError("Repository name is required when importing from zip")
            return self.git_state_sync.init_repo_from_zip(zip_bytes, name)

        if git_url is None:
            raise GitEngineError("Git URL required for git initialization")

        repo_name = name or Path(git_url).stem.replace(".git", "")
        return self.git_state_sync.init_repo_from_git(git_url, repo_name)

    def delete_repository(self, repo_id: str, *, keep_files: bool = False) -> None:
        """Delete a repository and associated state."""

        self.git_state_sync.delete_repository(repo_id, remove_files=not keep_files)

    # ------------------------------------------------------------------
    # Workpad operations
    # ------------------------------------------------------------------
    def list_workpads(self, repo_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List workpads for a repository."""

        return [
            workpad for workpad in self.git_state_sync.list_workpads(repo_id) if workpad
        ]

    def get_workpad(self, pad_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve workpad metadata."""

        details = self.git_state_sync.get_workpad(pad_id)
        if not details:
            return None

        try:
            details["can_promote"] = self.git_engine.can_promote(pad_id)
        except GitEngineError:
            details["can_promote"] = False
        return details

    def create_workpad(self, repo_id: str, title: str) -> Dict[str, Any]:
        """Create a workpad and return its metadata."""

        result = self.git_state_sync.create_workpad(repo_id, title)
        pad_id = result.get("workpad_id")
        if not pad_id:
            raise GitEngineError("Workpad creation failed to return an identifier")
        workpad = self.git_state_sync.get_workpad(pad_id)
        if not workpad:
            raise GitEngineError("Workpad metadata not found after creation")
        return workpad

    def delete_workpad(self, pad_id: str, *, force: bool = False) -> None:
        """Delete a workpad."""

        self.git_state_sync.delete_workpad(pad_id, force=force)

    def can_promote(self, pad_id: str) -> bool:
        """Determine if the workpad is eligible for promotion."""

        workpad = self.git_engine.get_workpad(pad_id)
        if not workpad:
            raise WorkpadNotFoundError(f"Workpad {pad_id} not found")
        return self.git_engine.can_promote(pad_id)

    def promote_workpad(self, pad_id: str) -> Dict[str, Any]:
        """Promote a workpad and return promotion details."""

        workpad = self.git_engine.get_workpad(pad_id)
        if not workpad:
            raise WorkpadNotFoundError(f"Workpad {pad_id} not found")

        if not self.git_engine.can_promote(pad_id):
            raise GitEngineError("Workpad cannot be promoted: fast-forward required")

        commit_hash = self.git_engine.promote_workpad(pad_id)
        branch_name = getattr(workpad, "branch_name", "")

        return {
            "workpad_id": pad_id,
            "commit_hash": commit_hash,
            "branch_removed": branch_name,
            "promoted_at": datetime.utcnow().isoformat(),
        }

    def checkpoint_workpad(self, pad_id: str, message: str) -> Dict[str, Any]:
        """Checkpoint a workpad with the provided commit message."""

        workpad = self.git_engine.get_workpad(pad_id)
        if not workpad:
            raise WorkpadNotFoundError(f"Workpad {pad_id} not found")

        commit_hash = self.git_engine.checkpoint_workpad(pad_id, message)
        return {
            "workpad_id": pad_id,
            "commit_hash": commit_hash,
            "message": message,
        }

    def get_workpad_diff(self, pad_id: str) -> Dict[str, Any]:
        """Return diff data for the specified workpad."""

        workpad = self.git_engine.get_workpad(pad_id)
        if not workpad:
            raise WorkpadNotFoundError(f"Workpad {pad_id} not found")

        diff_text = self.git_engine.get_diff(pad_id)
        summary = self.git_engine.get_workpad_diff_summary(pad_id)
        return {
            "workpad_id": pad_id,
            "diff": diff_text or "",
            "summary": summary,
        }

    # ------------------------------------------------------------------
    # Test orchestration
    # ------------------------------------------------------------------
    def get_tests_for_target(self, target: str) -> List[EngineTestConfig]:
        """Resolve test definitions for the requested target."""

        target = target.lower()
        config = self.config_manager.config.tests
        default_timeout = config.timeout_seconds

        if target not in {"fast", "full"}:
            raise ValueError("target must be 'fast' or 'full'")

        entries: Optional[Sequence[Union[EngineTestConfig, Dict[str, Any]]]]
        if target == "fast":
            entries = config.fast_tests
        else:
            entries = config.full_tests or config.fast_tests

        tests = self._tests_from_entries(entries, default_timeout)

        if not tests:
            logger.warning("No test definitions found in configuration; using defaults")
            base_cmd = "python -m pytest tests/ -q"
            tests = [
                EngineTestConfig(name="unit-tests", cmd=base_cmd, timeout=default_timeout)
            ]
            if target == "full":
                tests.append(
                    EngineTestConfig(
                        name="integration",
                        cmd="python -m pytest tests/integration/ -q",
                        timeout=max(default_timeout * 2, 120),
                    )
                )
        return tests

    async def run_tests(
        self,
        pad_id: str,
        *,
        target: str = "fast",
        parallel: bool = True,
        on_output: Optional[Callable[[str, str, str], None]] = None,
        on_test_complete: Optional[Callable[[EngineTestResult], None]] = None,
    ) -> TestRunOutcome:
        """Execute tests for a workpad and synchronize state."""

        workpad = self.git_engine.get_workpad(pad_id)
        if not workpad:
            raise WorkpadNotFoundError(f"Workpad {pad_id} not found")

        run_info = self.git_state_sync.create_test_run(pad_id, target)
        run_id = run_info["run_id"]
        self.state_manager.update_test_run(run_id, status="running")

        tests = self.get_tests_for_target(target)
        results = await self.test_orchestrator.run_tests(
            pad_id,
            tests,
            parallel=parallel,
            on_output=on_output,
            on_test_complete=on_test_complete,
        )

        result_dicts: List[Dict[str, Any]] = [self._serialize_test_result(r) for r in results]
        summary = self.test_orchestrator.get_summary(results)
        duration_ms = sum(result.duration_ms for result in results)
        status = "passed" if summary["status"] == "green" else "failed"

        state_results = [
            StateTestResult(
                test_id=result["name"],
                name=result["name"],
                status=result["status"],
                duration_ms=result["duration_ms"],
                output=result.get("stdout", ""),
                error=result.get("error"),
            )
            for result in result_dicts
        ]

        self.state_manager.update_test_run(
            run_id,
            status=status,
            completed_at=datetime.utcnow().isoformat(),
            total_tests=summary["total"],
            passed=summary["passed"],
            failed=summary["failed"],
            skipped=summary["skipped"],
            duration_ms=duration_ms,
            tests=state_results,
        )

        return TestRunOutcome(
            run_id=run_id,
            summary=summary,
            results=result_dicts,
            duration_ms=duration_ms,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _tests_from_entries(
        self,
        entries: Optional[Sequence[Union[EngineTestConfig, Dict[str, Any]]]],
        default_timeout: int,
    ) -> List[EngineTestConfig]:
        """Normalize test definitions into EngineTestConfig objects."""

        if not entries:
            return []

        normalized: List[EngineTestConfig] = []
        for entry in entries:
            if isinstance(entry, EngineTestConfig):
                normalized.append(entry)
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
            depends_on_raw = entry.get("depends_on", []) or []
            if isinstance(depends_on_raw, list):
                depends_on = [str(dep).strip() for dep in depends_on_raw if dep]
            elif isinstance(depends_on_raw, str):
                depends_on = [depends_on_raw]
            else:
                logger.warning("Invalid depends_on for test entry: %s", entry)
                depends_on = []

            try:
                timeout = int(timeout_value) if timeout_value is not None else default_timeout
            except (TypeError, ValueError):
                logger.warning("Invalid timeout for test entry: %s", entry)
                timeout = default_timeout

            normalized.append(
                EngineTestConfig(
                    name=name,
                    cmd=cmd,
                    timeout=timeout,
                    depends_on=depends_on,
                )
            )
        return normalized

    def _serialize_test_result(self, result: EngineTestResult) -> Dict[str, Any]:
        """Convert engine test result into a JSON-ready dictionary."""

        status_value = getattr(result.status, "value", str(result.status))
        log_path = str(result.log_path) if result.log_path else None
        return {
            "name": result.name,
            "status": status_value,
            "duration_ms": result.duration_ms,
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "error": result.error,
            "log_path": log_path,
            "mode": result.mode,
            "metrics": result.metrics or {},
        }

    def get_workpad_diff(self, pad_id: str) -> Dict[str, Any]:
        """Return diff and summary information for the workpad."""

        workpad = self.git_engine.get_workpad(pad_id)
        if not workpad:
            raise WorkpadNotFoundError(f"Workpad {pad_id} not found")

        diff_text = self.git_engine.get_diff(pad_id)
        summary = self.git_engine.get_workpad_diff_summary(pad_id)
        return {
            "workpad_id": pad_id,
            "diff": diff_text or "",
            "summary": summary,
        }

    async def generate_commit_message(
        self,
        pad_id: str,
        *,
        conventional: bool = True,
    ) -> Dict[str, Any]:
        """Generate an AI-assisted commit message for a workpad."""

        workpad = self.git_engine.get_workpad(pad_id)
        if not workpad:
            raise WorkpadNotFoundError(f"Workpad {pad_id} not found")

        diff_text = self.git_engine.get_diff(pad_id)
        if not diff_text:
            raise GitEngineError("No changes detected for commit message generation")

        generator = self._get_commit_message_generator()
        request = CommitMessageRequest(
            diff=diff_text,
            workpad_title=getattr(workpad, "title", pad_id),
            conventional_commit=conventional,
        )

        response = await generator.generate(request)
        return {
            "message": response.message,
            "provider": response.provider.value,
            "model": response.model,
            "latency_ms": response.latency_ms,
            "cost_usd": response.cost_usd,
            "fallback_used": response.fallback_used,
            "workpad_id": pad_id,
            "diff": diff_text,
        }

    def get_telemetry_summary(self, days: int = 30) -> Dict[str, Any]:
        """Return AI telemetry summary for the specified timeframe."""

        summary = self._telemetry_collector.get_summary(days=days)
        return summary

    def _get_commit_message_generator(self) -> CommitMessageGenerator:
        """Create or return cached commit message generator."""

        if self._commit_message_generator is not None:
            return self._commit_message_generator

        adapters = self._build_provider_adapters()
        policy = RoutingPolicy()
        engine = PolicyEngine(policy, adapters)
        self._commit_message_generator = CommitMessageGenerator(engine, self._telemetry_collector)
        return self._commit_message_generator

    def _build_provider_adapters(self) -> Dict[ProviderType, Any]:
        """Construct provider adapters from configuration."""

        adapters: Dict[ProviderType, Any] = {}
        config = self.config_manager.config

        # Abacus primary provider
        abacus_config = getattr(config, "abacus", None)
        api_key = getattr(abacus_config, "api_key", None)
        if api_key:
            provider_config = ProviderConfig(provider_type=ProviderType.ABACUS, api_key=api_key, enabled=True)
            if hasattr(abacus_config, "deployment_id"):
                setattr(provider_config, "deployment_id", getattr(abacus_config, "deployment_id"))
            if hasattr(abacus_config, "deployment_token"):
                setattr(provider_config, "deployment_token", getattr(abacus_config, "deployment_token"))
            adapters[ProviderType.ABACUS] = AbacusAdapter(provider_config)

        # OpenAI fallback
        openai_key = getattr(config, "openai_api_key", None)
        if openai_key:
            adapters[ProviderType.OPENAI] = OpenAIAdapter(
                ProviderConfig(provider_type=ProviderType.OPENAI, api_key=openai_key, enabled=True)
            )

        # Anthropic fallback
        anthropic_key = getattr(config, "anthropic_api_key", None)
        if anthropic_key:
            adapters[ProviderType.ANTHROPIC] = AnthropicAdapter(
                ProviderConfig(provider_type=ProviderType.ANTHROPIC, api_key=anthropic_key, enabled=True)
            )

        if not adapters:
            raise GitEngineError(
                "No AI providers configured. Set abacus.api_key, openai_api_key, or anthropic_api_key in config."
            )

        return adapters


__all__ = ["SoloGitService", "TestRunOutcome"]
