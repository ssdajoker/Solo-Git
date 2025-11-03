
#!/usr/bin/env python3
"""
Preflight Test: Core Features

Tests all core documented features to ensure they work end-to-end.

Success criteria:
- All documented features work as described
- No errors or exceptions
- Results match expected behavior
"""

import pytest
from pathlib import Path


@pytest.mark.smoke
def test_repository_init_from_zip(git_engine, sample_zip):
    """Test repository initialization from ZIP file."""
    repo_id = git_engine.init_from_zip(sample_zip, "Preflight Test Repo")
    
    assert repo_id is not None
    assert repo_id.startswith("repo_")
    
    repo = git_engine.get_repo(repo_id)
    assert repo.name == "Preflight Test Repo"


@pytest.mark.smoke
def test_workpad_create(git_engine, sample_zip):
    """Test workpad creation."""
    repo_id = git_engine.init_from_zip(sample_zip, "Test Repo")
    workpad_id = git_engine.create_workpad(repo_id, "Test Feature")
    
    assert workpad_id is not None
    assert workpad_id.startswith("pad_")
    
    workpad = git_engine.get_workpad(workpad_id)
    assert workpad.title == "Test Feature"
    assert workpad.status == "active"


@pytest.mark.smoke
def test_workpad_checkpoint(git_engine, sample_zip):
    """Test workpad checkpointing."""
    repo_id = git_engine.init_from_zip(sample_zip, "Test Repo")
    workpad_id = git_engine.create_workpad(repo_id, "Test Feature")
    
    # Make a change
    repo_path = git_engine._get_repo_path(repo_id)
    test_file = repo_path / "test_change.txt"
    test_file.write_text("Test change")
    
    # Checkpoint
    git_engine.checkpoint_workpad(workpad_id, "Test checkpoint")
    
    workpad = git_engine.get_workpad(workpad_id)
    assert workpad.checkpoint_count > 0


@pytest.mark.smoke
def test_workpad_promote(git_engine, sample_zip):
    """Test workpad promotion."""
    repo_id = git_engine.init_from_zip(sample_zip, "Test Repo")
    workpad_id = git_engine.create_workpad(repo_id, "Test Feature")
    
    # Make and checkpoint a change
    repo_path = git_engine._get_repo_path(repo_id)
    test_file = repo_path / "feature.txt"
    test_file.write_text("New feature")
    git_engine.checkpoint_workpad(workpad_id, "Add feature")
    
    # Promote
    result = git_engine.promote_workpad(workpad_id)
    assert result is True
    
    workpad = git_engine.get_workpad(workpad_id)
    assert workpad.status == "merged"


def test_workpad_delete(git_engine, sample_zip):
    """Test workpad deletion."""
    repo_id = git_engine.init_from_zip(sample_zip, "Test Repo")
    workpad_id = git_engine.create_workpad(repo_id, "Test Feature")
    
    # Delete workpad
    git_engine.delete_workpad(workpad_id)
    
    # Verify it's gone
    with pytest.raises(Exception):
        git_engine.get_workpad(workpad_id)


def test_list_repos(git_engine, sample_zip):
    """Test repository listing."""
    # Create multiple repos
    repo_id1 = git_engine.init_from_zip(sample_zip, "Repo 1")
    repo_id2 = git_engine.init_from_zip(sample_zip, "Repo 2")
    
    repos = git_engine.list_repos()
    repo_ids = [r.id for r in repos]
    
    assert repo_id1 in repo_ids
    assert repo_id2 in repo_ids


def test_list_workpads(git_engine, sample_zip):
    """Test workpad listing."""
    repo_id = git_engine.init_from_zip(sample_zip, "Test Repo")
    
    # Create multiple workpads
    pad_id1 = git_engine.create_workpad(repo_id, "Feature 1")
    pad_id2 = git_engine.create_workpad(repo_id, "Feature 2")
    
    workpads = git_engine.list_workpads(repo_id)
    workpad_ids = [w.id for w in workpads]
    
    assert pad_id1 in workpad_ids
    assert pad_id2 in workpad_ids


def test_get_workpad_diff(git_engine, sample_zip):
    """Test getting workpad diff."""
    repo_id = git_engine.init_from_zip(sample_zip, "Test Repo")
    workpad_id = git_engine.create_workpad(repo_id, "Test Feature")
    
    # Make a change
    repo_path = git_engine._get_repo_path(repo_id)
    test_file = repo_path / "new_file.txt"
    test_file.write_text("New content")
    
    # Get diff
    diff = git_engine.get_workpad_diff(workpad_id)
    
    assert "new_file.txt" in diff
    assert "New content" in diff


def test_config_loading(config_manager):
    """Test configuration loading."""
    config = config_manager.config
    
    assert config is not None
    assert 'ai_models' in config
    assert 'budget' in config


def test_state_persistence(state_manager):
    """Test state can be saved and loaded."""
    # Create some state
    test_state = {
        'repos': {
            'repo_123': {
                'name': 'Test Repo',
                'created': '2024-01-01'
            }
        }
    }
    
    # Save
    state_manager.save_state(test_state)
    
    # Load
    loaded_state = state_manager.load_state()
    
    assert 'repos' in loaded_state
    assert 'repo_123' in loaded_state['repos']
