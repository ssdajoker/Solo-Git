
"""
Tests for Git Engine.
"""

import pytest
import tempfile
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO

from sologit.engines.git_engine import GitEngine, RepositoryNotFoundError, WorkpadNotFoundError


@pytest.fixture
def git_engine():
    """Create GitEngine with temporary data directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = GitEngine(data_dir=Path(tmpdir))
        yield engine


@pytest.fixture
def sample_zip():
    """Create a sample zip file."""
    buffer = BytesIO()
    with ZipFile(buffer, 'w') as zf:
        zf.writestr('README.md', '# Test Project\n')
        zf.writestr('main.py', 'print("Hello, World!")\n')
    buffer.seek(0)
    return buffer.read()


def test_init_from_zip(git_engine, sample_zip):
    """Test repository initialization from zip."""
    repo_id = git_engine.init_from_zip(sample_zip, "Test Repo")
    
    assert repo_id.startswith("repo_")
    assert len(repo_id) == 13  # repo_ + 8 char hex
    
    repo = git_engine.get_repo(repo_id)
    assert repo is not None
    assert repo.name == "Test Repo"
    assert repo.trunk_branch == "main"
    assert repo.workpad_count == 0


def test_create_workpad(git_engine, sample_zip):
    """Test workpad creation."""
    repo_id = git_engine.init_from_zip(sample_zip, "Test Repo")
    
    pad_id = git_engine.create_workpad(repo_id, "Add feature")
    
    assert pad_id.startswith("pad_")
    assert len(pad_id) == 12  # pad_ + 8 char hex
    
    workpad = git_engine.get_workpad(pad_id)
    assert workpad is not None
    assert workpad.title == "Add feature"
    assert workpad.repo_id == repo_id
    assert "pads/add-feature-" in workpad.branch_name
    assert workpad.status == "active"
    
    # Check repository updated
    repo = git_engine.get_repo(repo_id)
    assert repo.workpad_count == 1


def test_list_repos(git_engine, sample_zip):
    """Test listing repositories."""
    # Initially empty
    assert len(git_engine.list_repos()) == 0
    
    # Add repos
    repo_id1 = git_engine.init_from_zip(sample_zip, "Repo 1")
    repo_id2 = git_engine.init_from_zip(sample_zip, "Repo 2")
    
    repos = git_engine.list_repos()
    assert len(repos) == 2
    assert {r.id for r in repos} == {repo_id1, repo_id2}


def test_list_workpads(git_engine, sample_zip):
    """Test listing workpads."""
    repo_id1 = git_engine.init_from_zip(sample_zip, "Repo 1")
    repo_id2 = git_engine.init_from_zip(sample_zip, "Repo 2")
    
    pad_id1 = git_engine.create_workpad(repo_id1, "Feature 1")
    pad_id2 = git_engine.create_workpad(repo_id1, "Feature 2")
    pad_id3 = git_engine.create_workpad(repo_id2, "Feature 3")
    
    # List all workpads
    all_pads = git_engine.list_workpads()
    assert len(all_pads) == 3
    
    # Filter by repo
    repo1_pads = git_engine.list_workpads(repo_id1)
    assert len(repo1_pads) == 2
    assert {p.id for p in repo1_pads} == {pad_id1, pad_id2}


def test_workpad_not_found(git_engine):
    """Test error when workpad not found."""
    with pytest.raises(WorkpadNotFoundError):
        git_engine.get_diff("pad_invalid")


def test_repository_not_found(git_engine):
    """Test error when repository not found."""
    with pytest.raises(RepositoryNotFoundError):
        git_engine.create_workpad("repo_invalid", "Title")


def test_can_promote(git_engine, sample_zip):
    """Test can_promote check."""
    repo_id = git_engine.init_from_zip(sample_zip, "Test Repo")
    pad_id = git_engine.create_workpad(repo_id, "Feature")
    
    # Should be able to promote (no changes yet, but fast-forward is possible)
    assert git_engine.can_promote(pad_id) is True


def test_metadata_persistence(git_engine, sample_zip):
    """Test metadata is saved and loaded."""
    repo_id = git_engine.init_from_zip(sample_zip, "Test Repo")
    pad_id = git_engine.create_workpad(repo_id, "Feature")
    
    # Create new engine with same data directory
    new_engine = GitEngine(data_dir=git_engine.data_dir)
    
    # Check data persisted
    repo = new_engine.get_repo(repo_id)
    assert repo is not None
    assert repo.name == "Test Repo"
    
    workpad = new_engine.get_workpad(pad_id)
    assert workpad is not None
    assert workpad.title == "Feature"
