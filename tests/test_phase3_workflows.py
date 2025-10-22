"""
Tests for Phase 3 workflows (auto-merge, CI, rollback).
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from sologit.engines.git_engine import GitEngine
from sologit.engines.test_orchestrator import TestOrchestrator, TestConfig, TestStatus
from sologit.workflows.auto_merge import AutoMergeWorkflow, AutoMergeResult
from sologit.workflows.promotion_gate import PromotionRules
from sologit.workflows.ci_orchestrator import CIOrchestrator, CIResult, CIStatus
from sologit.workflows.rollback_handler import RollbackHandler, RollbackResult


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
def test_orchestrator(git_engine):
    """Create TestOrchestrator."""
    return TestOrchestrator(git_engine)


@pytest.fixture
def test_repo(git_engine, temp_dir):
    """Create a test repository."""
    repo_path = temp_dir / "test_repo"
    repo_path.mkdir()
    (repo_path / "README.md").write_text("# Test Repo\n")
    
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


class TestAutoMergeWorkflow:
    """Tests for AutoMergeWorkflow."""
    
    def test_workflow_initialization(self, git_engine, test_orchestrator):
        """Test workflow can be initialized."""
        workflow = AutoMergeWorkflow(git_engine, test_orchestrator)
        
        assert workflow.git_engine == git_engine
        assert workflow.test_orchestrator == test_orchestrator
        assert workflow.test_analyzer is not None
        assert workflow.promotion_gate is not None
    
    def test_workflow_with_custom_rules(self, git_engine, test_orchestrator):
        """Test workflow with custom promotion rules."""
        rules = PromotionRules(require_tests=False)
        workflow = AutoMergeWorkflow(git_engine, test_orchestrator, rules)
        
        assert workflow.promotion_gate.rules.require_tests is False
    
    def test_execute_nonexistent_workpad(self, git_engine, test_orchestrator):
        """Test executing workflow on non-existent workpad."""
        workflow = AutoMergeWorkflow(git_engine, test_orchestrator)
        tests = [TestConfig(name="test", cmd="echo 'pass'", timeout=10)]
        
        result = workflow.execute("nonexistent", tests)
        
        assert not result.success
        assert "not found" in result.message.lower()
    
    def test_format_result(self, git_engine, test_orchestrator):
        """Test formatting workflow result."""
        workflow = AutoMergeWorkflow(git_engine, test_orchestrator)
        
        result = AutoMergeResult(
            success=True,
            pad_id="test_pad",
            commit_hash="abc123",
            message="Success",
            details=["Step 1 complete", "Step 2 complete"]
        )
        
        formatted = workflow.format_result(result)
        
        assert isinstance(formatted, str)
        assert "AUTO-MERGE WORKFLOW" in formatted
        assert "SUCCESS" in formatted
        assert "abc123" in formatted


class TestCIOrchestrator:
    """Tests for CIOrchestrator."""
    
    def test_orchestrator_initialization(self, git_engine, test_orchestrator):
        """Test CI orchestrator can be initialized."""
        orchestrator = CIOrchestrator(git_engine, test_orchestrator)
        
        assert orchestrator.git_engine == git_engine
        assert orchestrator.test_orchestrator == test_orchestrator
    
    def test_run_smoke_tests_nonexistent_repo(self, git_engine, test_orchestrator):
        """Test running smoke tests on non-existent repo."""
        orchestrator = CIOrchestrator(git_engine, test_orchestrator)
        tests = [TestConfig(name="smoke", cmd="echo 'test'", timeout=10)]
        
        result = orchestrator.run_smoke_tests("nonexistent", "abc123", tests)
        
        assert result.status == CIStatus.FAILURE
        assert "not found" in result.message.lower()
    
    def test_ci_result_is_green(self):
        """Test CI result green check."""
        result = CIResult(
            repo_id="test",
            commit_hash="abc123",
            status=CIStatus.SUCCESS,
            duration_ms=1000,
            test_results=[]
        )
        
        assert result.is_green
        assert not result.is_red
    
    def test_ci_result_is_red(self):
        """Test CI result red check."""
        result = CIResult(
            repo_id="test",
            commit_hash="abc123",
            status=CIStatus.FAILURE,
            duration_ms=1000,
            test_results=[]
        )
        
        assert result.is_red
        assert not result.is_green
    
    def test_format_ci_result(self, git_engine, test_orchestrator):
        """Test formatting CI result."""
        orchestrator = CIOrchestrator(git_engine, test_orchestrator)
        
        result = CIResult(
            repo_id="test",
            commit_hash="abc123",
            status=CIStatus.SUCCESS,
            duration_ms=2000,
            test_results=[],
            message="All tests passed"
        )
        
        formatted = orchestrator.format_result(result)
        
        assert isinstance(formatted, str)
        assert "CI SMOKE TEST" in formatted
        assert "SUCCESS" in formatted


class TestRollbackHandler:
    """Tests for RollbackHandler."""
    
    def test_handler_initialization(self, git_engine):
        """Test rollback handler can be initialized."""
        handler = RollbackHandler(git_engine)
        
        assert handler.git_engine == git_engine
    
    def test_handle_passing_ci(self, git_engine):
        """Test handling passing CI (no rollback needed)."""
        handler = RollbackHandler(git_engine)
        
        ci_result = CIResult(
            repo_id="test",
            commit_hash="abc123",
            status=CIStatus.SUCCESS,
            duration_ms=1000,
            test_results=[]
        )
        
        result = handler.handle_failed_ci(ci_result)
        
        assert result.success
        assert "no rollback needed" in result.message.lower()
    
    def test_handle_failed_ci_nonexistent_repo(self, git_engine):
        """Test handling failed CI for non-existent repo."""
        handler = RollbackHandler(git_engine)
        
        ci_result = CIResult(
            repo_id="nonexistent",
            commit_hash="abc123",
            status=CIStatus.FAILURE,
            duration_ms=1000,
            test_results=[]
        )
        
        result = handler.handle_failed_ci(ci_result)
        
        assert not result.success
    
    def test_format_rollback_result(self, git_engine):
        """Test formatting rollback result."""
        handler = RollbackHandler(git_engine)
        
        result = RollbackResult(
            success=True,
            repo_id="test",
            reverted_commit="abc123",
            new_pad_id="fix_pad",
            message="Rollback complete"
        )
        
        formatted = handler.format_result(result)
        
        assert isinstance(formatted, str)
        assert "ROLLBACK" in formatted
        assert "SUCCESSFUL" in formatted
        assert "abc123" in formatted


class TestPhase3Integration:
    """Integration tests for Phase 3 workflows."""
    
    def test_ci_status_enum(self):
        """Test CI status enum values."""
        assert CIStatus.SUCCESS.value == "success"
        assert CIStatus.FAILURE.value == "failure"
        assert CIStatus.PENDING.value == "pending"
    
    def test_auto_merge_result_dataclass(self):
        """Test AutoMergeResult dataclass."""
        result = AutoMergeResult(
            success=True,
            pad_id="test",
            commit_hash="abc123"
        )
        
        assert result.success
        assert result.pad_id == "test"
        assert result.commit_hash == "abc123"
        assert result.details is not None
    
    def test_rollback_result_dataclass(self):
        """Test RollbackResult dataclass."""
        result = RollbackResult(
            success=True,
            repo_id="test",
            reverted_commit="abc123"
        )
        
        assert result.success
        assert result.repo_id == "test"
        assert result.reverted_commit == "abc123"
