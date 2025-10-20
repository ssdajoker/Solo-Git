"""
CI orchestrator for post-merge smoke tests.

Runs smoke tests after promotion to trunk and coordinates rollback if needed.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import List, Optional, Callable
from enum import Enum

from sologit.engines.git_engine import GitEngine
from sologit.engines.test_orchestrator import TestOrchestrator, TestConfig, TestResult, TestStatus
from sologit.utils.logger import get_logger

logger = get_logger(__name__)


class CIStatus(Enum):
    """CI pipeline status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    UNSTABLE = "unstable"
    ABORTED = "aborted"


@dataclass
class CIResult:
    """Result of CI pipeline execution."""
    repo_id: str
    commit_hash: str
    status: CIStatus
    duration_ms: int
    test_results: List[TestResult]
    message: str = ""
    
    @property
    def is_green(self) -> bool:
        """Check if CI passed."""
        return self.status == CIStatus.SUCCESS
    
    @property
    def is_red(self) -> bool:
        """Check if CI failed."""
        return self.status in [CIStatus.FAILURE, CIStatus.UNSTABLE]


class CIOrchestrator:
    """
    Orchestrates CI smoke tests after promotion.
    
    This is a simplified CI system that runs smoke tests after code
    is promoted to trunk. In production, this would integrate with
    Jenkins, GitHub Actions, or another CI system.
    """
    
    def __init__(
        self,
        git_engine: GitEngine,
        test_orchestrator: TestOrchestrator
    ):
        """
        Initialize CI orchestrator.
        
        Args:
            git_engine: GitEngine instance
            test_orchestrator: TestOrchestrator instance
        """
        self.git_engine = git_engine
        self.test_orchestrator = test_orchestrator
        logger.info("CIOrchestrator initialized")
    
    def run_smoke_tests(
        self,
        repo_id: str,
        commit_hash: str,
        smoke_tests: List[TestConfig],
        on_progress: Optional[Callable[[str], None]] = None
    ) -> CIResult:
        """
        Run smoke tests for a commit.
        
        Args:
            repo_id: Repository ID
            commit_hash: Commit hash to test
            smoke_tests: Smoke test configurations
            on_progress: Progress callback (optional)
            
        Returns:
            CIResult with test outcomes
        """
        logger.info(f"Running smoke tests for {repo_id}@{commit_hash[:8]}")
        
        start_time = time.time()
        
        if on_progress:
            on_progress(f"🔬 Starting smoke tests for commit {commit_hash[:8]}...")
        
        # Get repository
        repo = self.git_engine.get_repo(repo_id)
        if not repo:
            logger.error(f"Repository {repo_id} not found")
            return CIResult(
                repo_id=repo_id,
                commit_hash=commit_hash,
                status=CIStatus.FAILURE,
                duration_ms=0,
                test_results=[],
                message="Repository not found"
            )
        
        # Create temporary workpad for testing
        # (We test on trunk, but use a workpad abstraction to isolate)
        try:
            # Note: In production, we'd checkout the specific commit
            # For now, we assume trunk is at the commit we want to test
            history = self.git_engine.get_history(repo_id, limit=1)
            if not history:
                raise Exception("No commits found in repository")
            
            if on_progress:
                on_progress(f"Running {len(smoke_tests)} smoke tests...")
            
            # Run smoke tests
            # Create a temp workpad to use the test orchestrator
            temp_pad = self.git_engine.create_workpad(repo_id, f"ci-smoke-{commit_hash[:8]}")
            
            try:
                results = self.test_orchestrator.run_tests_sync(
                    temp_pad.id,
                    smoke_tests,
                    parallel=True
                )
                
                # Determine status
                all_passed = all(r.status == TestStatus.PASSED for r in results)
                any_failed = any(r.status == TestStatus.FAILED for r in results)
                any_timeout = any(r.status == TestStatus.TIMEOUT for r in results)
                
                if all_passed:
                    status = CIStatus.SUCCESS
                    message = "All smoke tests passed"
                elif any_timeout:
                    status = CIStatus.UNSTABLE
                    message = "Some tests timed out"
                else:
                    status = CIStatus.FAILURE
                    message = f"{sum(1 for r in results if r.status != TestStatus.PASSED)} tests failed"
                
                duration_ms = int((time.time() - start_time) * 1000)
                
                if on_progress:
                    on_progress(f"✅ Smoke tests complete: {status.value}")
                
                return CIResult(
                    repo_id=repo_id,
                    commit_hash=commit_hash,
                    status=status,
                    duration_ms=duration_ms,
                    test_results=results,
                    message=message
                )
            
            finally:
                # Clean up temp workpad
                try:
                    self.git_engine.delete_workpad(temp_pad.id)
                except:
                    pass
        
        except Exception as e:
            logger.error(f"Smoke tests failed: {e}", exc_info=True)
            duration_ms = int((time.time() - start_time) * 1000)
            
            if on_progress:
                on_progress(f"❌ Smoke tests failed: {e}")
            
            return CIResult(
                repo_id=repo_id,
                commit_hash=commit_hash,
                status=CIStatus.FAILURE,
                duration_ms=duration_ms,
                test_results=[],
                message=str(e)
            )
    
    async def run_smoke_tests_async(
        self,
        repo_id: str,
        commit_hash: str,
        smoke_tests: List[TestConfig],
        on_progress: Optional[Callable[[str], None]] = None
    ) -> CIResult:
        """
        Run smoke tests asynchronously.
        
        Args:
            repo_id: Repository ID
            commit_hash: Commit hash to test
            smoke_tests: Smoke test configurations
            on_progress: Progress callback (optional)
            
        Returns:
            CIResult with test outcomes
        """
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self.run_smoke_tests,
            repo_id,
            commit_hash,
            smoke_tests,
            on_progress
        )
        return result
    
    def format_result(self, result: CIResult) -> str:
        """Format CI result for display."""
        lines = []
        
        lines.append("=" * 60)
        lines.append("CI SMOKE TESTS")
        lines.append("=" * 60)
        lines.append("")
        
        # Status
        if result.status == CIStatus.SUCCESS:
            lines.append("✅ SUCCESS")
        elif result.status == CIStatus.FAILURE:
            lines.append("❌ FAILURE")
        elif result.status == CIStatus.UNSTABLE:
            lines.append("⚠️ UNSTABLE")
        else:
            lines.append(f"📊 {result.status.value.upper()}")
        
        lines.append(f"   {result.message}")
        lines.append("")
        
        # Details
        lines.append(f"Repository: {result.repo_id}")
        lines.append(f"Commit: {result.commit_hash}")
        lines.append(f"Duration: {result.duration_ms/1000:.1f}s")
        lines.append("")
        
        # Test results
        if result.test_results:
            lines.append(f"Tests: {len(result.test_results)}")
            passed = sum(1 for r in result.test_results if r.status == TestStatus.PASSED)
            failed = sum(1 for r in result.test_results if r.status == TestStatus.FAILED)
            timeout = sum(1 for r in result.test_results if r.status == TestStatus.TIMEOUT)
            
            lines.append(f"  ✅ Passed: {passed}")
            if failed > 0:
                lines.append(f"  ❌ Failed: {failed}")
            if timeout > 0:
                lines.append(f"  ⏱️ Timeout: {timeout}")
            
            lines.append("")
            
            # Show failed tests
            failures = [r for r in result.test_results if r.status != TestStatus.PASSED]
            if failures:
                lines.append("Failed Tests:")
                for test in failures:
                    lines.append(f"  • {test.name} ({test.status.value})")
        
        lines.append("")
        lines.append("=" * 60)
        
        return "\n".join(lines)
