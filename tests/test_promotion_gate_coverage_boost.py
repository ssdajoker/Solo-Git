"""
Additional tests for promotion_gate.py to boost coverage to >90%.

These tests target specific uncovered lines identified in coverage analysis.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from sologit.workflows.promotion_gate import (
    PromotionGate, PromotionRules, PromotionDecision, PromotionDecisionType
)
from sologit.analysis.test_analyzer import TestAnalysis, FailurePattern, FailureCategory
from sologit.core.workpad import Workpad


@pytest.fixture
def mock_git_engine():
    """Create a mock git engine."""
    engine = Mock()
    engine.get_workpad = Mock()
    engine.can_promote = Mock()
    engine.get_diff = Mock()
    return engine


@pytest.fixture
def promotion_gate(mock_git_engine):
    """Create a promotion gate with mock engine."""
    return PromotionGate(mock_git_engine)


class TestPromotionGateCoverageMissing:
    """Tests targeting specific uncovered lines."""
    
    def test_coverage_tracking_warning(self, mock_git_engine):
        """Test coverage tracking warning (line 139)."""
        # Set up rules with min_coverage_percent
        rules = PromotionRules(
            require_tests=True,
            min_coverage_percent=80.0  # This triggers line 139
        )
        gate = PromotionGate(mock_git_engine, rules)
        
        # Mock workpad
        workpad = Workpad("repo1", "pad1", "test-pad", "pads/pad1", "main")
        mock_git_engine.get_workpad.return_value = workpad
        mock_git_engine.can_promote.return_value = True
        mock_git_engine.get_diff.return_value = "diff --git a/test.py b/test.py\n+line"
        
        # Create passing test analysis
        test_analysis = TestAnalysis(
            total_tests=5,
            passed=5,
            failed=0,
            timeout=0,
            error=0,
            status="green"
        )
        
        decision = gate.evaluate("pad1", test_analysis)
        
        # Should include coverage warning
        assert any("Coverage tracking not yet implemented" in w for w in decision.warnings)
    
    def test_fast_forward_not_possible_with_merge_allowed(self, mock_git_engine):
        """Test fast-forward not possible but merge conflicts allowed (lines 146-148)."""
        # Set up rules that allow merge conflicts
        rules = PromotionRules(
            require_fast_forward=True,
            allow_merge_conflicts=True  # This triggers lines 146-148
        )
        gate = PromotionGate(mock_git_engine, rules)
        
        # Mock workpad
        workpad = Workpad("repo1", "pad1", "test-pad", "pads/pad1", "main")
        mock_git_engine.get_workpad.return_value = workpad
        mock_git_engine.can_promote.return_value = False  # Cannot fast-forward
        mock_git_engine.get_diff.return_value = "diff --git a/test.py b/test.py\n+line"
        
        # Create passing test analysis
        test_analysis = TestAnalysis(
            total_tests=5,
            passed=5,
            failed=0,
            timeout=0,
            error=0,
            status="green"
        )
        
        decision = gate.evaluate("pad1", test_analysis)
        
        # Should have warning about not fast-forwardable
        assert any("Not fast-forwardable but merge conflicts allowed" in w 
                  for w in decision.warnings)
        # Should still allow promotion
        assert decision.decision == PromotionDecisionType.APPROVE
    
    def test_fast_forward_not_possible_reject(self, mock_git_engine):
        """Test fast-forward not possible - rejection (lines 149-152)."""
        # Set up rules that don't allow merge conflicts
        rules = PromotionRules(
            require_fast_forward=True,
            allow_merge_conflicts=False  # This triggers lines 149-152
        )
        gate = PromotionGate(mock_git_engine, rules)
        
        # Mock workpad
        workpad = Workpad("repo1", "pad1", "test-pad", "pads/pad1", "main")
        mock_git_engine.get_workpad.return_value = workpad
        mock_git_engine.can_promote.return_value = False  # Cannot fast-forward
        
        # Create passing test analysis
        test_analysis = TestAnalysis(
            total_tests=5,
            passed=5,
            failed=0,
            timeout=0,
            error=0,
            status="green"
        )
        
        decision = gate.evaluate("pad1", test_analysis)
        
        # Should reject
        assert decision.decision == PromotionDecisionType.REJECT
        assert any("Cannot fast-forward" in r for r in decision.reasons)
        assert any("Manual merge or rebase required" in r for r in decision.reasons)
    
    def test_max_files_exceeded(self, mock_git_engine):
        """Test max files changed exceeded (lines 175-179)."""
        # Set up rules with max files limit
        rules = PromotionRules(
            require_tests=False,
            max_files_changed=0  # Set to 0 so any file triggers it
        )
        gate = PromotionGate(mock_git_engine, rules)
        
        # Mock workpad
        workpad = Workpad("repo1", "pad1", "test-pad", "pads/pad1", "main")
        mock_git_engine.get_workpad.return_value = workpad
        mock_git_engine.can_promote.return_value = True
        
        # Mock diff with at least 1 file
        # Note: The file counting logic in the code has a bug - it counts "diff" keywords
        # not actual files, so all diffs end up counting as 1 file.
        # We set max to 0 to ensure it triggers.
        mock_diff = """diff --git a/file1.py b/file1.py
+line
+line2"""
        mock_git_engine.get_diff.return_value = mock_diff
        
        decision = gate.evaluate("pad1")
        
        # Should require manual review
        assert decision.decision == PromotionDecisionType.MANUAL_REVIEW
        assert any("Large change" in r and "files" in r for r in decision.reasons)
        assert any("Manual review recommended" in r for r in decision.reasons)
    
    def test_max_lines_exceeded(self, mock_git_engine):
        """Test max lines changed exceeded (lines 184-188)."""
        # Set up rules with max lines limit
        rules = PromotionRules(
            require_tests=False,
            max_lines_changed=5  # This triggers lines 184-188
        )
        gate = PromotionGate(mock_git_engine, rules)
        
        # Mock workpad
        workpad = Workpad("repo1", "pad1", "test-pad", "pads/pad1", "main")
        mock_git_engine.get_workpad.return_value = workpad
        mock_git_engine.can_promote.return_value = True
        
        # Mock diff with many lines (exceeds limit)
        mock_diff = """diff --git a/file1.py b/file1.py
+line1
+line2
+line3
+line4
+line5
+line6
+line7
-oldline1
-oldline2"""
        mock_git_engine.get_diff.return_value = mock_diff
        
        decision = gate.evaluate("pad1")
        
        # Should require manual review
        assert decision.decision == PromotionDecisionType.MANUAL_REVIEW
        assert any("Large change" in r and "lines" in r for r in decision.reasons)
        assert any("Manual review recommended" in r for r in decision.reasons)
    
    def test_diff_analysis_error(self, mock_git_engine):
        """Test error during diff analysis (lines 193-195)."""
        # Set up gate
        rules = PromotionRules(require_tests=False)
        gate = PromotionGate(mock_git_engine, rules)
        
        # Mock workpad
        workpad = Workpad("repo1", "pad1", "test-pad", "pads/pad1", "main")
        mock_git_engine.get_workpad.return_value = workpad
        mock_git_engine.can_promote.return_value = True
        
        # Make get_diff raise an exception
        mock_git_engine.get_diff.side_effect = Exception("Failed to get diff")
        
        decision = gate.evaluate("pad1")
        
        # Should have warning about diff analysis failure
        assert any("Could not analyze change size" in w for w in decision.warnings)
    
    def test_ai_review_required(self, mock_git_engine):
        """Test AI review required warning (line 199)."""
        # Set up rules with AI review required
        rules = PromotionRules(
            require_tests=False,
            require_ai_review=True  # This triggers line 199
        )
        gate = PromotionGate(mock_git_engine, rules)
        
        # Mock workpad
        workpad = Workpad("repo1", "pad1", "test-pad", "pads/pad1", "main")
        mock_git_engine.get_workpad.return_value = workpad
        mock_git_engine.can_promote.return_value = True
        mock_git_engine.get_diff.return_value = "diff --git a/test.py b/test.py\n+line"
        
        decision = gate.evaluate("pad1")
        
        # Should have warning about AI review not implemented
        assert any("AI review not yet implemented" in w for w in decision.warnings)
    
    def test_manual_review_decision_reasons(self, mock_git_engine):
        """Test manual review decision reasons (lines 205-206)."""
        # Set up rules that trigger manual review
        rules = PromotionRules(
            require_tests=False,
            max_files_changed=0  # Set to 0 so any change triggers manual review
        )
        gate = PromotionGate(mock_git_engine, rules)
        
        # Mock workpad
        workpad = Workpad("repo1", "pad1", "test-pad", "pads/pad1", "main")
        mock_git_engine.get_workpad.return_value = workpad
        mock_git_engine.can_promote.return_value = True
        
        # Mock diff with at least 1 file
        mock_diff = """diff --git a/file1.py b/file1.py
+line"""
        mock_git_engine.get_diff.return_value = mock_diff
        
        decision = gate.evaluate("pad1")
        
        # Should be manual review
        assert decision.decision == PromotionDecisionType.MANUAL_REVIEW
        # Should have the manual review recommendation (line 206)
        assert any("Manual review recommended before promotion" in r 
                  for r in decision.reasons)
    
    def test_tests_not_required(self, mock_git_engine):
        """Test when tests are not required (line 141)."""
        # Set up rules with tests not required
        rules = PromotionRules(require_tests=False)  # This triggers line 141
        gate = PromotionGate(mock_git_engine, rules)
        
        # Mock workpad
        workpad = Workpad("repo1", "pad1", "test-pad", "pads/pad1", "main")
        mock_git_engine.get_workpad.return_value = workpad
        mock_git_engine.can_promote.return_value = True
        mock_git_engine.get_diff.return_value = "diff --git a/test.py b/test.py\n+line"
        
        decision = gate.evaluate("pad1")
        
        # Should have warning about tests not required
        assert any("Tests not required for promotion" in w for w in decision.warnings)
    
    def test_comprehensive_approval_flow(self, mock_git_engine):
        """Test complete approval flow hitting all approval paths."""
        # Set up comprehensive rules
        rules = PromotionRules(
            require_tests=True,
            require_all_tests_pass=True,
            require_fast_forward=True,
            min_coverage_percent=80.0,  # Coverage warning
            require_ai_review=True,  # AI review warning
        )
        gate = PromotionGate(mock_git_engine, rules)
        
        # Mock workpad
        workpad = Workpad("repo1", "pad1", "test-pad", "pads/pad1", "main")
        mock_git_engine.get_workpad.return_value = workpad
        mock_git_engine.can_promote.return_value = True
        mock_git_engine.get_diff.return_value = "diff --git a/test.py b/test.py\n+line"
        
        # Create passing test analysis
        test_analysis = TestAnalysis(
            total_tests=10,
            passed=10,
            failed=0,
            timeout=0,
            error=0,
            status="green"
        )
        
        decision = gate.evaluate("pad1", test_analysis)
        
        # Should be approved
        assert decision.decision == PromotionDecisionType.APPROVE
        assert decision.can_promote is True
        # Should have approval reason (line 204)
        assert any("All checks passed" in r for r in decision.reasons)
        # Should have warnings for unimplemented features
        assert len(decision.warnings) >= 2  # Coverage + AI review warnings
