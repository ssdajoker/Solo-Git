
#!/usr/bin/env python3
"""
Preflight Test: Data Persistence

Tests that data is correctly persisted and survives process restarts.

Success criteria:
- State saves correctly
- State loads correctly
- No data loss
- State is consistent after restart
"""

import pytest
from pathlib import Path


def test_state_save_and_load(data_dir):
    """Test state can be saved and loaded."""
    from sologit.state.manager import StateManager
    
    manager = StateManager(data_dir=data_dir)
    
    # Create test state
    test_state = {
        'repos': {
            'repo_123': {
                'name': 'Test Repo',
                'created': '2024-01-01'
            }
        },
        'workpads': {
            'pad_456': {
                'title': 'Test Workpad',
                'repo_id': 'repo_123'
            }
        }
    }
    
    # Save
    manager.save_state(test_state)
    
    # Create new manager instance (simulates process restart)
    manager2 = StateManager(data_dir=data_dir)
    loaded_state = manager2.load_state()
    
    # Verify data persisted
    assert 'repos' in loaded_state
    assert 'repo_123' in loaded_state['repos']
    assert loaded_state['repos']['repo_123']['name'] == 'Test Repo'


def test_repo_persistence(git_engine, sample_zip):
    """Test repository information persists."""
    # Create repo
    repo_id = git_engine.init_from_zip(sample_zip, "Persistent Repo")
    original_repo = git_engine.get_repo(repo_id)
    
    # Create new engine instance (simulates restart)
    from sologit.engines.git_engine import GitEngine
    engine2 = GitEngine(data_dir=git_engine.data_dir)
    
    # Load repo
    loaded_repo = engine2.get_repo(repo_id)
    
    assert loaded_repo.id == original_repo.id
    assert loaded_repo.name == original_repo.name


def test_workpad_persistence(git_engine, sample_zip):
    """Test workpad information persists."""
    # Create repo and workpad
    repo_id = git_engine.init_from_zip(sample_zip, "Test Repo")
    workpad_id = git_engine.create_workpad(repo_id, "Persistent Workpad")
    original_workpad = git_engine.get_workpad(workpad_id)
    
    # Create new engine instance
    from sologit.engines.git_engine import GitEngine
    engine2 = GitEngine(data_dir=git_engine.data_dir)
    
    # Load workpad
    loaded_workpad = engine2.get_workpad(workpad_id)
    
    assert loaded_workpad.id == original_workpad.id
    assert loaded_workpad.title == original_workpad.title


def test_config_persistence(config_dir):
    """Test configuration persists across instances."""
    from sologit.config.manager import ConfigManager
    
    config_file = config_dir / "persistent_config.yaml"
    
    # Create and save config
    manager = ConfigManager(config_path=config_file)
    manager.set('test_key', 'test_value')
    manager.save_config()
    
    # Load in new instance
    manager2 = ConfigManager(config_path=config_file)
    value = manager2.get('test_key')
    
    assert value == 'test_value'


def test_state_handles_empty_file(data_dir):
    """Test state manager handles empty/missing state file."""
    from sologit.state.manager import StateManager
    
    manager = StateManager(data_dir=data_dir)
    
    # Should not crash, should return empty/default state
    state = manager.load_state()
    
    assert isinstance(state, dict)
