"""Auto-merge workflow for Solo Git with CI integration and state recording."""

import os
import shlex
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING, Tuple

import requests

from sologit.analysis.test_analyzer import TestAnalyzer, TestAnalysis
from sologit.engines.git_engine import GitEngine
from sologit.engines.test_orchestrator import (
    TestConfig,
    TestOrchestrator,
    TestResult as EngineTestResult,
    TestStatus,
)
from sologit.state.schema import TestResult as StateTestResult
from sologit.utils.logger import get_logger
from sologit.workflows.ci_orchestrator import CIOrchestrator, CIResult, CIStatus
from sologit.workflows.promotion_gate import PromotionDecision, PromotionGate, PromotionRules

if TYPE_CHECKING:
    from sologit.config.manager import CISmokeConfig
    from sologit.state.manager import StateManager
    from sologit.workflows.rollback_handler import RollbackHandler

logger = get_logger(__name__)


@dataclass
class AutoMergeResult:
    """Result of auto-merge workflow."""
    success: bool
    pad_id: str
    commit_hash: Optional[str] = None
    test_analysis: Optional[TestAnalysis] = None
    promotion_decision: Optional[PromotionDecision] = None
    ci_result: Optional[CIResult] = None
    message: str = ""
    details: List[str] = field(default_factory=list)


class AutoMergeWorkflow:
    """
    Orchestrates the complete auto-merge workflow.
    
    Steps:
    1. Run tests in workpad
    2. Analyze test results
    3. Evaluate promotion gate
    4. Auto-promote if approved
    5. Optionally trigger CI smoke tests
    """
    
    def __init__(
        self,
        git_engine: GitEngine,
        test_orchestrator: TestOrchestrator,
        promotion_rules: Optional[PromotionRules] = None,
        *,
        state_manager: Optional["StateManager"] = None,
        ci_orchestrator: Optional[CIOrchestrator] = None,
        rollback_handler: Optional["RollbackHandler"] = None,
        ci_smoke_tests: Optional[List[TestConfig]] = None,
        ci_config: Optional["CISmokeConfig"] = None,
        rollback_on_ci_red: bool = True,
    ):
        """
        Initialize auto-merge workflow.
        
        Args:
            git_engine: GitEngine instance
            test_orchestrator: TestOrchestrator instance
            promotion_rules: Promotion rules (uses defaults if None)
        """
        self.git_engine = git_engine
        self.test_orchestrator = test_orchestrator
        self.test_analyzer = TestAnalyzer()
        self.promotion_gate = PromotionGate(git_engine, promotion_rules)
        self.state_manager = state_manager
        self.ci_orchestrator = ci_orchestrator
        self.rollback_handler = rollback_handler
        self.ci_smoke_tests = list(ci_smoke_tests or [])
        self.ci_config = ci_config
        self.rollback_on_ci_red = rollback_on_ci_red

        logger.info("AutoMergeWorkflow initialized")
    
    def execute(
        self,
        pad_id: str,
        tests: List[TestConfig],
        parallel: bool = True,
        auto_promote: bool = True,
        target: str = "custom"
    ) -> AutoMergeResult:
        """
        Execute auto-merge workflow.
        
        Args:
            pad_id: Workpad ID
            tests: Test configurations to run
            parallel: Run tests in parallel
            auto_promote: Automatically promote if approved
            target: Configured test target label (fast/full/custom)
            
        Returns:
            AutoMergeResult with outcome
        """
        logger.info(f"Starting auto-merge workflow for pad {pad_id}")
        
        result = AutoMergeResult(success=False, pad_id=pad_id)

        # Get workpad info
        workpad = self.git_engine.get_workpad(pad_id)
        if not workpad:
            result.message = f"Workpad {pad_id} not found"
            result.details.append("❌ " + result.message)
            return result

        repo_id = getattr(workpad, 'repo_id', None)

        result.details.append(f"📝 Workpad: {workpad.title}")
        if target:
            result.details.append(f"🎯 Target: {target}")

        test_run_id = self._start_test_run(pad_id, target)
        
        # Step 1: Run tests
        logger.info(f"Step 1: Running {len(tests)} tests")
        result.details.append(f"\n🧪 Running {len(tests)} tests...")

        test_results: List[EngineTestResult] = []
        try:
            test_results = self.test_orchestrator.run_tests_sync(pad_id, tests, parallel)
            result.details.append(f"   Tests completed in {sum(r.duration_ms for r in test_results)/1000:.1f}s")
        except Exception as e:
            result.message = f"Test execution failed: {e}"
            result.details.append(f"❌ {result.message}")
            logger.error(result.message, exc_info=True)
            self._finalize_test_run(test_run_id, test_results, "failed")
            return result

        # Step 2: Analyze results
        logger.info("Step 2: Analyzing test results")
        result.details.append("\n📊 Analyzing test results...")

        analysis: Optional[TestAnalysis] = None
        try:
            analysis = self.test_analyzer.analyze(test_results)
            result.test_analysis = analysis

            result.details.append(f"   Status: {analysis.status.upper()}")
            result.details.append(f"   Passed: {analysis.passed}/{analysis.total_tests}")

            if analysis.status != "green":
                result.details.append(f"   Failed: {analysis.failed}")
                if analysis.timeout > 0:
                    result.details.append(f"   Timeout: {analysis.timeout}")
                if analysis.error > 0:
                    result.details.append(f"   Error: {analysis.error}")
                
                # Show failure patterns
                if analysis.failure_patterns:
                    result.details.append("\n   Failure Patterns:")
                    for pattern in analysis.failure_patterns[:3]:  # Show top 3
                        result.details.append(f"     • {pattern.category.value}: {pattern.message[:80]}")
                
                # Show suggestions
                if analysis.suggested_actions:
                    result.details.append("\n   Suggested Actions:")
                    for action in analysis.suggested_actions[:3]:  # Show top 3
                        result.details.append(f"     • {action}")
        
        except Exception as e:
            result.message = f"Test analysis failed: {e}"
            result.details.append(f"❌ {result.message}")
            logger.error(result.message, exc_info=True)
            self._finalize_test_run(test_run_id, test_results, "failed")
            return result

        self._finalize_test_run(
            test_run_id,
            test_results,
            "passed" if analysis and analysis.status == "green" else "failed",
        )

        # Step 3: Evaluate promotion gate
        logger.info("Step 3: Evaluating promotion gate")
        result.details.append("\n🚦 Evaluating promotion gate...")
        
        try:
            decision = self.promotion_gate.evaluate(pad_id, analysis)
            result.promotion_decision = decision
            
            # Show key reasons
            for reason in decision.reasons[:5]:  # Show top 5
                result.details.append(f"   {reason}")
            
            # Show warnings
            for warning in decision.warnings:
                result.details.append(f"   {warning}")
        
        except Exception as e:
            result.message = f"Promotion gate evaluation failed: {e}"
            result.details.append(f"❌ {result.message}")
            logger.error(result.message, exc_info=True)
            return result
        
        # Step 4: Auto-promote if approved
        ci_result: Optional[CIResult] = None

        if decision.can_promote and auto_promote:
            logger.info("Step 4: Auto-promoting to trunk")
            result.details.append("\n🚀 Auto-promoting to trunk...")

            try:
                commit_hash = self.git_engine.promote_workpad(pad_id)
                result.commit_hash = commit_hash
                result.success = True
                result.message = f"Successfully promoted to trunk"
                result.details.append(f"✅ Promoted to trunk: {commit_hash[:8]}")

                logger.info(f"Auto-merge successful: {commit_hash}")

            except Exception as e:
                result.message = f"Promotion failed: {e}"
                result.details.append(f"❌ {result.message}")
                logger.error(result.message, exc_info=True)
                return result

        elif decision.can_promote:
            result.message = "Tests passed, ready to promote (auto-promote disabled)"
            result.details.append(f"\n✅ {result.message}")
            result.details.append("   Run 'sologit pad promote' to merge manually")

        else:
            result.message = "Cannot promote - promotion gate rejected"
            result.details.append(f"\n❌ {result.message}")

            if decision.decision.value == "manual_review":
                result.details.append("   👀 Manual review required")

            result.details.append("\n   Fix the issues and try again:")
            result.details.append("   1. Address test failures")
            result.details.append("   2. Re-run tests: sologit test run <pad-id>")
            result.details.append("   3. Try again: sologit pad auto-merge <pad-id>")

        if result.commit_hash and repo_id:
            ci_result = self._run_ci_pipeline(repo_id, result.commit_hash, result)
            result.ci_result = ci_result

            if ci_result and ci_result.is_red:
                result.success = False
                if "Successfully promoted" in result.message:
                    result.message = "Promotion rolled back due to failed CI smoke tests"

        self._record_promotion_decision(
            repo_id=repo_id,
            workpad_id=pad_id,
            decision=decision,
            auto_promote_requested=auto_promote,
            promoted=bool(result.commit_hash) and not (
                ci_result and ci_result.is_red and self.rollback_on_ci_red
            ),
            commit_hash=result.commit_hash,
            message=result.message,
            test_run_id=test_run_id,
            ci_result=ci_result,
        )

        return result

    def _start_test_run(self, pad_id: str, target: str) -> Optional[str]:
        """Create a test run entry in the state manager."""
        if not self.state_manager:
            return None

        try:
            run = self.state_manager.create_test_run(pad_id, target)
            self.state_manager.update_test_run(run.run_id, status="running")
            return run.run_id
        except Exception as exc:
            logger.warning("Failed to record test run start for %s: %s", pad_id, exc)
            return None

    def _finalize_test_run(
        self,
        run_id: Optional[str],
        test_results: List[EngineTestResult],
        status: str,
    ) -> None:
        """Persist final test run results to state manager."""
        if not self.state_manager or not run_id:
            return

        try:
            state_results = []
            for index, test in enumerate(test_results, start=1):
                state_status = "passed" if test.status == TestStatus.PASSED else "failed"
                state_results.append(
                    StateTestResult(
                        test_id=f"{run_id}-{index}",
                        name=test.name,
                        status=state_status,
                        duration_ms=test.duration_ms,
                        output=(test.stdout or ""),
                        error=test.error or test.stderr or None,
                    )
                )

            total = len(test_results)
            passed = sum(1 for test in test_results if test.status == TestStatus.PASSED)
            failed = total - passed
            duration = sum(test.duration_ms for test in test_results)

            self.state_manager.update_test_run(
                run_id,
                status=status,
                completed_at=datetime.utcnow().isoformat(),
                total_tests=total,
                passed=passed,
                failed=failed,
                duration_ms=duration,
                tests=state_results,
            )
        except Exception as exc:
            logger.warning("Failed to finalize test run %s: %s", run_id, exc)

    def _record_promotion_decision(
        self,
        *,
        repo_id: Optional[str],
        workpad_id: str,
        decision: PromotionDecision,
        auto_promote_requested: bool,
        promoted: bool,
        commit_hash: Optional[str],
        message: str,
        test_run_id: Optional[str],
        ci_result: Optional[CIResult],
    ) -> None:
        """Persist promotion decisions for history tracking."""
        if not self.state_manager or not repo_id:
            return

        try:
            self.state_manager.record_promotion_decision(
                repo_id=repo_id,
                workpad_id=workpad_id,
                decision=decision,
                auto_promote_requested=auto_promote_requested,
                promoted=promoted,
                commit_hash=commit_hash,
                message=message,
                test_run_id=test_run_id,
                ci_status=ci_result.status.value if ci_result else None,
                ci_message=ci_result.message if ci_result else None,
            )
        except Exception as exc:
            logger.warning("Failed to record promotion decision for %s: %s", workpad_id, exc)

    def _run_ci_pipeline(
        self,
        repo_id: str,
        commit_hash: str,
        result: AutoMergeResult,
    ) -> Optional[CIResult]:
        """Execute configured CI smoke jobs and handle rollback if needed."""
        if not self.ci_config or not self.ci_config.auto_run:
            logger.info("CI auto-run disabled")
            return None

        result.details.append("\n🔬 Triggering CI smoke job...")

        ci_result: Optional[CIResult] = None

        if self.ci_orchestrator and self.ci_smoke_tests:
            try:
                ci_result = self.ci_orchestrator.run_smoke_tests(
                    repo_id,
                    commit_hash,
                    self.ci_smoke_tests,
                )
                result.details.append(
                    f"   Smoke tests: {ci_result.status.value.upper()} - {ci_result.message}"
                )
            except Exception as exc:
                logger.error("Smoke tests execution failed: %s", exc, exc_info=True)
                result.details.append(f"   ❌ Smoke tests failed to run: {exc}")
                ci_result = CIResult(
                    repo_id=repo_id,
                    commit_hash=commit_hash,
                    status=CIStatus.FAILURE,
                    duration_ms=0,
                    test_results=[],
                    message=str(exc),
                )
        elif self.ci_smoke_tests:
            result.details.append(
                "   ⚠️ Smoke tests configured but CI orchestrator unavailable"
            )

        if self.ci_config.command:
            success, message = self._run_ci_command(
                self.ci_config.command,
                repo_id,
                commit_hash,
            )
            detail = "✅" if success else "❌"
            trimmed = (message or "").strip()
            if len(trimmed) > 120:
                trimmed = trimmed[:117] + "..."
            detail_line = f"   {detail} CI command: {self.ci_config.command}"
            if trimmed:
                detail_line += f" -> {trimmed}"
            result.details.append(detail_line)

            if not success:
                if ci_result:
                    ci_result.status = CIStatus.FAILURE
                    ci_result.message = f"CI command failed: {message}"
                else:
                    ci_result = CIResult(
                        repo_id=repo_id,
                        commit_hash=commit_hash,
                        status=CIStatus.FAILURE,
                        duration_ms=0,
                        test_results=[],
                        message=f"CI command failed: {message}",
                    )
            elif not ci_result:
                ci_result = CIResult(
                    repo_id=repo_id,
                    commit_hash=commit_hash,
                    status=CIStatus.SUCCESS,
                    duration_ms=0,
                    test_results=[],
                    message="CI command succeeded",
                )

        if self.ci_config.webhook:
            success, message = self._trigger_ci_webhook(
                self.ci_config.webhook,
                repo_id,
                commit_hash,
            )
            detail = "✅" if success else "❌"
            trimmed = (message or "").strip()
            if len(trimmed) > 120:
                trimmed = trimmed[:117] + "..."
            detail_line = f"   {detail} CI webhook: {self.ci_config.webhook}"
            if trimmed:
                detail_line += f" -> {trimmed}"
            result.details.append(detail_line)

            if not success:
                if ci_result:
                    ci_result.status = CIStatus.FAILURE
                    ci_result.message = f"CI webhook failed: {message}"
                else:
                    ci_result = CIResult(
                        repo_id=repo_id,
                        commit_hash=commit_hash,
                        status=CIStatus.FAILURE,
                        duration_ms=0,
                        test_results=[],
                        message=f"CI webhook failed: {message}",
                    )
            elif not ci_result:
                ci_result = CIResult(
                    repo_id=repo_id,
                    commit_hash=commit_hash,
                    status=CIStatus.SUCCESS,
                    duration_ms=0,
                    test_results=[],
                    message="CI webhook triggered",
                )

        if ci_result and ci_result.is_red and self.rollback_on_ci_red and self.rollback_handler:
            try:
                rollback = self.rollback_handler.handle_failed_ci(ci_result)
                if rollback:
                    status_icon = "✅" if rollback.success else "❌"
                    result.details.append(
                        f"\n🔄 Rollback: {status_icon} {rollback.message}"
                    )
            except Exception as exc:
                logger.error("Rollback handler failed: %s", exc, exc_info=True)
                result.details.append(f"   ❌ Rollback failed: {exc}")

        return ci_result

    def _run_ci_command(
        self,
        command: str,
        repo_id: str,
        commit_hash: str,
    ) -> Tuple[bool, str]:
        """Execute configured CI command and return success status."""
        if not command.strip():
            return True, ""

        try:
            args = shlex.split(command)
        except ValueError as exc:
            logger.error("Invalid CI command '%s': %s", command, exc)
            return False, str(exc)

        try:
            completed = subprocess.run(
                args,
                check=False,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    "SOLOGIT_REPO_ID": repo_id,
                    "SOLOGIT_COMMIT": commit_hash,
                },
            )
        except Exception as exc:
            logger.error("CI command execution failed: %s", exc, exc_info=True)
            return False, str(exc)

        output = completed.stdout.strip() or completed.stderr.strip()
        return completed.returncode == 0, output

    def _trigger_ci_webhook(
        self,
        url: str,
        repo_id: str,
        commit_hash: str,
    ) -> Tuple[bool, str]:
        """Trigger configured CI webhook."""
        if not url:
            return True, ""

        try:
            response = requests.post(
                url,
                json={
                    "repo_id": repo_id,
                    "commit": commit_hash,
                },
                timeout=getattr(self.ci_config, 'webhook_timeout', 10),
            )
            success = response.status_code < 400
            message = response.text.strip()
            if not success:
                logger.error(
                    "CI webhook %s failed with status %s", url, response.status_code
                )
            return success, message
        except Exception as exc:
            logger.error("CI webhook call failed: %s", exc, exc_info=True)
            return False, str(exc)
    
    def format_result(self, result: AutoMergeResult) -> str:
        """Format auto-merge result for display."""
        lines = []
        
        lines.append("=" * 60)
        lines.append("AUTO-MERGE WORKFLOW RESULT")
        lines.append("=" * 60)
        lines.append("")
        
        # Status
        if result.success:
            lines.append("✅ SUCCESS")
        else:
            lines.append("❌ FAILED")
        
        lines.append(f"   {result.message}")
        lines.append("")
        
        # Details
        if result.details:
            lines.extend(result.details)
            lines.append("")
        
        # Commit hash if promoted
        if result.commit_hash:
            lines.append(f"📌 Commit: {result.commit_hash}")
            lines.append("")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)
