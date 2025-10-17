"""
Tests to achieve 100% coverage for core classes (Repository and Workpad).
"""

import pytest
from datetime import datetime
from pathlib import Path
from sologit.core.repository import Repository
from sologit.core.workpad import Workpad, Checkpoint


class TestRepositoryComplete:
    """Complete coverage for Repository class."""

    def test_repository_path_conversion(self):
        """Test __post_init__ converts string path to Path object."""
        repo = Repository(
            id="repo_test",
            name="Test Repo",
            path="/some/path/to/repo",  # String path
            trunk_branch="main",
            created_at=datetime.now()
        )
        
        # Path should be converted to Path object
        assert isinstance(repo.path, Path)
        assert str(repo.path) == "/some/path/to/repo"


class TestCheckpointComplete:
    """Complete coverage for Checkpoint class."""

    def test_checkpoint_to_dict(self):
        """Test Checkpoint to_dict serialization."""
        created = datetime(2025, 10, 17, 12, 0, 0)
        checkpoint = Checkpoint(
            id="t1",
            pad_id="pad_test123",
            tag_name="pads/test-branch@t1",
            commit_hash="abc123def456",
            message="Test checkpoint",
            created_at=created
        )
        
        result = checkpoint.to_dict()
        
        assert result["id"] == "t1"
        assert result["pad_id"] == "pad_test123"
        assert result["tag_name"] == "pads/test-branch@t1"
        assert result["commit_hash"] == "abc123def456"
        assert result["message"] == "Test checkpoint"
        assert result["created_at"] == created.isoformat()

    def test_checkpoint_from_dict(self):
        """Test Checkpoint from_dict deserialization."""
        data = {
            "id": "t2",
            "pad_id": "pad_test456",
            "tag_name": "pads/another-branch@t2",
            "commit_hash": "def789ghi012",
            "message": "Another checkpoint",
            "created_at": "2025-10-17T13:30:00"
        }
        
        checkpoint = Checkpoint.from_dict(data)
        
        assert checkpoint.id == "t2"
        assert checkpoint.pad_id == "pad_test456"
        assert checkpoint.tag_name == "pads/another-branch@t2"
        assert checkpoint.commit_hash == "def789ghi012"
        assert checkpoint.message == "Another checkpoint"
        assert isinstance(checkpoint.created_at, datetime)
