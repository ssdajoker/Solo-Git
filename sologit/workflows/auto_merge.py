"""
Auto-merge workflow for Solo Git.

Coordinates testing, analysis, and promotion in a single workflow.
"""

from dataclasses import dataclass
from typing import List, Optional

from sologit.engines.git_engine import GitEngine
from sologit.engines.test_orchestrator import TestOrchestrator, TestConfig
from sologit.analysis.test_analyzer import TestAnalyzer, TestAnalysis
from sologit.workflows.promotion_gate import PromotionGate, PromotionRules, PromotionDecision
from sologit.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AutoMergeResult:
    """Result of auto-merge workflow."""
    success: bool
    pad_id: str
    commit_hash: Optional[str] = None
    test_analysis: Optional[TestAnalysis] = None
    promotion_decision: Optional[PromotionDecision] = None
    message: str = ""
    details: List[str] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = []


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
        promotion_rules: Optional[PromotionRules] = None
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
        
        logger.info("AutoMergeWorkflow initialized")
    
    def execute(
        self,
        pad_id: str,
        tests: List[TestConfig],
        parallel: bool = True,
        auto_promote: bool = True
    ) -> AutoMergeResult:
        """
        Execute auto-merge workflow.
        
        Args:
            pad_id: Workpad ID
            tests: Test configurations to run
            parallel: Run tests in parallel
            auto_promote: Automatically promote if approved
            
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
        
        result.details.append(f"📝 Workpad: {workpad.title}")
        
        # Step 1: Run tests
        logger.info(f"Step 1: Running {len(tests)} tests")
        result.details.append(f"\n🧪 Running {len(tests)} tests...")
        
        try:
            test_results = self.test_orchestrator.run_tests_sync(pad_id, tests, parallel)
            result.details.append(f"   Tests completed in {sum(r.duration_ms for r in test_results)/1000:.1f}s")
        except Exception as e:
            result.message = f"Test execution failed: {e}"
            result.details.append(f"❌ {result.message}")
            logger.error(result.message, exc_info=True)
            return result
        
        # Step 2: Analyze results
        logger.info("Step 2: Analyzing test results")
        result.details.append("\n📊 Analyzing test results...")
        
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
            return result
        
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
        
        return result
    
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
