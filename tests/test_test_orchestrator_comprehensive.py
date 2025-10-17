"""
Comprehensive tests for TestOrchestrator to achieve >90% coverage.

This test suite uses mocks to test all code paths in the TestOrchestrator
without requiring Docker to be available.
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from pathlib import Path
from docker.errors import DockerException

from sologit.engines.test_orchestrator import (
    TestOrchestrator,
    TestConfig,
    TestResult,
    TestStatus,
    TestOrchestratorError,
)
from sologit.engines.git_engine import WorkpadNotFoundError


@pytest.fixture
def mock_git_engine():
    """Create mock git engine."""
    engine = Mock()
    
    # Mock workpad
    workpad = Mock()
    workpad.id = "pad_123"
    workpad.repo_id = "repo_456"
    engine.get_workpad.return_value = workpad
    
    # Mock repository
    repo = Mock()
    repo.path = Path("/tmp/test-repo")
    engine.get_repo.return_value = repo
    
    return engine


@pytest.fixture
def mock_docker_client():
    """Create mock docker client."""
    client = Mock()
    
    # Mock container
    container = Mock()
    container.id = "abc123def456"
    container.start = Mock()
    container.stop = Mock()
    container.remove = Mock()
    container.wait.return_value = {'StatusCode': 0}
    container.logs.return_value = b"Test output"
    
    client.containers.create.return_value = container
    
    return client


class TestTestOrchestratorInitialization:
    """Test TestOrchestrator initialization."""
    
    def test_init_success(self, mock_git_engine):
        """Test successful initialization with Docker available."""
        with patch('docker.from_env') as mock_docker:
            mock_docker.return_value = Mock()
            
            orchestrator = TestOrchestrator(mock_git_engine, "python:3.11-slim")
            
            assert orchestrator.git_engine == mock_git_engine
            assert orchestrator.sandbox_image == "python:3.11-slim"
            assert orchestrator.docker_client is not None
    
    def test_init_docker_not_available(self, mock_git_engine):
        """Test initialization fails when Docker is not available."""
        with patch('docker.from_env') as mock_docker:
            mock_docker.side_effect = DockerException("Docker not found")
            
            with pytest.raises(TestOrchestratorError) as exc_info:
                TestOrchestrator(mock_git_engine)
            
            assert "Docker not available" in str(exc_info.value)


class TestRunTestsAsync:
    """Test async run_tests method."""
    
    @pytest.mark.asyncio
    async def test_run_tests_parallel(self, mock_git_engine, mock_docker_client):
        """Test running tests in parallel."""
        with patch('docker.from_env') as mock_docker:
            mock_docker.return_value = mock_docker_client
            
            orchestrator = TestOrchestrator(mock_git_engine)
            
            tests = [
                TestConfig(name="test1", cmd="echo 'test1'", timeout=10),
                TestConfig(name="test2", cmd="echo 'test2'", timeout=10),
            ]
            
            results = await orchestrator.run_tests("pad_123", tests, parallel=True)
            
            assert len(results) == 2
            assert all(r.status == TestStatus.PASSED for r in results)
    
    @pytest.mark.asyncio
    async def test_run_tests_sequential(self, mock_git_engine, mock_docker_client):
        """Test running tests sequentially."""
        with patch('docker.from_env') as mock_docker:
            mock_docker.return_value = mock_docker_client
            
            orchestrator = TestOrchestrator(mock_git_engine)
            
            tests = [
                TestConfig(name="test1", cmd="echo 'test1'", timeout=10),
                TestConfig(name="test2", cmd="echo 'test2'", timeout=10),
            ]
            
            results = await orchestrator.run_tests("pad_123", tests, parallel=False)
            
            assert len(results) == 2
            assert all(r.status == TestStatus.PASSED for r in results)
    
    @pytest.mark.asyncio
    async def test_run_tests_workpad_not_found(self, mock_git_engine, mock_docker_client):
        """Test running tests with non-existent workpad."""
        with patch('docker.from_env') as mock_docker:
            mock_docker.return_value = mock_docker_client
            
            orchestrator = TestOrchestrator(mock_git_engine)
            mock_git_engine.get_workpad.return_value = None
            
            tests = [TestConfig(name="test1", cmd="echo 'test1'", timeout=10)]
            
            with pytest.raises(WorkpadNotFoundError):
                await orchestrator.run_tests("pad_invalid", tests)


class TestRunTestsSync:
    """Test synchronous run_tests_sync method."""
    
    def test_run_tests_sync(self, mock_git_engine, mock_docker_client):
        """Test synchronous wrapper for run_tests."""
        with patch('docker.from_env') as mock_docker:
            mock_docker.return_value = mock_docker_client
            
            orchestrator = TestOrchestrator(mock_git_engine)
            
            tests = [TestConfig(name="test1", cmd="echo 'test1'", timeout=10)]
            
            results = orchestrator.run_tests_sync("pad_123", tests)
            
            assert len(results) == 1
            assert results[0].status == TestStatus.PASSED


class TestSequentialExecution:
    """Test sequential test execution."""
    
    @pytest.mark.asyncio
    async def test_sequential_early_exit_on_failure(self, mock_git_engine, mock_docker_client):
        """Test that sequential execution stops on first failure."""
        # Mock first test to fail, second test should not run
        container1 = Mock()
        container1.id = "abc123"
        container1.start = Mock()
        container1.wait.return_value = {'StatusCode': 1}  # Failure
        container1.logs.return_value = b"Test failed"
        container1.remove = Mock()
        
        mock_docker_client.containers.create.return_value = container1
        
        with patch('docker.from_env') as mock_docker:
            mock_docker.return_value = mock_docker_client
            
            orchestrator = TestOrchestrator(mock_git_engine)
            
            tests = [
                TestConfig(name="test1", cmd="exit 1", timeout=10),
                TestConfig(name="test2", cmd="echo 'test2'", timeout=10),
            ]
            
            results = await orchestrator.run_tests("pad_123", tests, parallel=False)
            
            # Should only have 1 result (first test), second test should not run
            assert len(results) == 1
            assert results[0].status == TestStatus.FAILED


class TestParallelExecution:
    """Test parallel test execution with dependencies."""
    
    @pytest.mark.asyncio
    async def test_parallel_with_dependencies(self, mock_git_engine, mock_docker_client):
        """Test parallel execution respects dependencies."""
        with patch('docker.from_env') as mock_docker:
            mock_docker.return_value = mock_docker_client
            
            orchestrator = TestOrchestrator(mock_git_engine)
            
            tests = [
                TestConfig(name="test1", cmd="echo 'test1'", timeout=10),
                TestConfig(name="test2", cmd="echo 'test2'", timeout=10, depends_on=["test1"]),
                TestConfig(name="test3", cmd="echo 'test3'", timeout=10, depends_on=["test1"]),
            ]
            
            results = await orchestrator.run_tests("pad_123", tests, parallel=True)
            
            assert len(results) == 3
            # Results should maintain order
            assert results[0].name == "test1"
    
    @pytest.mark.asyncio
    async def test_parallel_deadlock_detection(self, mock_git_engine, mock_docker_client):
        """Test deadlock detection in parallel execution."""
        with patch('docker.from_env') as mock_docker:
            mock_docker.return_value = mock_docker_client
            
            orchestrator = TestOrchestrator(mock_git_engine)
            
            # Create circular dependency
            tests = [
                TestConfig(name="test1", cmd="echo 'test1'", timeout=10, depends_on=["test2"]),
                TestConfig(name="test2", cmd="echo 'test2'", timeout=10, depends_on=["test1"]),
            ]
            
            results = await orchestrator.run_tests("pad_123", tests, parallel=True)
            
            # Should detect deadlock and return empty results
            assert len(results) == 0


class TestSingleTestExecution:
    """Test single test execution in Docker container."""
    
    @pytest.mark.asyncio
    async def test_run_single_test_success(self, mock_git_engine, mock_docker_client):
        """Test successful test execution."""
        with patch('docker.from_env') as mock_docker:
            mock_docker.return_value = mock_docker_client
            
            orchestrator = TestOrchestrator(mock_git_engine)
            
            test = TestConfig(name="test1", cmd="echo 'success'", timeout=10)
            result = await orchestrator._run_single_test(Path("/tmp/repo"), test)
            
            assert result.name == "test1"
            assert result.status == TestStatus.PASSED
            assert result.exit_code == 0
            assert "Test output" in result.stdout
    
    @pytest.mark.asyncio
    async def test_run_single_test_failure(self, mock_git_engine, mock_docker_client):
        """Test failed test execution."""
        container = Mock()
        container.id = "abc123"
        container.start = Mock()
        container.wait.return_value = {'StatusCode': 1}  # Failure
        container.logs.return_value = b"Test failed"
        container.remove = Mock()
        
        mock_docker_client.containers.create.return_value = container
        
        with patch('docker.from_env') as mock_docker:
            mock_docker.return_value = mock_docker_client
            
            orchestrator = TestOrchestrator(mock_git_engine)
            
            test = TestConfig(name="test1", cmd="exit 1", timeout=10)
            result = await orchestrator._run_single_test(Path("/tmp/repo"), test)
            
            assert result.name == "test1"
            assert result.status == TestStatus.FAILED
            assert result.exit_code == 1
    
    @pytest.mark.asyncio
    async def test_run_single_test_timeout(self, mock_git_engine, mock_docker_client):
        """Test test timeout handling."""
        container = Mock()
        container.id = "abc123"
        container.start = Mock()
        container.stop = Mock()
        container.wait.side_effect = Exception("Timeout")
        container.remove = Mock()
        
        mock_docker_client.containers.create.return_value = container
        
        with patch('docker.from_env') as mock_docker:
            mock_docker.return_value = mock_docker_client
            
            orchestrator = TestOrchestrator(mock_git_engine)
            
            test = TestConfig(name="test1", cmd="sleep 1000", timeout=1)
            result = await orchestrator._run_single_test(Path("/tmp/repo"), test)
            
            assert result.name == "test1"
            assert result.status == TestStatus.TIMEOUT
            assert result.exit_code == -1
            assert "timed out" in result.stdout
    
    @pytest.mark.asyncio
    async def test_run_single_test_error(self, mock_git_engine, mock_docker_client):
        """Test error handling during test execution."""
        mock_docker_client.containers.create.side_effect = Exception("Container creation failed")
        
        with patch('docker.from_env') as mock_docker:
            mock_docker.return_value = mock_docker_client
            
            orchestrator = TestOrchestrator(mock_git_engine)
            
            test = TestConfig(name="test1", cmd="echo 'test'", timeout=10)
            result = await orchestrator._run_single_test(Path("/tmp/repo"), test)
            
            assert result.name == "test1"
            assert result.status == TestStatus.ERROR
            assert result.exit_code == -1
            assert result.error is not None


class TestDependencyGraph:
    """Test dependency graph building."""
    
    def test_build_dependency_graph(self, mock_git_engine):
        """Test building dependency graph from test configs."""
        with patch('docker.from_env') as mock_docker:
            mock_docker.return_value = Mock()
            
            orchestrator = TestOrchestrator(mock_git_engine)
            
            tests = [
                TestConfig(name="test1", cmd="echo 'test1'"),
                TestConfig(name="test2", cmd="echo 'test2'", depends_on=["test1"]),
                TestConfig(name="test3", cmd="echo 'test3'", depends_on=["test1", "test2"]),
            ]
            
            graph = orchestrator._build_dependency_graph(tests)
            
            assert graph["test1"] == []
            assert graph["test2"] == ["test1"]
            assert graph["test3"] == ["test1", "test2"]


class TestUtilityMethods:
    """Test utility methods."""
    
    def test_all_tests_passed_true(self, mock_git_engine):
        """Test all_tests_passed returns True when all tests pass."""
        with patch('docker.from_env') as mock_docker:
            mock_docker.return_value = Mock()
            
            orchestrator = TestOrchestrator(mock_git_engine)
            
            results = [
                TestResult("test1", TestStatus.PASSED, 100, 0, "out", "err"),
                TestResult("test2", TestStatus.PASSED, 200, 0, "out", "err"),
            ]
            
            assert orchestrator.all_tests_passed(results) is True
    
    def test_all_tests_passed_false(self, mock_git_engine):
        """Test all_tests_passed returns False when any test fails."""
        with patch('docker.from_env') as mock_docker:
            mock_docker.return_value = Mock()
            
            orchestrator = TestOrchestrator(mock_git_engine)
            
            results = [
                TestResult("test1", TestStatus.PASSED, 100, 0, "out", "err"),
                TestResult("test2", TestStatus.FAILED, 200, 1, "out", "err"),
            ]
            
            assert orchestrator.all_tests_passed(results) is False
    
    def test_get_summary_all_passed(self, mock_git_engine):
        """Test get_summary with all tests passing."""
        with patch('docker.from_env') as mock_docker:
            mock_docker.return_value = Mock()
            
            orchestrator = TestOrchestrator(mock_git_engine)
            
            results = [
                TestResult("test1", TestStatus.PASSED, 100, 0, "out", "err"),
                TestResult("test2", TestStatus.PASSED, 200, 0, "out", "err"),
            ]
            
            summary = orchestrator.get_summary(results)
            
            assert summary["total"] == 2
            assert summary["passed"] == 2
            assert summary["failed"] == 0
            assert summary["timeout"] == 0
            assert summary["error"] == 0
            assert summary["status"] == "green"
    
    def test_get_summary_with_failures(self, mock_git_engine):
        """Test get_summary with mixed results."""
        with patch('docker.from_env') as mock_docker:
            mock_docker.return_value = Mock()
            
            orchestrator = TestOrchestrator(mock_git_engine)
            
            results = [
                TestResult("test1", TestStatus.PASSED, 100, 0, "out", "err"),
                TestResult("test2", TestStatus.FAILED, 200, 1, "out", "err"),
                TestResult("test3", TestStatus.TIMEOUT, 300, -1, "out", "err"),
                TestResult("test4", TestStatus.ERROR, 400, -1, "out", "err", error="Error msg"),
            ]
            
            summary = orchestrator.get_summary(results)
            
            assert summary["total"] == 4
            assert summary["passed"] == 1
            assert summary["failed"] == 1
            assert summary["timeout"] == 1
            assert summary["error"] == 1
            assert summary["status"] == "red"


class TestDataClasses:
    """Test data classes."""
    
    def test_test_config_defaults(self):
        """Test TestConfig with default values."""
        config = TestConfig(name="test1", cmd="echo 'test'")
        
        assert config.name == "test1"
        assert config.cmd == "echo 'test'"
        assert config.timeout == 300
        assert config.depends_on == []
    
    def test_test_config_with_dependencies(self):
        """Test TestConfig with dependencies."""
        config = TestConfig(
            name="test1", 
            cmd="echo 'test'", 
            timeout=60,
            depends_on=["test0"]
        )
        
        assert config.name == "test1"
        assert config.timeout == 60
        assert config.depends_on == ["test0"]
    
    def test_test_result_creation(self):
        """Test TestResult creation."""
        result = TestResult(
            name="test1",
            status=TestStatus.PASSED,
            duration_ms=1500,
            exit_code=0,
            stdout="Test output",
            stderr="",
        )
        
        assert result.name == "test1"
        assert result.status == TestStatus.PASSED
        assert result.duration_ms == 1500
        assert result.exit_code == 0
        assert result.stdout == "Test output"
        assert result.error is None
    
    def test_test_result_with_error(self):
        """Test TestResult with error."""
        result = TestResult(
            name="test1",
            status=TestStatus.ERROR,
            duration_ms=100,
            exit_code=-1,
            stdout="",
            stderr="",
            error="Something went wrong",
        )
        
        assert result.status == TestStatus.ERROR
        assert result.error == "Something went wrong"


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.mark.asyncio
    async def test_empty_test_list(self, mock_git_engine, mock_docker_client):
        """Test running with empty test list."""
        with patch('docker.from_env') as mock_docker:
            mock_docker.return_value = mock_docker_client
            
            orchestrator = TestOrchestrator(mock_git_engine)
            
            results = await orchestrator.run_tests("pad_123", [])
            
            assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_container_cleanup_failure(self, mock_git_engine, mock_docker_client):
        """Test that container cleanup failures don't crash the orchestrator."""
        container = Mock()
        container.id = "abc123"
        container.start = Mock()
        container.wait.return_value = {'StatusCode': 0}
        container.logs.return_value = b"Test output"
        container.remove.side_effect = Exception("Cleanup failed")
        
        mock_docker_client.containers.create.return_value = container
        
        with patch('docker.from_env') as mock_docker:
            mock_docker.return_value = mock_docker_client
            
            orchestrator = TestOrchestrator(mock_git_engine)
            
            test = TestConfig(name="test1", cmd="echo 'test'", timeout=10)
            result = await orchestrator._run_single_test(Path("/tmp/repo"), test)
            
            # Should still return success even if cleanup fails
            assert result.status == TestStatus.PASSED
