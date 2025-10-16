
"""
Test Orchestrator for Solo Git.

Manages test execution in Docker sandboxes with parallel execution,
timeout enforcement, and result collection.
"""

import asyncio
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
from enum import Enum

import docker
from docker.errors import DockerException

from sologit.engines.git_engine import GitEngine, WorkpadNotFoundError
from sologit.utils.logger import get_logger

logger = get_logger(__name__)


class TestStatus(Enum):
    """Test execution status."""
    PASSED = "passed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class TestConfig:
    """Test configuration."""
    name: str
    cmd: str
    timeout: int = 300
    depends_on: List[str] = None
    
    def __post_init__(self):
        if self.depends_on is None:
            self.depends_on = []


@dataclass
class TestResult:
    """Test execution result."""
    name: str
    status: TestStatus
    duration_ms: int
    exit_code: int
    stdout: str
    stderr: str
    error: Optional[str] = None


class TestOrchestratorError(Exception):
    """Base exception for Test Orchestrator errors."""
    pass


class TestOrchestrator:
    """
    Test execution orchestrator.
    
    Runs tests in isolated Docker containers with timeout enforcement.
    """
    
    def __init__(
        self, 
        git_engine: GitEngine,
        sandbox_image: str = "python:3.11-slim"
    ):
        """
        Initialize Test Orchestrator.
        
        Args:
            git_engine: GitEngine instance
            sandbox_image: Docker image for test sandbox
        """
        self.git_engine = git_engine
        self.sandbox_image = sandbox_image
        
        try:
            self.docker_client = docker.from_env()
            logger.info(f"TestOrchestrator initialized with image={sandbox_image}")
        except DockerException as e:
            logger.error(f"Failed to connect to Docker: {e}")
            raise TestOrchestratorError(f"Docker not available: {e}")
    
    async def run_tests(
        self,
        pad_id: str,
        tests: List[TestConfig],
        parallel: bool = True
    ) -> List[TestResult]:
        """
        Run tests with optional parallelization.
        
        Args:
            pad_id: Workpad ID
            tests: List of test configurations
            parallel: Whether to run tests in parallel
            
        Returns:
            List of test results
        """
        logger.info(f"Running {len(tests)} test(s) for pad {pad_id} (parallel={parallel})")
        
        # Get workpad
        workpad = self.git_engine.get_workpad(pad_id)
        if not workpad:
            raise WorkpadNotFoundError(f"Workpad {pad_id} not found")
        
        repository = self.git_engine.get_repo(workpad.repo_id)
        
        if parallel:
            results = await self._run_parallel(repository.path, tests)
        else:
            results = await self._run_sequential(repository.path, tests)
        
        # Log summary
        passed = sum(1 for r in results if r.status == TestStatus.PASSED)
        failed = len(results) - passed
        logger.info(f"Tests complete: {passed} passed, {failed} failed")
        
        return results
    
    def run_tests_sync(
        self,
        pad_id: str,
        tests: List[TestConfig],
        parallel: bool = True
    ) -> List[TestResult]:
        """
        Synchronous wrapper for run_tests.
        
        Args:
            pad_id: Workpad ID
            tests: List of test configurations
            parallel: Whether to run tests in parallel
            
        Returns:
            List of test results
        """
        return asyncio.run(self.run_tests(pad_id, tests, parallel))
    
    async def _run_sequential(
        self,
        repo_path: Path,
        tests: List[TestConfig]
    ) -> List[TestResult]:
        """Run tests sequentially."""
        results = []
        
        for test in tests:
            logger.debug(f"Running test: {test.name}")
            result = await self._run_single_test(repo_path, test)
            results.append(result)
            
            # Early exit on failure
            if result.status != TestStatus.PASSED:
                logger.info(f"Test failed, stopping sequential execution: {test.name}")
                break
        
        return results
    
    async def _run_parallel(
        self,
        repo_path: Path,
        tests: List[TestConfig]
    ) -> List[TestResult]:
        """Run tests in parallel respecting dependencies."""
        # Build dependency graph
        graph = self._build_dependency_graph(tests)
        
        # Execute with dependency resolution
        results = []
        completed = set()
        running = {}
        
        while len(completed) < len(tests):
            # Find ready tests (dependencies satisfied)
            ready = [
                test for test in tests
                if test.name not in completed 
                and test.name not in running
                and all(dep in completed for dep in test.depends_on)
            ]
            
            if not ready and not running:
                # Deadlock or circular dependency
                logger.error("Dependency deadlock detected")
                break
            
            # Start ready tests
            for test in ready:
                logger.debug(f"Starting test: {test.name}")
                task = asyncio.create_task(self._run_single_test(repo_path, test))
                running[test.name] = task
            
            # Wait for any test to complete
            if running:
                done, pending = await asyncio.wait(
                    running.values(),
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                for task in done:
                    result = task.result()
                    results.append(result)
                    completed.add(result.name)
                    
                    # Remove from running
                    for name, t in list(running.items()):
                        if t == task:
                            del running[name]
                            break
        
        # Sort results by original test order
        test_order = {t.name: i for i, t in enumerate(tests)}
        results.sort(key=lambda r: test_order.get(r.name, 999))
        
        return results
    
    async def _run_single_test(
        self,
        repo_path: Path,
        test: TestConfig
    ) -> TestResult:
        """
        Run a single test in Docker container.
        
        Args:
            repo_path: Repository path on host
            test: Test configuration
            
        Returns:
            Test result
        """
        start_time = time.time()
        
        try:
            # Create container
            container = self.docker_client.containers.create(
                self.sandbox_image,
                command=["/bin/sh", "-c", test.cmd],
                working_dir="/workspace",
                volumes={
                    str(repo_path): {'bind': '/workspace', 'mode': 'ro'}
                },
                network_mode="none",  # Isolated
                mem_limit="2g",
                cpu_quota=100000,  # 1 CPU
                detach=True,
                remove=False  # We'll remove manually
            )
            
            logger.debug(f"Created container for test {test.name}: {container.id[:12]}")
            
            # Start container
            container.start()
            
            # Wait with timeout
            try:
                result = container.wait(timeout=test.timeout)
                exit_code = result.get('StatusCode', -1)
                
                # Get logs
                logs = container.logs(stdout=True, stderr=True).decode('utf-8', errors='replace')
                
                # Determine status
                status = TestStatus.PASSED if exit_code == 0 else TestStatus.FAILED
                
            except Exception as e:
                logger.warning(f"Test timeout: {test.name}")
                container.stop(timeout=5)
                exit_code = -1
                logs = f"Test timed out after {test.timeout}s"
                status = TestStatus.TIMEOUT
            
            finally:
                # Clean up container
                try:
                    container.remove(force=True)
                except:
                    pass
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            return TestResult(
                name=test.name,
                status=status,
                duration_ms=duration_ms,
                exit_code=exit_code,
                stdout=logs,
                stderr="",
            )
            
        except Exception as e:
            logger.error(f"Error running test {test.name}: {e}")
            duration_ms = int((time.time() - start_time) * 1000)
            
            return TestResult(
                name=test.name,
                status=TestStatus.ERROR,
                duration_ms=duration_ms,
                exit_code=-1,
                stdout="",
                stderr="",
                error=str(e),
            )
    
    def _build_dependency_graph(
        self,
        tests: List[TestConfig]
    ) -> Dict[str, List[str]]:
        """
        Build dependency graph from test configurations.
        
        Args:
            tests: List of test configurations
            
        Returns:
            Dependency graph as adjacency list
        """
        graph = {}
        for test in tests:
            graph[test.name] = test.depends_on
        return graph
    
    def all_tests_passed(self, results: List[TestResult]) -> bool:
        """Check if all tests passed."""
        return all(r.status == TestStatus.PASSED for r in results)
    
    def get_summary(self, results: List[TestResult]) -> dict:
        """Get test results summary."""
        return {
            "total": len(results),
            "passed": sum(1 for r in results if r.status == TestStatus.PASSED),
            "failed": sum(1 for r in results if r.status == TestStatus.FAILED),
            "timeout": sum(1 for r in results if r.status == TestStatus.TIMEOUT),
            "error": sum(1 for r in results if r.status == TestStatus.ERROR),
            "status": "green" if self.all_tests_passed(results) else "red",
        }
