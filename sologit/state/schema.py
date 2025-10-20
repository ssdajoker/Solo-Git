
"""
State schema definitions for Solo Git Heaven Interface.

Defines the data structures for the shared state layer that connects
the CLI/TUI with the GUI companion app.
"""

from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Any
import json


class WorkpadStatus(Enum):
    """Status of a workpad."""
    ACTIVE = "active"
    TESTING = "testing"
    PASSED = "passed"
    FAILED = "failed"
    PROMOTED = "promoted"
    DELETED = "deleted"


class TestStatus(Enum):
    """Status of a test run."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class AIOperationStatus(Enum):
    """Status of an AI operation."""
    PENDING = "pending"
    PLANNING = "planning"
    CODING = "coding"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class CommitNode:
    """Represents a commit in the graph."""
    sha: str
    short_sha: str
    message: str
    author: str
    timestamp: str  # ISO format
    parent_sha: Optional[str] = None
    workpad_id: Optional[str] = None
    test_status: Optional[str] = None  # "passed", "failed", "pending"
    ci_status: Optional[str] = None  # "passed", "failed", "running", None
    is_trunk: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'CommitNode':
        return CommitNode(**data)


@dataclass
class TestResult:
    """Result of a single test."""
    test_id: str
    name: str
    status: str  # TestStatus
    duration_ms: int
    output: str = ""
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'TestResult':
        return TestResult(**data)


@dataclass
class TestRun:
    """A complete test run."""
    run_id: str
    workpad_id: Optional[str]
    target: str  # "fast" or "full"
    status: str  # TestStatus
    started_at: str
    completed_at: Optional[str] = None
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    duration_ms: int = 0
    tests: List[TestResult] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['tests'] = [t.to_dict() for t in self.tests]
        return result
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'TestRun':
        tests = [TestResult.from_dict(t) for t in data.pop('tests', [])]
        run = TestRun(**data)
        run.tests = tests
        return run


@dataclass
class PromotionRecord:
    """Record of a promotion decision."""

    record_id: str
    repo_id: str
    workpad_id: str
    decision: str
    can_promote: bool
    auto_promote_requested: bool
    promoted: bool
    commit_hash: Optional[str]
    message: str
    test_run_id: Optional[str] = None
    ci_status: Optional[str] = None
    ci_message: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'PromotionRecord':
        return PromotionRecord(**data)


@dataclass
class AIOperation:
    """An AI operation (planning, coding, etc.)."""
    operation_id: str
    workpad_id: Optional[str]
    operation_type: str  # "planning", "coding", "reviewing", "fixing"
    status: str  # AIOperationStatus
    model: str
    prompt: str
    response: Optional[str] = None
    cost_usd: float = 0.0
    tokens_used: int = 0
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'AIOperation':
        return AIOperation(**data)


@dataclass
class WorkpadState:
    """State of a workpad."""
    workpad_id: str
    repo_id: str
    title: str
    status: str  # WorkpadStatus
    branch_name: str
    base_commit: str
    current_commit: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    promoted_at: Optional[str] = None
    test_runs: List[str] = field(default_factory=list)  # TestRun IDs
    ai_operations: List[str] = field(default_factory=list)  # AIOperation IDs
    patches_applied: int = 0
    files_changed: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'WorkpadState':
        return WorkpadState(**data)


@dataclass
class RepositoryState:
    """State of a repository."""
    repo_id: str
    name: str
    path: str
    trunk_branch: str = "main"
    current_commit: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    workpads: List[str] = field(default_factory=list)  # Workpad IDs
    total_commits: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'RepositoryState':
        return RepositoryState(**data)


@dataclass
class GlobalState:
    """Global application state."""
    version: str = "1.0.0"
    last_updated: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    active_repo: Optional[str] = None
    active_workpad: Optional[str] = None
    session_start: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    total_operations: int = 0
    total_cost_usd: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'GlobalState':
        return GlobalState(**data)


# Event types for real-time updates
class EventType(Enum):
    """Types of events that can be emitted."""
    REPO_CREATED = "repo_created"
    REPO_UPDATED = "repo_updated"
    WORKPAD_CREATED = "workpad_created"
    WORKPAD_UPDATED = "workpad_updated"
    WORKPAD_PROMOTED = "workpad_promoted"
    WORKPAD_DELETED = "workpad_deleted"
    TEST_STARTED = "test_started"
    TEST_COMPLETED = "test_completed"
    AI_OPERATION_STARTED = "ai_operation_started"
    AI_OPERATION_COMPLETED = "ai_operation_completed"
    COMMIT_CREATED = "commit_created"
    PROMOTION_RECORDED = "promotion_recorded"


@dataclass
class StateEvent:
    """An event in the state system."""
    event_id: str
    event_type: str  # EventType
    timestamp: str
    data: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'StateEvent':
        return StateEvent(**data)
