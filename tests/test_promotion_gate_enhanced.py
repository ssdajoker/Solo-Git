
"""
Enhanced tests for promotion gate to achieve >90% coverage.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from sologit.workflows.promotion_gate import (
    PromotionGate, 
    PromotionRules, 
    PromotionDecision, 
    PromotionDecisionType
)
from sologit.engines.git_engine import GitEngine, GitEngineError
from sologit.analysis.test_analyzer import TestAnalysis
from sologit.core.workpad import Workpad


class TestPromotionGateEnhanced:
    """Enhanced tests for PromotionGate."""
    
    @pytest.fixture
    def git_engine(self):
        """Mock git engine."""
        return Mock(spec=GitEngine)
    
    @pytest.fixture
    def gate(self, git_engine):
        """Create gate instance with default rules."""
        return PromotionGate(git_engine)
    
    @pytest.fixture
    def custom_gate(self, git_engine):
        """Create gate instance with custom rules."""
        rules = PromotionRules(
            require_tests=False,
            require_fast_forward=False,
            min_coverage=0
        )
        return PromotionGate(git_engine, rules)
    
    def test_evaluate_workpad_not_found(self, gate, git_engine):
        """Test evaluation when workpad doesn't exist."""
        # Mock git engine to return None
        git_engine.get_workpad = Mock(return_value=None)
        
        # Mock analysis
        analysis = Mock(spec=TestAnalysis)
        analysis.status = "green"
        
        # Evaluate
        decision = gate.evaluate("nonexistent-pad", analysis)
        
        # Verify
        assert not decision.can_promote
        assert decision.decision == PromotionDecisionType.REJECT
        assert any("not found" in reason.lower() for reason in decision.reasons)
    
    def test_evaluate_cannot_promote_exception(self, gate, git_engine):
        """Test evaluation when can_promote check raises exception."""
        # Mock git engine
        mock_workpad = Mock(spec=Workpad)
        mock_workpad.id = "test-pad"
        git_engine.get_workpad = Mock(return_value=mock_workpad)
        git_engine.can_promote = Mock(side_effect=GitEngineError("Cannot check promotion"))
        
        # Create proper TestAnalysis instance
        analysis = TestAnalysis(
            total_tests=10,
            passed=10,
            failed=0,
            timeout=0,
            error=0,
            status="green"
        )
        
        # Evaluate
        decision = gate.evaluate("test-pad", analysis)
        
        # Verify
        assert not decision.can_promote
        assert decision.decision == PromotionDecisionType.REJECT
    
    def test_evaluate_tests_required_but_status_red(self, gate, git_engine):
        """Test evaluation when tests are required but failed."""
        # Mock git engine
        mock_workpad = Mock(spec=Workpad)
        mock_workpad.id = "test-pad"
        git_engine.get_workpad = Mock(return_value=mock_workpad)
        git_engine.can_promote = Mock(return_value=True)
        
        # Create proper TestAnalysis instance with red status
        analysis = TestAnalysis(
            total_tests=8,
            passed=5,
            failed=3,
            timeout=0,
            error=0,
            status="red"
        )
        
        # Evaluate
        decision = gate.evaluate("test-pad", analysis)
        
        # Verify
        assert not decision.can_promote
        assert decision.decision == PromotionDecisionType.REJECT
        assert any("failed" in reason.lower() for reason in decision.reasons)
    
    def test_evaluate_tests_required_but_status_yellow(self, gate, git_engine):
        """Test evaluation when tests have warnings (yellow status)."""
        # Mock git engine
        mock_workpad = Mock(spec=Workpad)
        mock_workpad.id = "test-pad"
        git_engine.get_workpad = Mock(return_value=mock_workpad)
        git_engine.can_promote = Mock(return_value=True)
        
        # Create proper TestAnalysis instance with yellow status
        analysis = TestAnalysis(
            total_tests=8,
            passed=8,
            failed=0,
            timeout=0,
            error=0,
            status="yellow"
        )
        
        # Evaluate
        decision = gate.evaluate("test-pad", analysis)
        
        # Verify - Implementation treats non-green as REJECT
        assert not decision.can_promote
        assert decision.decision == PromotionDecisionType.REJECT
        assert any("failed" in reason.lower() or "error" in reason.lower() for reason in decision.reasons)
    
    def test_evaluate_tests_not_required(self, custom_gate, git_engine):
        """Test evaluation when tests are not required."""
        # Mock git engine
        mock_workpad = Mock(spec=Workpad)
        mock_workpad.id = "test-pad"
        git_engine.get_workpad = Mock(return_value=mock_workpad)
        git_engine.can_promote = Mock(return_value=True)
        
        # Mock analysis (doesn't matter since tests not required)
        analysis = None
        
        # Evaluate
        decision = custom_gate.evaluate("test-pad", analysis)
        
        # Verify
        assert decision.can_promote
        assert decision.decision == PromotionDecisionType.APPROVE
    
    def test_evaluate_fast_forward_not_possible(self, gate, git_engine):
        """Test evaluation when fast-forward merge is not possible."""
        # Mock git engine
        mock_workpad = Mock(spec=Workpad)
        mock_workpad.id = "test-pad"
        git_engine.get_workpad = Mock(return_value=mock_workpad)
        git_engine.can_promote = Mock(return_value=False)  # Cannot fast-forward
        
        # Create proper TestAnalysis instance
        analysis = TestAnalysis(
            total_tests=10,
            passed=10,
            failed=0,
            timeout=0,
            error=0,
            status="green"
        )
        
        # Evaluate
        decision = gate.evaluate("test-pad", analysis)
        
        # Verify
        assert not decision.can_promote
        assert any("fast-forward" in reason.lower() or "rebase" in reason.lower() for reason in decision.reasons)
    
    def test_format_decision_reject(self, gate):
        """Test formatting REJECT decision."""
        decision = PromotionDecision(
            can_promote=False,
            decision=PromotionDecisionType.REJECT,
            reasons=["❌ Tests failed", "❌ Cannot fast-forward"],
            warnings=[]
        )
        
        formatted = gate.format_decision(decision)
        
        # Verify
        assert "PROMOTION GATE DECISION" in formatted
        assert "❌ REJECT" in formatted
        assert "Tests failed" in formatted
        assert "Cannot fast-forward" in formatted
    
    def test_format_decision_manual_review(self, gate):
        """Test formatting MANUAL_REVIEW decision."""
        decision = PromotionDecision(
            can_promote=False,
            decision=PromotionDecisionType.MANUAL_REVIEW,
            reasons=["⚠️ Some concerns"],
            warnings=["Warning 1", "Warning 2"]
        )
        
        formatted = gate.format_decision(decision)
        
        # Verify
        assert "PROMOTION GATE DECISION" in formatted
        assert "👀 MANUAL REVIEW REQUIRED" in formatted  # Uses 👀 emoji
        assert "Warning 1" in formatted
        assert "Warning 2" in formatted
    
    def test_format_decision_with_empty_lists(self, gate):
        """Test formatting decision with empty reasons and warnings."""
        decision = PromotionDecision(
            can_promote=True,
            decision=PromotionDecisionType.APPROVE,
            reasons=[],
            warnings=[]
        )
        
        formatted = gate.format_decision(decision)
        
        # Verify basic formatting works
        assert "PROMOTION GATE DECISION" in formatted
        assert "✅ APPROVE" in formatted


class TestPromotionRulesDefaults:
    """Tests for PromotionRules default values."""
    
    def test_default_rules(self):
        """Test default promotion rules."""
        rules = PromotionRules()
        
        assert rules.require_tests
        assert rules.require_fast_forward
        assert rules.min_coverage == 0


class TestPromotionDecisionMethods:
    """Tests for PromotionDecision methods."""
    
    def test_add_reason(self):
        """Test adding reasons to decision."""
        decision = PromotionDecision(
            can_promote=True,
            decision=PromotionDecisionType.APPROVE,
            reasons=[],
            warnings=[]
        )
        
        decision.add_reason("✅ All tests passed")
        
        assert len(decision.reasons) == 1
        assert "All tests passed" in decision.reasons[0]
    
    def test_add_warning(self):
        """Test adding warnings to decision."""
        decision = PromotionDecision(
            can_promote=True,
            decision=PromotionDecisionType.APPROVE,
            reasons=[],
            warnings=[]
        )
        
        decision.add_warning("⚠️ Low test coverage")
        
        assert len(decision.warnings) == 1
        assert "Low test coverage" in decision.warnings[0]
