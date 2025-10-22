
"""State Manager for Solo Git Heaven Interface.

The manager exposes a pluggable :class:`StateBackend` abstraction that now uses
Python's ``abc`` module to define a consistent contract for all persistence
implementations. The default JSON backend remains the on-disk implementation,
while planned future backends include SQLite for richer local state management
and a REST service for distributed deployments.
"""

import json
import threading
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sologit.state.schema import (
    CommitNode,
    TestRun,
    AIOperation,
    PromotionRecord,
    WorkpadState,
    RepositoryState,
    GlobalState,
    StateEvent,
    EventType,
)
from sologit.utils.logger import get_logger

# Import for type annotation - avoid circular import at runtime
if TYPE_CHECKING:
    from sologit.workflows.promotion_gate import PromotionDecision

logger = get_logger(__name__)


class StateBackend(ABC):
    """Abstract base class for state backends."""

    @abstractmethod
    def read_global_state(self) -> GlobalState:
        """Read the global state from the backend."""
        ...

    @abstractmethod
    def write_global_state(self, state: GlobalState) -> None:
        """Persist the provided global state."""
        ...

    @abstractmethod
    def read_repository(self, repo_id: str) -> Optional[RepositoryState]:
        """Return the repository state for the given repository identifier."""
        ...

    @abstractmethod
    def write_repository(self, state: RepositoryState) -> None:
        """Persist the provided repository state."""
        ...

    @abstractmethod
    def list_repositories(self) -> List[RepositoryState]:
        """List repository states known to the backend."""
        ...

    @abstractmethod
    def delete_repository(self, repo_id: str) -> None:
        """Remove repository state."""
        ...

    @abstractmethod
    def read_workpad(self, workpad_id: str) -> Optional[WorkpadState]:
        """Return the workpad state for the provided identifier."""
        ...

    @abstractmethod
    def write_workpad(self, state: WorkpadState) -> None:
        """Persist the provided workpad state."""
        ...

    @abstractmethod
    def list_workpads(self, repo_id: Optional[str] = None) -> List[WorkpadState]:
        """List workpad states, optionally filtered by repository identifier."""
        ...

    @abstractmethod
    def delete_workpad(self, workpad_id: str) -> None:
        """Remove workpad state."""
        ...

    @abstractmethod
    def read_test_run(self, run_id: str) -> Optional[TestRun]:
        """Return the recorded test run for the provided identifier."""
        ...

    @abstractmethod
    def write_test_run(self, test_run: TestRun) -> None:
        """Persist the provided test run."""
        ...

    @abstractmethod
    def list_test_runs(self, workpad_id: Optional[str] = None) -> List[TestRun]:
        """List test runs, optionally filtered by workpad identifier."""
        ...

    @abstractmethod
    def delete_test_run(self, run_id: str) -> None:
        """Remove a test run record."""
        ...

    @abstractmethod
    def read_ai_operation(self, operation_id: str) -> Optional[AIOperation]:
        """Return the AI operation for the provided identifier."""
        ...

    @abstractmethod
    def write_ai_operation(self, operation: AIOperation) -> None:
        """Persist the provided AI operation."""
        ...

    @abstractmethod
    def list_ai_operations(self, workpad_id: Optional[str] = None) -> List[AIOperation]:
        """List AI operations, optionally filtered by workpad identifier."""
        ...

    @abstractmethod
    def delete_ai_operation(self, operation_id: str) -> None:
        """Remove AI operation."""
        ...

    @abstractmethod
    def write_promotion_record(self, record: PromotionRecord) -> None:
        """Persist a promotion record."""
        ...

    @abstractmethod
    def list_promotion_records(
        self,
        repo_id: Optional[str] = None,
        workpad_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[PromotionRecord]:
        """List promotion records filtered by repository or workpad."""
        ...

    @abstractmethod
    def delete_promotion_record(self, record_id: str) -> None:
        """Remove a promotion record."""
        ...

    @abstractmethod
    def read_commits(self, repo_id: str, limit: int = 100) -> List[CommitNode]:
        """Return commit nodes for the specified repository."""
        ...

    @abstractmethod
    def write_commit(self, repo_id: str, commit: CommitNode) -> None:
        """Persist a commit for the specified repository."""
        ...

    @abstractmethod
    def write_event(self, event: StateEvent) -> None:
        """Persist a state event."""
        ...

    @abstractmethod
    def read_events(self, since: Optional[str] = None, limit: int = 100) -> List[StateEvent]:
        """List recent state events."""
        ...


class JSONStateBackend(StateBackend):
    """JSON file-based state backend."""

    def __init__(self, state_dir: Path) -> None:
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        self.repos_dir = self.state_dir / "repositories"
        self.workpads_dir = self.state_dir / "workpads"
        self.tests_dir = self.state_dir / "test_runs"
        self.ai_ops_dir = self.state_dir / "ai_operations"
        self.commits_dir = self.state_dir / "commits"
        self.events_dir = self.state_dir / "events"
        self.promotions_dir = self.state_dir / "promotions"

        for d in [self.repos_dir, self.workpads_dir, self.tests_dir,
                  self.ai_ops_dir, self.commits_dir, self.events_dir,
                  self.promotions_dir]:
            d.mkdir(exist_ok=True)
        
        self._lock = threading.Lock()
    
    def _read_json(self, path: Path, default: Any = None) -> Any:
        """Read JSON file with error handling."""
        try:
            if path.exists():
                with open(path, 'r') as f:
                    return json.load(f)
            return default
        except Exception as e:
            logger.error(f"Failed to read {path}: {e}")
            return default
    
    def _write_json(self, path: Path, data: Any) -> None:
        """Write JSON file with error handling."""
        try:
            with self._lock:
                # Write to temp file first, then rename (atomic)
                temp_path = path.with_suffix('.tmp')
                with open(temp_path, 'w') as f:
                    json.dump(data, f, indent=2)
                temp_path.replace(path)
        except Exception as e:
            logger.error(f"Failed to write {path}: {e}")
            raise
    
    def read_global_state(self) -> GlobalState:
        path = self.state_dir / "global.json"
        data = self._read_json(path, {})
        if data:
            return GlobalState.from_dict(data)
        return GlobalState()
    
    def write_global_state(self, state: GlobalState) -> None:
        state.last_updated = datetime.utcnow().isoformat()
        path = self.state_dir / "global.json"
        self._write_json(path, state.to_dict())
    
    def read_repository(self, repo_id: str) -> Optional[RepositoryState]:
        path = self.repos_dir / f"{repo_id}.json"
        data = self._read_json(path)
        return RepositoryState.from_dict(data) if data else None
    
    def write_repository(self, state: RepositoryState) -> None:
        state.updated_at = datetime.utcnow().isoformat()
        path = self.repos_dir / f"{state.repo_id}.json"
        self._write_json(path, state.to_dict())
    
    def list_repositories(self) -> List[RepositoryState]:
        repos = []
        for path in self.repos_dir.glob("*.json"):
            data = self._read_json(path)
            if data:
                repos.append(RepositoryState.from_dict(data))
        return sorted(repos, key=lambda r: r.created_at, reverse=True)

    def delete_repository(self, repo_id: str) -> None:
        path = self.repos_dir / f"{repo_id}.json"
        if path.exists():
            try:
                path.unlink()
            except Exception as exc:
                logger.error(f"Failed to delete repository {repo_id}: {exc}")
    def read_workpad(self, workpad_id: str) -> Optional[WorkpadState]:
        path = self.workpads_dir / f"{workpad_id}.json"
        data = self._read_json(path)
        return WorkpadState.from_dict(data) if data else None
    
    def write_workpad(self, state: WorkpadState) -> None:
        state.updated_at = datetime.utcnow().isoformat()
        path = self.workpads_dir / f"{state.workpad_id}.json"
        self._write_json(path, state.to_dict())
    
    def list_workpads(self, repo_id: Optional[str] = None) -> List[WorkpadState]:
        workpads = []
        for path in self.workpads_dir.glob("*.json"):
            data = self._read_json(path)
            if data:
                workpad = WorkpadState.from_dict(data)
                if repo_id is None or workpad.repo_id == repo_id:
                    workpads.append(workpad)
        return sorted(workpads, key=lambda w: w.created_at, reverse=True)

    def delete_workpad(self, workpad_id: str) -> None:
        path = self.workpads_dir / f"{workpad_id}.json"
        if path.exists():
            try:
                path.unlink()
            except Exception as exc:
                logger.error(f"Failed to delete workpad {workpad_id}: {exc}")
    def read_test_run(self, run_id: str) -> Optional[TestRun]:
        path = self.tests_dir / f"{run_id}.json"
        data = self._read_json(path)
        return TestRun.from_dict(data) if data else None
    
    def write_test_run(self, test_run: TestRun) -> None:
        path = self.tests_dir / f"{test_run.run_id}.json"
        self._write_json(path, test_run.to_dict())
    
    def list_test_runs(self, workpad_id: Optional[str] = None) -> List[TestRun]:
        test_runs = []
        for path in self.tests_dir.glob("*.json"):
            data = self._read_json(path)
            if data:
                test_run = TestRun.from_dict(data)
                if workpad_id is None or test_run.workpad_id == workpad_id:
                    test_runs.append(test_run)
        return sorted(test_runs, key=lambda t: t.started_at, reverse=True)

    def delete_test_run(self, run_id: str) -> None:
        path = self.tests_dir / f"{run_id}.json"
        if path.exists():
            try:
                path.unlink()
            except Exception as exc:
                logger.error(f"Failed to delete test run {run_id}: {exc}")
    
    def read_ai_operation(self, operation_id: str) -> Optional[AIOperation]:
        path = self.ai_ops_dir / f"{operation_id}.json"
        data = self._read_json(path)
        return AIOperation.from_dict(data) if data else None
    
    def write_ai_operation(self, operation: AIOperation) -> None:
        path = self.ai_ops_dir / f"{operation.operation_id}.json"
        self._write_json(path, operation.to_dict())
    
    def list_ai_operations(self, workpad_id: Optional[str] = None) -> List[AIOperation]:
        operations = []
        for path in self.ai_ops_dir.glob("*.json"):
            data = self._read_json(path)
            if data:
                operation = AIOperation.from_dict(data)
                if workpad_id is None or operation.workpad_id == workpad_id:
                    operations.append(operation)
        return sorted(operations, key=lambda o: o.started_at, reverse=True)

    def delete_ai_operation(self, operation_id: str) -> None:
        path = self.ai_ops_dir / f"{operation_id}.json"
        if path.exists():
            try:
                path.unlink()
            except Exception as exc:
                logger.error(f"Failed to delete AI operation {operation_id}: {exc}")

    def write_promotion_record(self, record: PromotionRecord) -> None:
        path = self.promotions_dir / f"{record.record_id}.json"
        self._write_json(path, record.to_dict())

    def list_promotion_records(
        self,
        repo_id: Optional[str] = None,
        workpad_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[PromotionRecord]:
        records: List[PromotionRecord] = []
        for path in sorted(self.promotions_dir.glob("*.json"), reverse=True):
            data = self._read_json(path)
            if data:
                record = PromotionRecord.from_dict(data)
                if (
                    (repo_id is None or record.repo_id == repo_id)
                    and (workpad_id is None or record.workpad_id == workpad_id)
                ):
                    records.append(record)
                if len(records) >= limit:
                    break
        return records

    def delete_promotion_record(self, record_id: str) -> None:
        path = self.promotions_dir / f"{record_id}.json"
        if path.exists():
            try:
                path.unlink()
            except Exception as exc:
                logger.error(f"Failed to delete promotion record {record_id}: {exc}")

    def read_commits(self, repo_id: str, limit: int = 100) -> List[CommitNode]:
        path = self.commits_dir / f"{repo_id}.json"
        data = self._read_json(path, {"commits": []})
        commits = [CommitNode.from_dict(c) for c in data.get("commits", [])]
        return commits[:limit]
    
    def write_commit(self, repo_id: str, commit: CommitNode) -> None:
        path = self.commits_dir / f"{repo_id}.json"
        data = self._read_json(path, {"commits": []})
        
        # Prepend new commit (most recent first)
        commits = [commit.to_dict()] + data.get("commits", [])
        
        # Keep only last 1000 commits
        commits = commits[:1000]
        
        self._write_json(path, {"commits": commits, "repo_id": repo_id})
    
    def write_event(self, event: StateEvent) -> None:
        # Append to daily event log
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        path = self.events_dir / f"events-{date_str}.json"
        
        data = self._read_json(path, {"events": []})
        data["events"].append(event.to_dict())
        
        # Keep only last 10000 events per day
        data["events"] = data["events"][-10000:]
        
        self._write_json(path, data)
    
    def read_events(self, since: Optional[str] = None, limit: int = 100) -> List[StateEvent]:
        events = []
        
        # Read today's events
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        path = self.events_dir / f"events-{date_str}.json"
        data = self._read_json(path, {"events": []})
        
        for event_data in reversed(data.get("events", [])):
            event = StateEvent.from_dict(event_data)
            if since is None or event.timestamp > since:
                events.append(event)
                if len(events) >= limit:
                    break
        
        return events


class StateManager:
    """
    High-level state manager with caching and event emission.
    
    This is the main interface for interacting with Solo Git state.
    It provides an abstraction layer that can be backed by JSON files,
    SQLite, or a REST API in the future.
    """
    
    def __init__(self, backend: Optional[StateBackend] = None, state_dir: Optional[Path] = None) -> None:
        if backend is None:
            if state_dir is None:
                state_dir = Path.home() / ".sologit" / "state"
            backend = JSONStateBackend(state_dir)
        
        self.backend = backend
        self._cache: Dict[str, Any] = {}
        self._cache_timeout = 5  # seconds
    
    # Global State
    
    def get_global_state(self) -> GlobalState:
        """Get current global state."""
        return self.backend.read_global_state()
    
    def update_global_state(self, **kwargs: Any) -> GlobalState:
        """Update global state fields."""
        state = self.get_global_state()
        for key, value in kwargs.items():
            if hasattr(state, key):
                setattr(state, key, value)
        self.backend.write_global_state(state)
        return state
    
    # Repositories
    
    def create_repository(self, repo_id: str, name: str, path: str) -> RepositoryState:
        """Create a new repository state."""
        state = RepositoryState(
            repo_id=repo_id,
            name=name,
            path=path
        )
        self.backend.write_repository(state)
        self._emit_event(EventType.REPO_CREATED, {"repo_id": repo_id})
        return state
    
    def get_repository(self, repo_id: str) -> Optional[RepositoryState]:
        """Get repository state by ID."""
        return self.backend.read_repository(repo_id)
    
    def update_repository(self, repo_id: str, **kwargs: Any) -> Optional[RepositoryState]:
        """Update repository state fields."""
        state = self.get_repository(repo_id)
        if state:
            for key, value in kwargs.items():
                if hasattr(state, key):
                    setattr(state, key, value)
            self.backend.write_repository(state)
            self._emit_event(EventType.REPO_UPDATED, {"repo_id": repo_id})
        return state
    
    def list_repositories(self) -> List[RepositoryState]:
        """List all repositories."""
        return self.backend.list_repositories()

    def delete_repository(self, repo_id: str) -> None:
        """Delete repository state and related records."""

        repo = self.get_repository(repo_id)
        if not repo:
            return

        # Remove associated workpads and promotions
        for workpad in self.list_workpads(repo_id):
            self.delete_workpad(workpad.workpad_id)

        for record in self.list_promotion_records(repo_id=repo_id):
            self.backend.delete_promotion_record(record.record_id)

        self.backend.delete_repository(repo_id)

    # Workpads

    def create_workpad(self, workpad_id: str, repo_id: str, title: str,
                       branch_name: str, base_commit: str) -> WorkpadState:
        """Create a new workpad state."""
        state = WorkpadState(
            workpad_id=workpad_id,
            repo_id=repo_id,
            title=title,
            status="active",
            branch_name=branch_name,
            base_commit=base_commit
        )
        self.backend.write_workpad(state)
        
        # Update repository
        repo = self.get_repository(repo_id)
        if repo:
            repo.workpads.append(workpad_id)
            self.backend.write_repository(repo)
        
        self._emit_event(EventType.WORKPAD_CREATED, {"workpad_id": workpad_id, "repo_id": repo_id})
        return state
    
    def get_workpad(self, workpad_id: str) -> Optional[WorkpadState]:
        """Get workpad state by ID."""
        return self.backend.read_workpad(workpad_id)
    
    def update_workpad(self, workpad_id: str, **kwargs: Any) -> Optional[WorkpadState]:
        """Update workpad state fields."""
        state = self.get_workpad(workpad_id)
        if state:
            for key, value in kwargs.items():
                if hasattr(state, key):
                    setattr(state, key, value)
            self.backend.write_workpad(state)
            self._emit_event(EventType.WORKPAD_UPDATED, {"workpad_id": workpad_id})
        return state
    
    def list_workpads(self, repo_id: Optional[str] = None) -> List[WorkpadState]:
        """List workpads, optionally filtered by repository."""
        return self.backend.list_workpads(repo_id)

    def delete_workpad(self, workpad_id: str) -> None:
        """Delete workpad state and related records."""

        workpad = self.get_workpad(workpad_id)
        if not workpad:
            return

        for test_run in self.list_test_runs(workpad_id):
            self.backend.delete_test_run(test_run.run_id)

        for operation in self.list_ai_operations(workpad_id):
            self.backend.delete_ai_operation(operation.operation_id)

        for record in self.list_promotion_records(workpad_id=workpad_id):
            self.backend.delete_promotion_record(record.record_id)

        self.backend.delete_workpad(workpad_id)

        repo = self.get_repository(workpad.repo_id)
        if repo and workpad_id in repo.workpads:
            repo.workpads.remove(workpad_id)
            self.backend.write_repository(repo)
    # Test Runs
    
    def create_test_run(self, workpad_id: Optional[str], target: str) -> TestRun:
        """Create a new test run."""
        run = TestRun(
            run_id=str(uuid.uuid4()),
            workpad_id=workpad_id,
            target=target,
            status="pending",
            started_at=datetime.utcnow().isoformat()
        )
        self.backend.write_test_run(run)
        
        # Update workpad
        if workpad_id:
            workpad = self.get_workpad(workpad_id)
            if workpad:
                workpad.test_runs.append(run.run_id)
                self.backend.write_workpad(workpad)
        
        self._emit_event(EventType.TEST_STARTED, {"run_id": run.run_id, "workpad_id": workpad_id})
        return run
    
    def update_test_run(self, run_id: str, **kwargs: Any) -> Optional[TestRun]:
        """Update test run fields."""
        test_run = self.backend.read_test_run(run_id)
        if test_run:
            for key, value in kwargs.items():
                if hasattr(test_run, key):
                    setattr(test_run, key, value)
            self.backend.write_test_run(test_run)
            
            if kwargs.get('status') in ['passed', 'failed']:
                self._emit_event(EventType.TEST_COMPLETED, {
                    "run_id": run_id,
                    "status": kwargs['status'],
                    "workpad_id": test_run.workpad_id
                })
        return test_run
    
    def get_test_run(self, run_id: str) -> Optional[TestRun]:
        """Get test run by ID."""
        return self.backend.read_test_run(run_id)
    
    def list_test_runs(self, workpad_id: Optional[str] = None) -> List[TestRun]:
        """List test runs, optionally filtered by workpad."""
        return self.backend.list_test_runs(workpad_id)
    
    # AI Operations
    
    def create_ai_operation(self, workpad_id: Optional[str], operation_type: str,
                           model: str, prompt: str) -> AIOperation:
        """Create a new AI operation."""
        operation = AIOperation(
            operation_id=str(uuid.uuid4()),
            workpad_id=workpad_id,
            operation_type=operation_type,
            status="pending",
            model=model,
            prompt=prompt
        )
        self.backend.write_ai_operation(operation)
        
        # Update workpad
        if workpad_id:
            workpad = self.get_workpad(workpad_id)
            if workpad:
                workpad.ai_operations.append(operation.operation_id)
                self.backend.write_workpad(workpad)
        
        self._emit_event(EventType.AI_OPERATION_STARTED, {
            "operation_id": operation.operation_id,
            "workpad_id": workpad_id,
            "type": operation_type
        })
        return operation
    
    def update_ai_operation(self, operation_id: str, **kwargs: Any) -> Optional[AIOperation]:
        """Update AI operation fields."""
        operation = self.backend.read_ai_operation(operation_id)
        if operation:
            for key, value in kwargs.items():
                if hasattr(operation, key):
                    setattr(operation, key, value)
            self.backend.write_ai_operation(operation)
            
            if kwargs.get('status') in ['completed', 'failed']:
                self._emit_event(EventType.AI_OPERATION_COMPLETED, {
                    "operation_id": operation_id,
                    "status": kwargs['status'],
                    "workpad_id": operation.workpad_id
                })
        return operation
    
    def get_ai_operation(self, operation_id: str) -> Optional[AIOperation]:
        """Get AI operation by ID."""
        return self.backend.read_ai_operation(operation_id)
    
    def list_ai_operations(self, workpad_id: Optional[str] = None) -> List[AIOperation]:
        """List AI operations, optionally filtered by workpad."""
        return self.backend.list_ai_operations(workpad_id)

    # Promotion records

    def record_promotion_decision(
        self,
        repo_id: str,
        workpad_id: str,
        decision: "PromotionDecision",
        auto_promote_requested: bool,
        promoted: bool,
        commit_hash: Optional[str],
        message: str,
        test_run_id: Optional[str] = None,
        ci_status: Optional[str] = None,
        ci_message: Optional[str] = None,
    ) -> PromotionRecord:
        """Record a promotion decision for history tracking."""
        record = PromotionRecord(
            record_id=str(uuid.uuid4()),
            repo_id=repo_id,
            workpad_id=workpad_id,
            decision=decision.decision.value,
            can_promote=decision.can_promote,
            auto_promote_requested=auto_promote_requested,
            promoted=promoted,
            commit_hash=commit_hash,
            message=message,
            test_run_id=test_run_id,
            ci_status=ci_status,
            ci_message=ci_message,
        )

        self.backend.write_promotion_record(record)
        self._emit_event(
            EventType.PROMOTION_RECORDED,
            {
                "repo_id": repo_id,
                "workpad_id": workpad_id,
                "decision": record.decision,
                "promoted": promoted,
                "commit_hash": commit_hash,
            },
        )

        return record

    def list_promotion_records(
        self,
        repo_id: Optional[str] = None,
        workpad_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[PromotionRecord]:
        """List recorded promotion decisions."""
        return self.backend.list_promotion_records(repo_id=repo_id, workpad_id=workpad_id, limit=limit)

    # Commits

    def add_commit(self, repo_id: str, commit: CommitNode) -> None:
        """Add a commit to the graph."""
        self.backend.write_commit(repo_id, commit)
        self._emit_event(EventType.COMMIT_CREATED, {
            "repo_id": repo_id,
            "sha": commit.sha,
            "message": commit.message
        })
    
    def get_commits(self, repo_id: str, limit: int = 100) -> List[CommitNode]:
        """Get commit history for a repository."""
        return self.backend.read_commits(repo_id, limit)
    
    # Events
    
    def _emit_event(self, event_type: EventType, data: Dict[str, Any]) -> None:
        """Emit a state event."""
        event = StateEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type.value,
            timestamp=datetime.utcnow().isoformat(),
            data=data
        )
        self.backend.write_event(event)
    
    def get_events(self, since: Optional[str] = None, limit: int = 100) -> List[StateEvent]:
        """Get recent events."""
        return self.backend.read_events(since, limit)
    
    # Utility methods
    
    def get_active_context(self) -> Dict[str, Optional[str]]:
        """Get the active repository and workpad."""
        global_state = self.get_global_state()
        return {
            "repo_id": global_state.active_repo,
            "workpad_id": global_state.active_workpad
        }
    
    def set_active_context(self, repo_id: Optional[str] = None, 
                          workpad_id: Optional[str] = None) -> None:
        """Set the active repository and/or workpad."""
        self.update_global_state(
            active_repo=repo_id if repo_id is not None else self.get_global_state().active_repo,
            active_workpad=workpad_id if workpad_id is not None else self.get_global_state().active_workpad
        )
