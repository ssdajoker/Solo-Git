"""
Promotion gate with configurable rules.

Determines whether a workpad is ready to be promoted to trunk.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum

from sologit.engines.git_engine import GitEngine
from sologit.analysis.test_analyzer import TestAnalysis
from sologit.utils.logger import get_logger

logger = get_logger(__name__)


class PromotionDecisionType(Enum):
    """Types of promotion decisions."""
    APPROVE = "approve"
    REJECT = "reject"
    MANUAL_REVIEW = "manual_review"


@dataclass
class PromotionRules:
    """Configurable rules for promotion gate."""
    
    # Test requirements
    require_tests: bool = True
    require_all_tests_pass: bool = True
    allow_skipped_tests: bool = False
    
    # Coverage requirements (optional)
    min_coverage: float = 0  # Minimum coverage percentage (0-100)
    min_coverage_percent: Optional[float] = None  # Alias for backwards compatibility
    
    # Fast-forward requirement
    require_fast_forward: bool = True
    
    # Change size limits
    max_files_changed: Optional[int] = None
    max_lines_changed: Optional[int] = None
    
    # Merge restrictions
    allow_merge_conflicts: bool = False
    
    # AI review (future enhancement)
    require_ai_review: bool = False
    min_ai_confidence: float = 0.8


@dataclass
class PromotionDecision:
    """Result of promotion gate evaluation."""
    decision: PromotionDecisionType
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    can_promote: bool = False
    
    def add_reason(self, reason: str) -> None:
        """Add a reason for the decision."""
        self.reasons.append(reason)

    def add_warning(self, warning: str) -> None:
        """Add a warning."""
        self.warnings.append(warning)


class PromotionGate:
    """
    Evaluates whether a workpad is ready for promotion.
    
    Applies configurable rules to determine if changes can be merged to trunk.
    """
    
    def __init__(
        self,
        git_engine: GitEngine,
        rules: Optional[PromotionRules] = None
    ) -> None:
        """
        Initialize promotion gate.
        
        Args:
            git_engine: GitEngine instance
            rules: Promotion rules (uses defaults if None)
        """
        self.git_engine = git_engine
        self.rules = rules or PromotionRules()
        logger.info(f"PromotionGate initialized with rules: {self.rules}")
    
    def evaluate(
        self,
        pad_id: str,
        test_analysis: Optional[TestAnalysis] = None
    ) -> PromotionDecision:
        """
        Evaluate if workpad can be promoted.
        
        Args:
            pad_id: Workpad ID to evaluate
            test_analysis: Test analysis result (if tests were run)
            
        Returns:
            Promotion decision with reasons
        """
        logger.info(f"Evaluating promotion gate for pad {pad_id}")
        
        decision = PromotionDecision(decision=PromotionDecisionType.APPROVE)
        
        # Get workpad
        workpad = self.git_engine.get_workpad(pad_id)
        if not workpad:
            decision.decision = PromotionDecisionType.REJECT
            decision.add_reason("❌ Workpad not found")
            return decision
        
        # Check 1: Test requirements
        if self.rules.require_tests:
            if test_analysis is None:
                decision.decision = PromotionDecisionType.REJECT
                decision.add_reason("❌ Tests required but not run")
                return decision
            
            if self.rules.require_all_tests_pass:
                if test_analysis.status != "green":
                    decision.decision = PromotionDecisionType.REJECT
                    decision.add_reason(
                        f"❌ Tests failed: {test_analysis.failed} failed, "
                        f"{test_analysis.timeout} timeout, {test_analysis.error} error"
                    )
                    return decision
                else:
                    decision.add_reason(f"✅ All tests passed ({test_analysis.passed}/{test_analysis.total_tests})")
            
            # Check coverage if specified
            if self.rules.min_coverage_percent is not None:
                # Note: Coverage tracking is a future enhancement
                decision.add_warning("⚠️ Coverage tracking not yet implemented")
        else:
            decision.add_warning("⚠️ Tests not required for promotion")
        
        # Check 2: Fast-forward requirement
        if self.rules.require_fast_forward:
            if not self.git_engine.can_promote(pad_id):
                if self.rules.allow_merge_conflicts:
                    decision.add_warning("⚠️ Not fast-forwardable but merge conflicts allowed")
                else:
                    decision.decision = PromotionDecisionType.REJECT
                    decision.add_reason("❌ Cannot fast-forward - trunk has diverged")
                    decision.add_reason("   Manual merge or rebase required")
                    return decision
            else:
                decision.add_reason("✅ Can fast-forward to trunk")
        
        # Check 3: Change size limits
        try:
            diff = self.git_engine.get_diff(pad_id)
            
            # Count files and lines changed
            files_changed = len(set(
                line.split()[0] 
                for line in diff.split('\n') 
                if line.startswith('diff --git')
            ))
            
            lines_changed = sum(
                1 for line in diff.split('\n')
                if line.startswith('+') or line.startswith('-')
            ) - (files_changed * 2)  # Subtract diff headers
            
            # Check file limit
            if self.rules.max_files_changed is not None:
                if files_changed > self.rules.max_files_changed:
                    decision.decision = PromotionDecisionType.MANUAL_REVIEW
                    decision.add_reason(
                        f"⚠️ Large change: {files_changed} files (limit: {self.rules.max_files_changed})"
                    )
                    decision.add_reason("   Manual review recommended")
            
            # Check lines limit
            if self.rules.max_lines_changed is not None:
                if lines_changed > self.rules.max_lines_changed:
                    decision.decision = PromotionDecisionType.MANUAL_REVIEW
                    decision.add_reason(
                        f"⚠️ Large change: {lines_changed} lines (limit: {self.rules.max_lines_changed})"
                    )
                    decision.add_reason("   Manual review recommended")
            
            # Log change size
            decision.add_reason(f"📊 Change size: {files_changed} files, ~{lines_changed} lines")
            
        except Exception as e:
            logger.error(f"Error analyzing diff: {e}")
            decision.add_warning(f"⚠️ Could not analyze change size: {e}")
        
        # Check 4: AI review (future enhancement)
        if self.rules.require_ai_review:
            decision.add_warning("⚠️ AI review not yet implemented")
        
        # Final decision
        if decision.decision == PromotionDecisionType.APPROVE:
            decision.can_promote = True
            decision.add_reason("🎉 All checks passed - ready to promote!")
        elif decision.decision == PromotionDecisionType.MANUAL_REVIEW:
            decision.add_reason("👀 Manual review recommended before promotion")
        
        logger.info(f"Promotion gate decision: {decision.decision.value}")
        
        return decision
    
    def format_decision(self, decision: PromotionDecision) -> str:
        """Format decision for display."""
        lines = []
        
        lines.append("=" * 60)
        lines.append("PROMOTION GATE DECISION")
        lines.append("=" * 60)
        lines.append("")
        
        # Decision header
        if decision.decision == PromotionDecisionType.APPROVE:
            lines.append("✅ APPROVED - Ready to promote")
        elif decision.decision == PromotionDecisionType.REJECT:
            lines.append("❌ REJECTED - Cannot promote")
        else:
            lines.append("👀 MANUAL REVIEW REQUIRED")
        
        lines.append("")
        
        # Reasons
        if decision.reasons:
            lines.append("Reasons:")
            for reason in decision.reasons:
                lines.append(f"  {reason}")
            lines.append("")
        
        # Warnings
        if decision.warnings:
            lines.append("Warnings:")
            for warning in decision.warnings:
                lines.append(f"  {warning}")
            lines.append("")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)
