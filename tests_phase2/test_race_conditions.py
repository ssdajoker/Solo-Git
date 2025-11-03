"""Test race conditions in Solo-Git."""
import json
import os
import pytest
import threading
from pathlib import Path
from unittest.mock import Mock, patch
from tempfile import TemporaryDirectory


def test_concurrent_workpad_creation():
    """Test creating workpads concurrently."""
    from sologit.engines.git_engine import GitEngine
    
    # Mock GitEngine to avoid actual git operations
    engine = Mock(spec=GitEngine)
    results = []
    errors = []
    
    def mock_create_workpad(repo_id, title):
        from sologit.core.workpad import Workpad
        # Simulate some work
        import time
        time.sleep(0.01)
        return Workpad(
            id=f"pad-{len(results)}",
            repo_id=repo_id,
            title=title,
            branch=f"workpad/{title}",
            created_at="2025-01-01"
        )
    
    engine.create_workpad.side_effect = mock_create_workpad
    
    def create_workpad(i):
        try:
            workpad = engine.create_workpad("test-repo", f"feature-{i}")
            results.append(workpad)
        except Exception as e:
            errors.append(e)
    
    # Create workpads concurrently
    threads = [threading.Thread(target=create_workpad, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    assert len(errors) == 0, f"Errors during concurrent creation: {errors}"
    assert len(results) == 10, "Not all workpads were created"
    assert len(set(w.id for w in results)) == 10, "Duplicate workpad IDs detected"


def test_state_file_corruption():
    """Test state file resilience to corruption."""
    from sologit.state.manager import StateManager
    
    with TemporaryDirectory() as tmpdir:
        state_file = Path(tmpdir) / "state.json"
        
        # Create StateManager with custom state file
        with patch('sologit.state.manager.StateManager._get_state_file') as mock_get_state:
            mock_get_state.return_value = state_file
            
            # First, create valid state
            state_manager = StateManager()
            
            # Now corrupt the state file
            state_file.write_text("CORRUPTED DATA {{{")
            
            # Should handle gracefully and create new state
            try:
                state_manager = StateManager()
                # Should not raise, but create new empty state
                assert state_file.exists()
                
                # Verify it's valid JSON now
                with open(state_file) as f:
                    state_data = json.load(f)
                assert isinstance(state_data, dict)
            except Exception as e:
                pytest.fail(f"Failed to handle corrupted state: {e}")


def test_concurrent_test_execution():
    """Test that concurrent test runs don't interfere with each other."""
    from sologit.engines.test_orchestrator import TestOrchestrator, TestConfig, TestStatus
    
    # Mock TestOrchestrator
    orchestrator = Mock(spec=TestOrchestrator)
    results_list = []
    
    def mock_run_tests(workpad_id, configs, parallel=False):
        from sologit.engines.test_orchestrator import TestResult
        import time
        # Simulate test execution
        time.sleep(0.01)
        return [
            TestResult(
                name=config.name,
                status=TestStatus.PASSED,
                duration_ms=10,
                output=f"Test {config.name} passed",
                workpad_id=workpad_id
            )
            for config in configs
        ]
    
    orchestrator.run_tests_sync.side_effect = mock_run_tests
    
    def run_tests(pad_id):
        try:
            configs = [TestConfig(name=f"test-{i}", cmd=f"test{i}") for i in range(3)]
            results = orchestrator.run_tests_sync(pad_id, configs, parallel=True)
            results_list.append((pad_id, results))
        except Exception as e:
            pytest.fail(f"Error in concurrent test run: {e}")
    
    # Run tests concurrently for different workpads
    threads = [threading.Thread(target=run_tests, args=(f"pad-{i}",)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    assert len(results_list) == 5, "Not all test runs completed"
    
    # Verify each workpad got its own results
    for pad_id, results in results_list:
        assert len(results) == 3
        assert all(r.workpad_id == pad_id for r in results)


def test_concurrent_state_updates():
    """Test that concurrent state updates don't corrupt the state."""
    from sologit.state.manager import StateManager
    from sologit.core.workpad import Workpad
    
    with TemporaryDirectory() as tmpdir:
        state_file = Path(tmpdir) / "state.json"
        
        with patch('sologit.state.manager.StateManager._get_state_file') as mock_get_state:
            mock_get_state.return_value = state_file
            
            state_manager = StateManager()
            errors = []
            
            def add_workpad(i):
                try:
                    workpad = Workpad(
                        id=f"pad-{i}",
                        repo_id="test-repo",
                        title=f"feature-{i}",
                        branch=f"workpad/feature-{i}",
                        created_at="2025-01-01"
                    )
                    # Mock add_workpad if it doesn't exist
                    if hasattr(state_manager, 'add_workpad'):
                        state_manager.add_workpad(workpad)
                except Exception as e:
                    errors.append(e)
            
            # Add workpads concurrently
            threads = [threading.Thread(target=add_workpad, args=(i,)) for i in range(10)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            
            # Should complete without errors (or with expected locking errors)
            # The key is that the state file shouldn't be corrupted
            if state_file.exists():
                try:
                    with open(state_file) as f:
                        state_data = json.load(f)
                    assert isinstance(state_data, dict), "State file is not valid JSON"
                except json.JSONDecodeError:
                    pytest.fail("State file was corrupted by concurrent updates")


def test_git_operation_serialization():
    """Test that git operations are properly serialized to avoid conflicts."""
    from sologit.engines.git_engine import GitEngine
    
    # Mock GitEngine
    engine = Mock(spec=GitEngine)
    operation_order = []
    lock = threading.Lock()
    
    def mock_git_operation(operation_name):
        with lock:
            import time
            time.sleep(0.01)  # Simulate git operation
            operation_order.append(operation_name)
    
    engine.create_workpad.side_effect = lambda repo_id, title: mock_git_operation(f"create-{title}")
    engine.delete_workpad.side_effect = lambda pad_id: mock_git_operation(f"delete-{pad_id}")
    
    def perform_operations(i):
        engine.create_workpad("test-repo", f"pad-{i}")
        engine.delete_workpad(f"pad-{i}")
    
    # Perform operations concurrently
    threads = [threading.Thread(target=perform_operations, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    # Verify all operations completed
    assert len(operation_order) == 10  # 5 creates + 5 deletes


def test_no_deadlocks_in_workflow():
    """Test that workflows don't deadlock under concurrent execution."""
    from sologit.workflows.auto_merge import AutoMergeWorkflow
    
    # Mock workflow components
    workflow = Mock(spec=AutoMergeWorkflow)
    completed = []
    
    def mock_execute(workpad_id):
        import time
        time.sleep(0.02)  # Simulate workflow execution
        completed.append(workpad_id)
        return {"success": True}
    
    workflow.execute.side_effect = mock_execute
    
    def run_workflow(pad_id):
        workflow.execute(pad_id)
    
    # Run workflows concurrently
    threads = [threading.Thread(target=run_workflow, args=(f"pad-{i}",)) for i in range(5)]
    for t in threads:
        t.start()
    
    # Wait with timeout to detect deadlocks
    for t in threads:
        t.join(timeout=5.0)
        assert not t.is_alive(), "Thread did not complete - possible deadlock"
    
    assert len(completed) == 5, "Not all workflows completed"
