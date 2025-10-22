"""
Automatic rollback handler for failed CI builds.

Reverts failed commits and recreates workpads for fixes.
"""

from dataclasses import dataclass
from typing import Optional

from sologit.engines.git_engine import GitEngine, GitEngineError
from sologit.workflows.ci_orchestrator import CIResult
from sologit.utils.logger import get_logger
from sologit.core.workpad import Workpad

logger = get_logger(__name__)


@dataclass
class RollbackResult:
    """Result of rollback operation."""
    success: bool
    repo_id: str
    reverted_commit: str
    new_pad_id: Optional[str] = None
    message: str = ""


class RollbackHandler:
    """
    Handles automatic rollback of failed commits.
    
    When CI smoke tests fail after promotion, this handler:
    1. Reverts the commit from trunk
    2. Recreates a workpad with the reverted changes
    3. Allows developer to fix and retry
    """
    
    def __init__(self, git_engine: GitEngine):
        """
        Initialize rollback handler.
        
        Args:
            git_engine: GitEngine instance
        """
        self.git_engine = git_engine
        logger.info("RollbackHandler initialized")
    
    def handle_failed_ci(
        self,
        ci_result: CIResult,
        recreate_workpad: bool = True
    ) -> RollbackResult:
        """
        Handle a failed CI build by rolling back.
        
        Args:
            ci_result: Failed CI result
            recreate_workpad: Whether to recreate workpad for fixes
            
        Returns:
            RollbackResult with outcome
        """
        logger.info(f"Handling failed CI for {ci_result.repo_id}@{ci_result.commit_hash[:8]}")
        
        repo_id = ci_result.repo_id
        commit_hash = ci_result.commit_hash
        
        # Check if CI actually failed
        if not ci_result.is_red:
            logger.warning("CI did not fail, no rollback needed")
            return RollbackResult(
                success=True,
                repo_id=repo_id,
                reverted_commit=commit_hash,
                message="CI passed - no rollback needed"
            )
        
        # Step 1: Revert the commit
        logger.info(f"Reverting commit {commit_hash[:8]}")
        
        try:
            self.git_engine.revert_last_commit(repo_id)
            logger.info("Commit reverted successfully")
        except GitEngineError as e:
            logger.error(f"Failed to revert commit: {e}", exc_info=True)
            return RollbackResult(
                success=False,
                repo_id=repo_id,
                reverted_commit=commit_hash,
                message=f"Rollback failed: {e}"
            )
        
        # Step 2: Recreate workpad if requested
        new_pad_id = None
        
        if recreate_workpad:
            logger.info("Recreating workpad for fixes")
            
            try:
                # Get the diff from the reverted commit
                repo = self.git_engine.get_repo(repo_id)
                
                # Create new workpad with "fix" prefix
                pad_title = f"fix-ci-{commit_hash[:7]}"
                new_pad = self.git_engine.create_workpad(repo_id, pad_title)
                if isinstance(new_pad, Workpad):
                    new_pad_id = new_pad.id
                else:
                    new_pad_id = new_pad
                
                # Note: The changes are already in trunk history, so we don't
                # need to reapply them to the workpad. The developer can cherry-pick
                # or manually apply fixes.
                
                logger.info(f"Workpad recreated: {new_pad_id}")
            
            except Exception as e:
                logger.error(f"Failed to recreate workpad: {e}", exc_info=True)
                # Don't fail the whole rollback if workpad creation fails
                logger.warning("Rollback succeeded but workpad recreation failed")
        
        message = (
            f"Rolled back commit {commit_hash[:8]} due to failed CI smoke tests. "
        )
        
        if new_pad_id:
            message += f"Created workpad {new_pad_id} for fixes."
        
        return RollbackResult(
            success=True,
            repo_id=repo_id,
            reverted_commit=commit_hash,
            new_pad_id=new_pad_id,
            message=message
        )
    
    def format_result(self, result: RollbackResult) -> str:
        """Format rollback result for display."""
        lines = []
        
        lines.append("=" * 60)
        lines.append("AUTOMATIC ROLLBACK")
        lines.append("=" * 60)
        lines.append("")
        
        if result.success:
            lines.append("✅ ROLLBACK SUCCESSFUL")
        else:
            lines.append("❌ ROLLBACK FAILED")
        
        lines.append(f"   {result.message}")
        lines.append("")
        
        lines.append(f"Repository: {result.repo_id}")
        lines.append(f"Reverted Commit: {result.reverted_commit}")
        
        if result.new_pad_id:
            lines.append(f"New Workpad: {result.new_pad_id}")
            lines.append("")
            lines.append("To fix the issues:")
            lines.append(f"  1. Work in workpad: {result.new_pad_id}")
            lines.append("  2. Fix the failing tests")
            lines.append("  3. Run tests: sologit test run <pad-id>")
            lines.append("  4. Try auto-merge again: sologit pad auto-merge <pad-id>")
        
        lines.append("")
        lines.append("=" * 60)
        
        return "\n".join(lines)


class CIMonitor:
    """
    Monitors CI builds and triggers rollback on failure.
    
    This would run in the background after promotions to watch CI results.
    """
    
    def __init__(
        self,
        git_engine: GitEngine,
        rollback_handler: RollbackHandler
    ):
        """
        Initialize CI monitor.
        
        Args:
            git_engine: GitEngine instance
            rollback_handler: RollbackHandler instance
        """
        self.git_engine = git_engine
        self.rollback_handler = rollback_handler
        logger.info("CIMonitor initialized")
    
    def monitor_and_rollback(
        self,
        ci_result: CIResult,
        auto_rollback: bool = True
    ) -> Optional[RollbackResult]:
        """
        Monitor CI result and rollback if failed.
        
        Args:
            ci_result: CI result to monitor
            auto_rollback: Whether to automatically rollback on failure
            
        Returns:
            RollbackResult if rollback performed, None otherwise
        """
        logger.info(f"Monitoring CI result for {ci_result.repo_id}@{ci_result.commit_hash[:8]}")
        
        # Check if CI failed
        if ci_result.is_red:
            logger.warning(f"CI failed for {ci_result.commit_hash[:8]}")
            
            if auto_rollback:
                logger.info("Auto-rollback enabled, initiating rollback")
                rollback_result = self.rollback_handler.handle_failed_ci(ci_result)
                
                if rollback_result.success:
                    logger.info("Auto-rollback successful")
                else:
                    logger.error("Auto-rollback failed")
                
                return rollback_result
            else:
                logger.info("Auto-rollback disabled, manual intervention required")
                return None
        
        else:
            logger.info("CI passed, no rollback needed")
            return None
