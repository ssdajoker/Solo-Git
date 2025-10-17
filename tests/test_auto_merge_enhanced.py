"""
Enhanced tests for auto-merge workflow to achieve >90% coverage.

This test suite covers:
- Error handling paths
- Edge cases in workflow execution
- All branches and decision paths
"""

import pytest
from unittest.mock import Mock, MagicMock, patch

from sologit.workflows.auto_merge import AutoMergeWorkflow, AutoMergeResult
from sologit.workflows.promotion_gate import PromotionGate, PromotionRules, PromotionDecision, PromotionDecisionType
from sologit.engines.git_engine import GitEngine, GitEngineError
from sologit.engines.test_orchestrator import TestOrchestrator, TestConfig, TestResult, TestStatus
from sologit.analysis.test_analyzer import TestAnalyzer, TestAnalysis, FailurePattern, FailureCategory
from sologit.core.workpad import Workpad


class TestAutoMergeWorkflowEnhanced:
    """Enhanced tests for AutoMergeWorkflow."""
    
    @pytest.fixture
    def git_engine(self):
        """Mock git engine."""
        return Mock(spec=GitEngine)
    
    @pytest.fixture
    def test_orchestrator(self):
        """Mock test orchestrator."""
        return Mock(spec=TestOrchestrator)
    
    @pytest.fixture
    def workflow(self, git_engine, test_orchestrator):
        """Create workflow instance."""
        return AutoMergeWorkflow(git_engine, test_orchestrator)
    
    @pytest.fixture
    def test_configs(self):
        """Create test configurations."""
        return [
            TestConfig(
                name="unit_tests",
                cmd="pytest tests/unit",
                timeout=30
            ),
            TestConfig(
                name="integration_tests",
                cmd="pytest tests/integration",
                timeout=60
            )
        ]
    
    def test_execute_workpad_not_found(self, workflow, git_engine, test_configs):
        """Test workflow when workpad is not found."""
        # Mock git engine to return None (workpad not found)
        git_engine.get_workpad = Mock(return_value=None)
        
        # Execute workflow
        result = workflow.execute("nonexistent-pad", test_configs)
        
        # Verify
        assert not result.success
        assert "Workpad nonexistent-pad not found" in result.message
        assert any("❌" in detail for detail in result.details)
        
        # Verify git engine was called
        git_engine.get_workpad.assert_called_once_with("nonexistent-pad")
    
    def test_execute_test_execution_fails(self, workflow, git_engine, test_orchestrator, test_configs):
        """Test workflow when test execution fails."""
        # Mock git engine to return workpad
        mock_workpad = Mock(spec=Workpad)
        mock_workpad.id = "test-pad"
        mock_workpad.title = "Test Feature"
        git_engine.get_workpad = Mock(return_value=mock_workpad)
        
        # Mock test orchestrator to raise exception
        test_orchestrator.run_tests_sync = Mock(side_effect=Exception("Test execution crashed"))
        
        # Execute workflow
        result = workflow.execute("test-pad", test_configs)
        
        # Verify
        assert not result.success
        assert "Test execution failed" in result.message
        assert "Test execution crashed" in result.message
        assert any("❌" in detail for detail in result.details)
    
    def test_execute_test_analysis_fails(self, workflow, git_engine, test_orchestrator, test_configs):
        """Test workflow when test analysis fails."""
        # Mock git engine
        mock_workpad = Mock(spec=Workpad)
        mock_workpad.id = "test-pad"
        mock_workpad.title = "Test Feature"
        git_engine.get_workpad = Mock(return_value=mock_workpad)
        
        # Mock test orchestrator to return results
        test_results = [
            TestResult(
                name="test_1",
                status=TestStatus.PASSED,
                duration_ms=100,
                exit_code=0,
                stdout="",
                stderr=""
            )
        ]
        test_orchestrator.run_tests_sync = Mock(return_value=test_results)
        
        # Mock test analyzer to raise exception
        with patch.object(workflow.test_analyzer, 'analyze', side_effect=Exception("Analysis crashed")):
            # Execute workflow
            result = workflow.execute("test-pad", test_configs)
        
        # Verify
        assert not result.success
        assert "Test analysis failed" in result.message
        assert "Analysis crashed" in result.message
        assert any("❌" in detail for detail in result.details)
    
    def test_execute_promotion_gate_evaluation_fails(self, workflow, git_engine, test_orchestrator, test_configs):
        """Test workflow when promotion gate evaluation fails."""
        # Mock git engine
        mock_workpad = Mock(spec=Workpad)
        mock_workpad.id = "test-pad"
        mock_workpad.title = "Test Feature"
        git_engine.get_workpad = Mock(return_value=mock_workpad)
        
        # Mock test orchestrator
        test_results = [
            TestResult(
                name="test_1",
                status=TestStatus.PASSED,
                duration_ms=100,
                exit_code=0,
                stdout="",
                stderr=""
            )
        ]
        test_orchestrator.run_tests_sync = Mock(return_value=test_results)
        
        # Mock test analyzer
        analysis = Mock(spec=TestAnalysis)
        analysis.status = "green"
        analysis.passed = 1
        analysis.total_tests = 1
        with patch.object(workflow.test_analyzer, 'analyze', return_value=analysis):
            # Mock promotion gate to raise exception
            with patch.object(workflow.promotion_gate, 'evaluate', side_effect=Exception("Gate evaluation crashed")):
                # Execute workflow
                result = workflow.execute("test-pad", test_configs)
        
        # Verify
        assert not result.success
        assert "Promotion gate evaluation failed" in result.message
        assert "Gate evaluation crashed" in result.message
        assert any("❌" in detail for detail in result.details)
    
    def test_execute_promotion_fails(self, workflow, git_engine, test_orchestrator, test_configs):
        """Test workflow when promotion fails."""
        # Mock git engine
        mock_workpad = Mock(spec=Workpad)
        mock_workpad.id = "test-pad"
        mock_workpad.title = "Test Feature"
        git_engine.get_workpad = Mock(return_value=mock_workpad)
        
        # Mock test orchestrator
        test_results = [
            TestResult(
                name="test_1",
                status=TestStatus.PASSED,
                duration_ms=100,
                exit_code=0,
                stdout="",
                stderr=""
            )
        ]
        test_orchestrator.run_tests_sync = Mock(return_value=test_results)
        
        # Mock test analyzer
        analysis = Mock(spec=TestAnalysis)
        analysis.status = "green"
        analysis.passed = 1
        analysis.total_tests = 1
        with patch.object(workflow.test_analyzer, 'analyze', return_value=analysis):
            # Mock promotion gate to approve
            decision = Mock(spec=PromotionDecision)
            decision.can_promote = True
            decision.reasons = ["✅ Tests passed"]
            decision.warnings = []
            with patch.object(workflow.promotion_gate, 'evaluate', return_value=decision):
                # Mock promote_workpad to fail
                git_engine.promote_workpad = Mock(side_effect=GitEngineError("Cannot promote"))
                
                # Execute workflow
                result = workflow.execute("test-pad", test_configs, auto_promote=True)
        
        # Verify
        assert not result.success
        assert "Promotion failed" in result.message
        assert "Cannot promote" in result.message
        assert any("❌" in detail for detail in result.details)
    
    def test_execute_with_test_timeout_and_errors(self, workflow, git_engine, test_orchestrator, test_configs):
        """Test workflow with timeout and error test results."""
        # Mock git engine
        mock_workpad = Mock(spec=Workpad)
        mock_workpad.id = "test-pad"
        mock_workpad.title = "Test Feature"
        git_engine.get_workpad = Mock(return_value=mock_workpad)
        
        # Mock test orchestrator with timeout and error results
        test_results = [
            TestResult(
                name="test_passed",
                status=TestStatus.PASSED,
                duration_ms=100,
                exit_code=0,
                stdout="",
                stderr=""
            ),
            TestResult(
                name="test_timeout",
                status=TestStatus.TIMEOUT,
                duration_ms=30000,
                exit_code=124,
                stdout="",
                stderr="Timeout exceeded"
            ),
            TestResult(
                name="test_error",
                status=TestStatus.ERROR,
                duration_ms=50,
                exit_code=1,
                stdout="",
                stderr="Import error",
                error="ModuleNotFoundError"
            )
        ]
        test_orchestrator.run_tests_sync = Mock(return_value=test_results)
        
        # Mock test analyzer to return analysis with timeouts and errors
        analysis = Mock(spec=TestAnalysis)
        analysis.status = "red"
        analysis.passed = 1
        analysis.failed = 0
        analysis.timeout = 1
        analysis.error = 1
        analysis.total_tests = 3
        analysis.failure_patterns = [
            FailurePattern(
                category=FailureCategory.TIMEOUT,
                message="Test timed out after 30s",
                count=1,
                file="test_timeout"
            )
        ]
        analysis.suggested_actions = ["Increase timeout for slow tests"]
        
        with patch.object(workflow.test_analyzer, 'analyze', return_value=analysis):
            # Mock promotion gate to reject
            decision = Mock(spec=PromotionDecision)
            decision.can_promote = False
            decision.reasons = ["❌ Tests have timeouts and errors"]
            decision.warnings = []
            decision.decision = PromotionDecisionType.REJECT
            with patch.object(workflow.promotion_gate, 'evaluate', return_value=decision):
                # Execute workflow
                result = workflow.execute("test-pad", test_configs)
        
        # Verify
        assert not result.success
        assert result.test_analysis is not None
        assert result.promotion_decision is not None
        assert "Cannot promote" in result.message
        # Check that timeout and error counts are shown in details
        details_text = "\n".join(result.details)
        assert "Timeout: 1" in details_text
        assert "Error: 1" in details_text
    
    def test_execute_with_manual_review_required(self, workflow, git_engine, test_orchestrator, test_configs):
        """Test workflow when manual review is required."""
        # Mock git engine
        mock_workpad = Mock(spec=Workpad)
        mock_workpad.id = "test-pad"
        mock_workpad.title = "Test Feature"
        git_engine.get_workpad = Mock(return_value=mock_workpad)
        
        # Mock test orchestrator
        test_results = [
            TestResult(
                name="test_1",
                status=TestStatus.PASSED,
                duration_ms=100,
                exit_code=0,
                stdout="",
                stderr=""
            )
        ]
        test_orchestrator.run_tests_sync = Mock(return_value=test_results)
        
        # Mock test analyzer
        analysis = Mock(spec=TestAnalysis)
        analysis.status = "yellow"  # Warning status
        analysis.passed = 1
        analysis.failed = 0
        analysis.timeout = 0
        analysis.error = 0
        analysis.total_tests = 1
        analysis.failure_patterns = []
        analysis.suggested_actions = []
        
        with patch.object(workflow.test_analyzer, 'analyze', return_value=analysis):
            # Mock promotion gate to require manual review
            decision = Mock(spec=PromotionDecision)
            decision.can_promote = False
            decision.reasons = ["⚠️ Manual review needed"]
            decision.warnings = ["No test coverage for critical files"]
            decision.decision = PromotionDecisionType.MANUAL_REVIEW
            with patch.object(workflow.promotion_gate, 'evaluate', return_value=decision):
                # Execute workflow
                result = workflow.execute("test-pad", test_configs)
        
        # Verify
        assert not result.success
        assert "Cannot promote" in result.message
        # Check that manual review message is shown
        details_text = "\n".join(result.details)
        assert "👀 Manual review required" in details_text
    
    def test_execute_ready_to_promote_but_auto_promote_disabled(self, workflow, git_engine, test_orchestrator, test_configs):
        """Test workflow when ready to promote but auto-promote is disabled."""
        # Mock git engine
        mock_workpad = Mock(spec=Workpad)
        mock_workpad.id = "test-pad"
        mock_workpad.title = "Test Feature"
        git_engine.get_workpad = Mock(return_value=mock_workpad)
        
        # Mock test orchestrator
        test_results = [
            TestResult(
                name="test_1",
                status=TestStatus.PASSED,
                duration_ms=100,
                exit_code=0,
                stdout="",
                stderr=""
            )
        ]
        test_orchestrator.run_tests_sync = Mock(return_value=test_results)
        
        # Mock test analyzer
        analysis = Mock(spec=TestAnalysis)
        analysis.status = "green"
        analysis.passed = 1
        analysis.total_tests = 1
        with patch.object(workflow.test_analyzer, 'analyze', return_value=analysis):
            # Mock promotion gate to approve
            decision = Mock(spec=PromotionDecision)
            decision.can_promote = True
            decision.reasons = ["✅ All checks passed"]
            decision.warnings = []
            with patch.object(workflow.promotion_gate, 'evaluate', return_value=decision):
                # Execute workflow with auto_promote=False
                result = workflow.execute("test-pad", test_configs, auto_promote=False)
        
        # Verify
        assert not result.success  # No promotion happened
        assert "ready to promote" in result.message
        assert "auto-promote disabled" in result.message
        # Check that manual promotion suggestion is shown
        details_text = "\n".join(result.details)
        assert "sologit pad promote" in details_text


class TestAutoMergeResultDataclass:
    """Tests for AutoMergeResult dataclass."""
    
    def test_auto_merge_result_creation(self):
        """Test creating AutoMergeResult."""
        result = AutoMergeResult(
            success=True,
            pad_id="test-pad",
            commit_hash="abc123",
            message="Success"
        )
        
        assert result.success
        assert result.pad_id == "test-pad"
        assert result.commit_hash == "abc123"
        assert result.message == "Success"
        assert result.details == []  # Default empty list
    
    def test_auto_merge_result_with_details(self):
        """Test AutoMergeResult with details list."""
        details = ["Step 1: Complete", "Step 2: Complete"]
        result = AutoMergeResult(
            success=True,
            pad_id="test-pad",
            details=details
        )
        
        assert result.details == details
    
    def test_auto_merge_result_post_init(self):
        """Test AutoMergeResult __post_init__ creates empty details list."""
        result = AutoMergeResult(success=False, pad_id="test-pad")
        
        assert result.details is not None
        assert isinstance(result.details, list)
        assert len(result.details) == 0


class TestAutoMergeWorkflowFormatResult:
    """Tests for AutoMergeWorkflow.format_result."""
    
    @pytest.fixture
    def workflow(self):
        """Create workflow instance with mocks."""
        git_engine = Mock(spec=GitEngine)
        test_orchestrator = Mock(spec=TestOrchestrator)
        return AutoMergeWorkflow(git_engine, test_orchestrator)
    
    def test_format_result_success(self, workflow):
        """Test formatting successful result."""
        result = AutoMergeResult(
            success=True,
            pad_id="test-pad",
            commit_hash="abc123def456",
            message="Successfully promoted to trunk",
            details=[
                "📝 Workpad: Test Feature",
                "🧪 Running 2 tests...",
                "✅ Promoted to trunk: abc123de"
            ]
        )
        
        formatted = workflow.format_result(result)
        
        # Verify
        assert "AUTO-MERGE WORKFLOW RESULT" in formatted
        assert "✅ SUCCESS" in formatted
        assert "Successfully promoted to trunk" in formatted
        assert "📌 Commit: abc123def456" in formatted
        assert "Test Feature" in formatted
    
    def test_format_result_failure(self, workflow):
        """Test formatting failed result."""
        result = AutoMergeResult(
            success=False,
            pad_id="test-pad",
            message="Cannot promote - tests failed",
            details=[
                "📝 Workpad: Test Feature",
                "🧪 Running 2 tests...",
                "❌ Tests failed"
            ]
        )
        
        formatted = workflow.format_result(result)
        
        # Verify
        assert "AUTO-MERGE WORKFLOW RESULT" in formatted
        assert "❌ FAILED" in formatted
        assert "Cannot promote" in formatted
        assert "tests failed" in formatted
    
    def test_format_result_with_empty_details(self, workflow):
        """Test formatting result with empty details."""
        result = AutoMergeResult(
            success=True,
            pad_id="test-pad",
            message="Success"
        )
        
        formatted = workflow.format_result(result)
        
        # Verify basic formatting works
        assert "AUTO-MERGE WORKFLOW RESULT" in formatted
        assert "Success" in formatted
