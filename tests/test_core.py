
"""
Tests for core abstractions (Repository and Workpad).
"""

import pytest
from datetime import datetime
from pathlib import Path

from sologit.core.repository import Repository
from sologit.core.workpad import Workpad, Checkpoint


def test_repository_creation():
    """Test Repository dataclass creation."""
    repo = Repository(
        id="repo_test123",
        name="Test Repo",
        path=Path("/tmp/test"),
        trunk_branch="main",
        workpad_count=0,
    )
    
    assert repo.id == "repo_test123"
    assert repo.name == "Test Repo"
    assert repo.path == Path("/tmp/test")
    assert repo.trunk_branch == "main"
    assert repo.workpad_count == 0
    assert isinstance(repo.created_at, datetime)


def test_repository_to_dict():
    """Test Repository serialization."""
    repo = Repository(
        id="repo_test123",
        name="Test Repo",
        path=Path("/tmp/test"),
        trunk_branch="main",
    )
    
    data = repo.to_dict()
    
    assert data["id"] == "repo_test123"
    assert data["name"] == "Test Repo"
    assert data["path"] == "/tmp/test"
    assert data["trunk_branch"] == "main"
    assert "created_at" in data


def test_repository_from_dict():
    """Test Repository deserialization."""
    data = {
        "id": "repo_test123",
        "name": "Test Repo",
        "path": "/tmp/test",
        "trunk_branch": "main",
        "created_at": "2025-10-16T12:00:00",
        "workpad_count": 2,
    }
    
    repo = Repository.from_dict(data)
    
    assert repo.id == "repo_test123"
    assert repo.name == "Test Repo"
    assert repo.path == Path("/tmp/test")
    assert repo.trunk_branch == "main"
    assert repo.workpad_count == 2


def test_workpad_creation():
    """Test Workpad dataclass creation."""
    pad = Workpad(
        id="pad_test456",
        repo_id="repo_test123",
        title="Add feature",
        branch_name="pads/add-feature-20251016-1200",
        checkpoints=["t1", "t2"],
        status="active",
    )
    
    assert pad.id == "pad_test456"
    assert pad.repo_id == "repo_test123"
    assert pad.title == "Add feature"
    assert pad.branch_name == "pads/add-feature-20251016-1200"
    assert pad.checkpoints == ["t1", "t2"]
    assert pad.status == "active"
    assert isinstance(pad.created_at, datetime)


def test_workpad_to_dict():
    """Test Workpad serialization."""
    pad = Workpad(
        id="pad_test456",
        repo_id="repo_test123",
        title="Add feature",
        branch_name="pads/add-feature-20251016-1200",
        checkpoints=["t1", "t2"],
    )
    
    data = pad.to_dict()
    
    assert data["id"] == "pad_test456"
    assert data["repo_id"] == "repo_test123"
    assert data["title"] == "Add feature"
    assert data["checkpoints"] == ["t1", "t2"]
    assert "created_at" in data


def test_workpad_from_dict():
    """Test Workpad deserialization."""
    data = {
        "id": "pad_test456",
        "repo_id": "repo_test123",
        "title": "Add feature",
        "branch_name": "pads/add-feature-20251016-1200",
        "created_at": "2025-10-16T12:00:00",
        "checkpoints": ["t1", "t2"],
        "last_activity": "2025-10-16T12:30:00",
        "status": "active",
    }
    
    pad = Workpad.from_dict(data)
    
    assert pad.id == "pad_test456"
    assert pad.repo_id == "repo_test123"
    assert pad.title == "Add feature"
    assert pad.checkpoints == ["t1", "t2"]
    assert pad.status == "active"


def test_checkpoint_creation():
    """Test Checkpoint dataclass creation."""
    cp = Checkpoint(
        id="t1",
        pad_id="pad_test456",
        tag_name="pads/feature@t1",
        commit_hash="abc123def456",
        message="First checkpoint",
    )
    
    assert cp.id == "t1"
    assert cp.pad_id == "pad_test456"
    assert cp.tag_name == "pads/feature@t1"
    assert cp.commit_hash == "abc123def456"
    assert cp.message == "First checkpoint"
    assert isinstance(cp.created_at, datetime)
