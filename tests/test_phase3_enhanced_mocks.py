"""
Enhanced mock-based tests for Phase 3 components.

These tests don't require Docker and use mocks to test the logic
of auto-merge workflow and CI orchestrator.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from sologit.workflows.auto_merge import AutoMergeWorkflow, AutoMergeResult
from sologit.workflows.ci_orchestrator import CIOrchestrator, CIResult, CIStatus
from sologit.workflows.promotion_gate import PromotionGate, PromotionRules, PromotionDecisionType
from sologit.analysis.test_analyzer import TestAnalyzer, TestAnalysis, FailureCategory
from sologit.engines.test_orchestrator import TestConfig, TestResult, TestStatus
from sologit.core.workpad import Workpad
from sologit.core.repository import Repository


class TestAutoMergeWorkflowMocked:
    """Test auto-merge workflow with mocked dependencies."""
    
    def test_execute_with_green_tests_and_auto_promote(self):
        """Test successful auto-merge with green tests."""
        # Setup mocks
        git_engine = Mock()
        test_orchestrator = Mock()
        
        # Mock workpad
        workpad = Workpad(
            id="pad_123",
            repo_id="repo_456",
            title="test-feature",
            branch_name="pads/test-feature-123",
            
        )
        git_engine.get_workpad.return_value = workpad
        git_engine.can_promote.return_value = True
        git_engine.get_diff.return_value = "diff --git a/test.py b/test.py\n+new line"
        git_engine.promote_workpad.return_value = "def456"
        
        # Mock test results
        test_results = [
            TestResult(
                name="test_1",
                status=TestStatus.PASSED,
                duration_ms=100,
                exit_code=0,
                stdout="Test passed",
                stderr=""
            )
        ]
        test_orchestrator.run_tests_sync.return_value = test_results
        
        # Create workflow
        workflow = AutoMergeWorkflow(
            git_engine=git_engine,
            test_orchestrator=test_orchestrator
        )
        
        # Execute
        tests = [TestConfig(name="test_1", cmd="pytest", timeout=30)]
        result = workflow.execute(
            pad_id="pad_123",
            tests=tests,
            parallel=True,
            auto_promote=True
        )
        
        # Verify
        assert result.success is True
        assert result.commit_hash == "def456"
        assert "promoted to trunk" in result.message.lower()
        assert git_engine.promote_workpad.called
    
    def test_execute_with_red_tests_no_promote(self):
        """Test auto-merge with failed tests - should not promote."""
        # Setup mocks
        git_engine = Mock()
        test_orchestrator = Mock()
        
        # Mock workpad
        workpad = Workpad(
            id="pad_123",
            repo_id="repo_456",
            title="test-feature",
            branch_name="pads/test-feature-123",
            
        )
        git_engine.get_workpad.return_value = workpad
        
        # Mock test results with failure
        test_results = [
            TestResult(
                name="test_1",
                status=TestStatus.FAILED,
                duration_ms=100,
                exit_code=1,
                stdout="",
                stderr="AssertionError: test failed"
            )
        ]
        test_orchestrator.run_tests_sync.return_value = test_results
        
        # Create workflow
        workflow = AutoMergeWorkflow(
            git_engine=git_engine,
            test_orchestrator=test_orchestrator
        )
        
        # Execute
        tests = [TestConfig(name="test_1", cmd="pytest", timeout=30)]
        result = workflow.execute(
            pad_id="pad_123",
            tests=tests,
            parallel=True,
            auto_promote=True
        )
        
        # Verify
        assert result.success is False
        assert result.commit_hash is None
        assert "cannot promote" in result.message.lower()
        assert not git_engine.promote_workpad.called
    
    def test_execute_with_test_failure_shows_patterns(self):
        """Test that failure patterns are shown in result."""
        # Setup mocks
        git_engine = Mock()
        test_orchestrator = Mock()
        
        # Mock workpad
        workpad = Workpad(
            id="pad_123",
            repo_id="repo_456",
            title="test-feature",
            branch_name="pads/test-feature-123",
            
        )
        git_engine.get_workpad.return_value = workpad
        
        # Mock test results with import error
        test_results = [
            TestResult(
                name="test_1",
                status=TestStatus.FAILED,
                duration_ms=100,
                exit_code=1,
                stdout="",
                stderr="ImportError: No module named 'requests'"
            )
        ]
        test_orchestrator.run_tests_sync.return_value = test_results
        
        # Create workflow
        workflow = AutoMergeWorkflow(
            git_engine=git_engine,
            test_orchestrator=test_orchestrator
        )
        
        # Execute
        tests = [TestConfig(name="test_1", cmd="pytest", timeout=30)]
        result = workflow.execute(
            pad_id="pad_123",
            tests=tests,
            parallel=True,
            auto_promote=False
        )
        
        # Verify failure patterns are detected
        assert result.test_analysis is not None
        assert len(result.test_analysis.failure_patterns) > 0
        assert any("import" in str(p.category).lower() 
                  for p in result.test_analysis.failure_patterns)
        assert len(result.test_analysis.suggested_actions) > 0
    
    def test_execute_without_auto_promote(self):
        """Test auto-merge with auto_promote=False."""
        # Setup mocks
        git_engine = Mock()
        test_orchestrator = Mock()
        
        # Mock workpad
        workpad = Workpad(
            id="pad_123",
            repo_id="repo_456",
            title="test-feature",
            branch_name="pads/test-feature-123",
            
        )
        git_engine.get_workpad.return_value = workpad
        git_engine.can_promote.return_value = True
        git_engine.get_diff.return_value = "diff --git a/test.py b/test.py\n+new line"
        
        # Mock green tests
        test_results = [
            TestResult(
                name="test_1",
                status=TestStatus.PASSED,
                duration_ms=100,
                exit_code=0,
                stdout="Test passed",
                stderr=""
            )
        ]
        test_orchestrator.run_tests_sync.return_value = test_results
        
        # Create workflow
        workflow = AutoMergeWorkflow(
            git_engine=git_engine,
            test_orchestrator=test_orchestrator
        )
        
        # Execute
        tests = [TestConfig(name="test_1", cmd="pytest", timeout=30)]
        result = workflow.execute(
            pad_id="pad_123",
            tests=tests,
            parallel=True,
            auto_promote=False
        )
        
        # Verify - should not promote even though tests passed
        assert result.commit_hash is None
        assert "ready to promote" in result.message.lower()
        assert not git_engine.promote_workpad.called
    
    def test_format_result_success(self):
        """Test formatting of successful result."""
        workflow = AutoMergeWorkflow(
            git_engine=Mock(),
            test_orchestrator=Mock()
        )
        
        result = AutoMergeResult(
            success=True,
            pad_id="pad_123",
            commit_hash="abc123",
            message="Successfully promoted",
            details=["✅ All tests passed", "✅ Promoted to trunk"]
        )
        
        formatted = workflow.format_result(result)
        
        assert "SUCCESS" in formatted
        assert "abc123" in formatted
        assert "All tests passed" in formatted
    
    def test_format_result_failure(self):
        """Test formatting of failed result."""
        workflow = AutoMergeWorkflow(
            git_engine=Mock(),
            test_orchestrator=Mock()
        )
        
        result = AutoMergeResult(
            success=False,
            pad_id="pad_123",
            message="Tests failed",
            details=["❌ 1 test failed"]
        )
        
        formatted = workflow.format_result(result)
        
        assert "FAILED" in formatted
        assert "Tests failed" in formatted


class TestCIOrchestratorMocked:
    """Test CI orchestrator with mocked dependencies."""
    
    def test_run_smoke_tests_all_pass(self):
        """Test smoke tests with all passing."""
        # Setup mocks
        git_engine = Mock()
        test_orchestrator = Mock()
        
        # Mock repository
        repo = Repository(
            id="repo_123",
            name="test-repo",
            path="/tmp/test-repo",
            trunk_branch="main"
        )
        git_engine.get_repo.return_value = repo
        
        # Mock workpad creation/deletion
        mock_workpad = Workpad(
            id="temp_pad",
            repo_id="repo_123",
            title="ci-smoke",
            branch_name="pads/ci-smoke-abc123",
            
        )
        git_engine.create_workpad.return_value = mock_workpad
        git_engine.delete_workpad.return_value = None
        
        # Mock passing test results
        test_results = [
            TestResult(
                name="smoke_test_1",
                status=TestStatus.PASSED,
                duration_ms=500,
                exit_code=0,
                stdout="Test passed",
                stderr=""
            ),
            TestResult(
                name="smoke_test_2",
                status=TestStatus.PASSED,
                duration_ms=300,
                exit_code=0,
                stdout="Test passed",
                stderr=""
            )
        ]
        test_orchestrator.run_tests_sync.return_value = test_results
        
        # Create orchestrator
        orchestrator = CIOrchestrator(
            git_engine=git_engine,
            test_orchestrator=test_orchestrator
        )
        
        # Run smoke tests
        smoke_tests = [
            TestConfig(name="smoke_test_1", cmd="npm test", timeout=60),
            TestConfig(name="smoke_test_2", cmd="pytest", timeout=60)
        ]
        
        result = orchestrator.run_smoke_tests(
            repo_id="repo_123",
            commit_hash="abc123",
            smoke_tests=smoke_tests
        )
        
        # Verify
        assert result.status == CIStatus.SUCCESS
        assert result.is_green is True
        assert result.is_red is False
        assert len(result.test_results) == 2
        assert all(r.status == TestStatus.PASSED for r in result.test_results)
    
    def test_run_smoke_tests_with_failures(self):
        """Test smoke tests with failures."""
        # Setup mocks
        git_engine = Mock()
        test_orchestrator = Mock()
        
        # Mock repository
        repo = Repository(
            id="repo_123",
            name="test-repo",
            path="/tmp/test-repo",
            trunk_branch="main"
        )
        git_engine.get_repo.return_value = repo
        
        # Mock workpad
        mock_workpad = Workpad(
            id="temp_pad",
            repo_id="repo_123",
            title="ci-smoke",
            branch_name="pads/ci-smoke-abc123",
            
        )
        git_engine.create_workpad.return_value = mock_workpad
        
        # Mock test results with failure
        test_results = [
            TestResult(
                name="smoke_test_1",
                status=TestStatus.PASSED,
                duration_ms=500,
                exit_code=0,
                stdout="Test passed",
                stderr=""
            ),
            TestResult(
                name="smoke_test_2",
                status=TestStatus.FAILED,
                duration_ms=300,
                exit_code=1,
                stdout="",
                stderr="Test failed"
            )
        ]
        test_orchestrator.run_tests_sync.return_value = test_results
        
        # Create orchestrator
        orchestrator = CIOrchestrator(
            git_engine=git_engine,
            test_orchestrator=test_orchestrator
        )
        
        # Run smoke tests
        smoke_tests = [
            TestConfig(name="smoke_test_1", cmd="npm test", timeout=60),
            TestConfig(name="smoke_test_2", cmd="pytest", timeout=60)
        ]
        
        result = orchestrator.run_smoke_tests(
            repo_id="repo_123",
            commit_hash="abc123",
            smoke_tests=smoke_tests
        )
        
        # Verify
        assert result.status == CIStatus.FAILURE
        assert result.is_green is False
        assert result.is_red is True
        assert "1 tests failed" in result.message
    
    def test_run_smoke_tests_with_timeouts(self):
        """Test smoke tests with timeouts."""
        # Setup mocks
        git_engine = Mock()
        test_orchestrator = Mock()
        
        # Mock repository
        repo = Repository(
            id="repo_123",
            name="test-repo",
            path="/tmp/test-repo",
            trunk_branch="main"
        )
        git_engine.get_repo.return_value = repo
        
        # Mock workpad
        mock_workpad = Workpad(
            id="temp_pad",
            repo_id="repo_123",
            title="ci-smoke",
            branch_name="pads/ci-smoke-abc123",
            
        )
        git_engine.create_workpad.return_value = mock_workpad
        
        # Mock test results with timeout
        test_results = [
            TestResult(
                name="smoke_test_1",
                status=TestStatus.TIMEOUT,
                duration_ms=60000,
                exit_code=-1,
                stdout="",
                stderr="Test timed out"
            )
        ]
        test_orchestrator.run_tests_sync.return_value = test_results
        
        # Create orchestrator
        orchestrator = CIOrchestrator(
            git_engine=git_engine,
            test_orchestrator=test_orchestrator
        )
        
        # Run smoke tests
        smoke_tests = [
            TestConfig(name="smoke_test_1", cmd="npm test", timeout=60)
        ]
        
        result = orchestrator.run_smoke_tests(
            repo_id="repo_123",
            commit_hash="abc123",
            smoke_tests=smoke_tests
        )
        
        # Verify
        assert result.status == CIStatus.UNSTABLE
        assert "timed out" in result.message.lower()
    
    def test_run_smoke_tests_repo_not_found(self):
        """Test smoke tests with non-existent repository."""
        # Setup mocks
        git_engine = Mock()
        test_orchestrator = Mock()
        
        # Mock repository not found
        git_engine.get_repo.return_value = None
        
        # Create orchestrator
        orchestrator = CIOrchestrator(
            git_engine=git_engine,
            test_orchestrator=test_orchestrator
        )
        
        # Run smoke tests
        smoke_tests = [TestConfig(name="smoke_test", cmd="pytest", timeout=60)]
        
        result = orchestrator.run_smoke_tests(
            repo_id="nonexistent",
            commit_hash="abc123",
            smoke_tests=smoke_tests
        )
        
        # Verify
        assert result.status == CIStatus.FAILURE
        assert "not found" in result.message.lower()
    
    def test_format_result_success(self):
        """Test formatting of successful CI result."""
        orchestrator = CIOrchestrator(
            git_engine=Mock(),
            test_orchestrator=Mock()
        )
        
        result = CIResult(
            repo_id="repo_123",
            commit_hash="abc123",
            status=CIStatus.SUCCESS,
            duration_ms=5000,
            test_results=[
                TestResult(
                    name="test_1",
                    status=TestStatus.PASSED,
                    duration_ms=1000,
                    exit_code=0,
                    stdout="passed",
                    stderr=""
                )
            ],
            message="All smoke tests passed"
        )
        
        formatted = orchestrator.format_result(result)
        
        assert "SUCCESS" in formatted
        assert "abc123" in formatted
        assert "All smoke tests passed" in formatted
        assert "Passed: 1" in formatted
    
    def test_format_result_failure(self):
        """Test formatting of failed CI result."""
        orchestrator = CIOrchestrator(
            git_engine=Mock(),
            test_orchestrator=Mock()
        )
        
        result = CIResult(
            repo_id="repo_123",
            commit_hash="abc123",
            status=CIStatus.FAILURE,
            duration_ms=3000,
            test_results=[
                TestResult(
                    name="test_1",
                    status=TestStatus.FAILED,
                    duration_ms=1000,
                    exit_code=1,
                    stdout="",
                    stderr="failed"
                )
            ],
            message="1 tests failed"
        )
        
        formatted = orchestrator.format_result(result)
        
        assert "FAILURE" in formatted
        assert "Failed: 1" in formatted
        assert "test_1" in formatted


class TestIntegrationWorkflow:
    """Test integration between components."""
    
    def test_full_workflow_green_path(self):
        """Test complete workflow from tests to promotion."""
        # Setup mocks
        git_engine = Mock()
        test_orchestrator = Mock()
        
        # Mock workpad
        workpad = Workpad(
            id="pad_123",
            repo_id="repo_456",
            title="feature-x",
            branch_name="pads/feature-x-123",
            
        )
        git_engine.get_workpad.return_value = workpad
        git_engine.can_promote.return_value = True
        git_engine.get_diff.return_value = "diff --git a/feature.py b/feature.py\n+new feature"
        git_engine.promote_workpad.return_value = "def456"
        
        # Mock passing tests
        test_results = [
            TestResult(
                name="test_feature",
                status=TestStatus.PASSED,
                duration_ms=200,
                exit_code=0,
                stdout="All tests passed",
                stderr=""
            )
        ]
        test_orchestrator.run_tests_sync.return_value = test_results
        
        # Create workflow with strict rules
        rules = PromotionRules(
            require_tests=True,
            require_all_tests_pass=True,
            require_fast_forward=True
        )
        
        workflow = AutoMergeWorkflow(
            git_engine=git_engine,
            test_orchestrator=test_orchestrator,
            promotion_rules=rules
        )
        
        # Execute workflow
        tests = [TestConfig(name="test_feature", cmd="pytest", timeout=30)]
        result = workflow.execute(
            pad_id="pad_123",
            tests=tests,
            parallel=True,
            auto_promote=True
        )
        
        # Verify complete flow
        assert result.success is True
        assert result.commit_hash == "def456"
        assert result.test_analysis is not None
        assert result.test_analysis.status == "green"
        assert result.promotion_decision is not None
        assert result.promotion_decision.can_promote is True
        assert git_engine.promote_workpad.called
    
    def test_full_workflow_red_path(self):
        """Test complete workflow with failing tests."""
        # Setup mocks
        git_engine = Mock()
        test_orchestrator = Mock()
        
        # Mock workpad
        workpad = Workpad(
            id="pad_123",
            repo_id="repo_456",
            title="feature-x",
            branch_name="pads/feature-x-123",
            
        )
        git_engine.get_workpad.return_value = workpad
        
        # Mock failing tests
        test_results = [
            TestResult(
                name="test_feature",
                status=TestStatus.FAILED,
                duration_ms=200,
                exit_code=1,
                stdout="",
                stderr="AssertionError: Expected True, got False"
            )
        ]
        test_orchestrator.run_tests_sync.return_value = test_results
        
        # Create workflow
        workflow = AutoMergeWorkflow(
            git_engine=git_engine,
            test_orchestrator=test_orchestrator
        )
        
        # Execute workflow
        tests = [TestConfig(name="test_feature", cmd="pytest", timeout=30)]
        result = workflow.execute(
            pad_id="pad_123",
            tests=tests,
            parallel=True,
            auto_promote=True
        )
        
        # Verify rejection
        assert result.success is False
        assert result.commit_hash is None
        assert result.test_analysis.status == "red"
        assert result.promotion_decision.can_promote is False
        assert not git_engine.promote_workpad.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
