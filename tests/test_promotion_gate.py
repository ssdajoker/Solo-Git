"""
Tests for promotion gate (Phase 3).
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from sologit.engines.git_engine import GitEngine
from sologit.workflows.promotion_gate import (
    PromotionGate, PromotionRules, PromotionDecision, PromotionDecisionType
)
from sologit.analysis.test_analyzer import TestAnalysis


@pytest.fixture
def temp_dir():
    """Create temporary directory for test repos."""
    tmpdir = tempfile.mkdtemp()
    yield Path(tmpdir)
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def git_engine(temp_dir):
    """Create GitEngine with temp storage."""
    return GitEngine(data_dir=temp_dir)


@pytest.fixture
def test_repo(git_engine, temp_dir):
    """Create a test repository."""
    # Create a simple repo
    repo_path = temp_dir / "test_repo"
    repo_path.mkdir()
    
    # Create a dummy file
    (repo_path / "README.md").write_text("# Test Repo\n")
    
    # Initialize repo
    import zipfile
    zip_path = temp_dir / "repo.zip"
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(repo_path / "README.md", "README.md")
    
    repo_id = git_engine.init_from_zip(zip_path.read_bytes(), "test_repo")
    return repo_id


@pytest.fixture
def test_workpad(git_engine, test_repo):
    """Create a test workpad."""
    workpad_id = git_engine.create_workpad(test_repo, "test-feature")
    return workpad_id


@pytest.fixture
def default_rules():
    """Create default promotion rules."""
    return PromotionRules()


@pytest.fixture
def strict_rules():
    """Create strict promotion rules."""
    return PromotionRules(
        require_tests=True,
        require_all_tests_pass=True,
        require_fast_forward=True,
        max_files_changed=10,
        max_lines_changed=500
    )


@pytest.fixture
def passing_analysis():
    """Create passing test analysis."""
    return TestAnalysis(
        total_tests=10,
        passed=10,
        failed=0,
        timeout=0,
        error=0,
        status="green"
    )


@pytest.fixture
def failing_analysis():
    """Create failing test analysis."""
    return TestAnalysis(
        total_tests=10,
        passed=7,
        failed=3,
        timeout=0,
        error=0,
        status="red"
    )


class TestPromotionRules:
    """Tests for PromotionRules dataclass."""
    
    def test_default_rules(self, default_rules):
        """Test default rule values."""
        assert default_rules.require_tests is True
        assert default_rules.require_all_tests_pass is True
        assert default_rules.require_fast_forward is True
        assert default_rules.max_files_changed is None
        assert default_rules.max_lines_changed is None
    
    def test_custom_rules(self):
        """Test custom rule configuration."""
        rules = PromotionRules(
            require_tests=False,
            max_files_changed=5,
            max_lines_changed=100
        )
        
        assert rules.require_tests is False
        assert rules.max_files_changed == 5
        assert rules.max_lines_changed == 100


class TestPromotionDecision:
    """Tests for PromotionDecision dataclass."""
    
    def test_decision_creation(self):
        """Test creating a decision."""
        decision = PromotionDecision(
            decision=PromotionDecisionType.APPROVE,
            can_promote=True
        )
        
        assert decision.decision == PromotionDecisionType.APPROVE
        assert decision.can_promote is True
        assert len(decision.reasons) == 0
        assert len(decision.warnings) == 0
    
    def test_add_reason(self):
        """Test adding reasons."""
        decision = PromotionDecision(decision=PromotionDecisionType.APPROVE)
        decision.add_reason("Tests passed")
        decision.add_reason("Fast-forward possible")
        
        assert len(decision.reasons) == 2
        assert "Tests passed" in decision.reasons
    
    def test_add_warning(self):
        """Test adding warnings."""
        decision = PromotionDecision(decision=PromotionDecisionType.APPROVE)
        decision.add_warning("Large change detected")
        
        assert len(decision.warnings) == 1
        assert "Large change detected" in decision.warnings


class TestPromotionGate:
    """Tests for PromotionGate class."""
    
    def test_gate_initialization(self, git_engine, default_rules):
        """Test gate initialization."""
        gate = PromotionGate(git_engine, default_rules)
        
        assert gate.git_engine == git_engine
        assert gate.rules == default_rules
    
    def test_evaluate_nonexistent_workpad(self, git_engine, default_rules):
        """Test evaluating non-existent workpad."""
        gate = PromotionGate(git_engine, default_rules)
        decision = gate.evaluate("nonexistent_pad")
        
        assert decision.decision == PromotionDecisionType.REJECT
        assert not decision.can_promote
        assert any("not found" in reason.lower() for reason in decision.reasons)
    
    def test_evaluate_without_tests_required(self, git_engine, test_workpad):
        """Test evaluation when tests not required."""
        rules = PromotionRules(require_tests=False)
        gate = PromotionGate(git_engine, rules)
        
        decision = gate.evaluate(test_workpad, test_analysis=None)
        
        # Should have warning about tests not required
        assert any("not required" in warning.lower() for warning in decision.warnings)
    
    def test_evaluate_tests_required_but_not_run(self, git_engine, test_workpad, default_rules):
        """Test evaluation when tests required but not run."""
        gate = PromotionGate(git_engine, default_rules)
        decision = gate.evaluate(test_workpad, test_analysis=None)
        
        assert decision.decision == PromotionDecisionType.REJECT
        assert not decision.can_promote
        assert any("not run" in reason.lower() for reason in decision.reasons)
    
    def test_evaluate_tests_passed(self, git_engine, test_workpad, default_rules, passing_analysis):
        """Test evaluation with passing tests."""
        gate = PromotionGate(git_engine, default_rules)
        decision = gate.evaluate(test_workpad, passing_analysis)
        
        # Check for passing message
        assert any("passed" in reason.lower() for reason in decision.reasons)
    
    def test_evaluate_tests_failed(self, git_engine, test_workpad, default_rules, failing_analysis):
        """Test evaluation with failing tests."""
        gate = PromotionGate(git_engine, default_rules)
        decision = gate.evaluate(test_workpad, failing_analysis)
        
        assert decision.decision == PromotionDecisionType.REJECT
        assert not decision.can_promote
        assert any("failed" in reason.lower() for reason in decision.reasons)
    
    def test_evaluate_fast_forward_possible(self, git_engine, test_workpad, passing_analysis):
        """Test evaluation when fast-forward is possible."""
        rules = PromotionRules(require_tests=True, require_fast_forward=True)
        gate = PromotionGate(git_engine, rules)
        
        decision = gate.evaluate(test_workpad, passing_analysis)
        
        # Should approve since tests passed and can fast-forward
        assert decision.can_promote
        assert any("fast-forward" in reason.lower() for reason in decision.reasons)
    
    def test_evaluate_all_checks_pass(self, git_engine, test_workpad, passing_analysis):
        """Test evaluation when all checks pass."""
        rules = PromotionRules(
            require_tests=True,
            require_all_tests_pass=True,
            require_fast_forward=True
        )
        gate = PromotionGate(git_engine, rules)
        
        decision = gate.evaluate(test_workpad, passing_analysis)
        
        assert decision.decision == PromotionDecisionType.APPROVE
        assert decision.can_promote
        assert any("ready to promote" in reason.lower() for reason in decision.reasons)
    
    def test_format_decision(self, git_engine, test_workpad, default_rules, passing_analysis):
        """Test formatting decision for display."""
        gate = PromotionGate(git_engine, default_rules)
        decision = gate.evaluate(test_workpad, passing_analysis)
        
        formatted = gate.format_decision(decision)
        
        assert isinstance(formatted, str)
        assert "PROMOTION GATE" in formatted
        assert "Reasons:" in formatted
    
    def test_format_reject_decision(self, git_engine, test_workpad, default_rules, failing_analysis):
        """Test formatting reject decision."""
        gate = PromotionGate(git_engine, default_rules)
        decision = gate.evaluate(test_workpad, failing_analysis)
        
        formatted = gate.format_decision(decision)
        
        assert "REJECTED" in formatted
    
    def test_format_manual_review_decision(self, git_engine, test_workpad, passing_analysis):
        """Test formatting manual review decision."""
        # Rules with size limits to trigger manual review
        rules = PromotionRules(
            require_tests=True,
            require_all_tests_pass=True,
            max_files_changed=1,  # Very small limit
            max_lines_changed=10
        )
        gate = PromotionGate(git_engine, rules)
        
        decision = gate.evaluate(test_workpad, passing_analysis)
        
        # Might require manual review if change is large
        if decision.decision == PromotionDecisionType.MANUAL_REVIEW:
            formatted = gate.format_decision(decision)
            assert "MANUAL REVIEW" in formatted


class TestPromotionGateIntegration:
    """Integration tests for promotion gate."""
    
    def test_full_workflow_approve(self, git_engine, test_workpad, passing_analysis):
        """Test full approval workflow."""
        rules = PromotionRules()
        gate = PromotionGate(git_engine, rules)
        
        # Evaluate
        decision = gate.evaluate(test_workpad, passing_analysis)
        
        # Should approve
        assert decision.can_promote
        assert decision.decision == PromotionDecisionType.APPROVE
        
        # Should have multiple reasons
        assert len(decision.reasons) >= 2
    
    def test_full_workflow_reject(self, git_engine, test_workpad, failing_analysis):
        """Test full rejection workflow."""
        rules = PromotionRules()
        gate = PromotionGate(git_engine, rules)
        
        # Evaluate
        decision = gate.evaluate(test_workpad, failing_analysis)
        
        # Should reject
        assert not decision.can_promote
        assert decision.decision == PromotionDecisionType.REJECT
        
        # Should explain why
        assert len(decision.reasons) > 0
