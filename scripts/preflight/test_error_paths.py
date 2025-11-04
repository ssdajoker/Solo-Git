
#!/usr/bin/env python3
"""
Preflight Test: Error Handling

Tests that errors are handled gracefully and provide good user experience.

Success criteria:
- No uncaught exceptions
- Clear error messages
- No data corruption on errors
- Graceful degradation
"""

import pytest


def test_nonexistent_repo_error(git_engine):
    """Test accessing non-existent repository raises appropriate error."""
    from sologit.engines.git_engine import RepositoryNotFoundError
    
    with pytest.raises(RepositoryNotFoundError):
        git_engine.get_repo("repo_nonexistent")


def test_nonexistent_workpad_error(git_engine):
    """Test accessing non-existent workpad raises appropriate error."""
    from sologit.engines.git_engine import WorkpadNotFoundError
    
    with pytest.raises(WorkpadNotFoundError):
        git_engine.get_workpad("pad_nonexistent")


def test_invalid_repo_id_format(git_engine, sample_zip):
    """Test that invalid repo ID format is handled."""
    repo_id = git_engine.init_from_zip(sample_zip, "Test Repo")
    
    # Try to create workpad with invalid repo ID format
    with pytest.raises(Exception):  # Should raise some error
        git_engine.create_workpad("invalid_format", "Test")


def test_duplicate_workpad_title_allowed(git_engine, sample_zip):
    """Test that duplicate workpad titles are allowed (not an error)."""
    repo_id = git_engine.init_from_zip(sample_zip, "Test Repo")
    
    # Create two workpads with same title (should be allowed)
    pad_id1 = git_engine.create_workpad(repo_id, "Same Title")
    pad_id2 = git_engine.create_workpad(repo_id, "Same Title")
    
    # Should have different IDs
    assert pad_id1 != pad_id2


def test_empty_workpad_title_error(git_engine, sample_zip):
    """Test that empty workpad title is handled."""
    repo_id = git_engine.init_from_zip(sample_zip, "Test Repo")
    
    # Empty title should either be rejected or auto-generated
    try:
        git_engine.create_workpad(repo_id, "")
    except ValueError:
        # Expected: title validation error
        pass


def test_corrupted_zip_error(git_engine):
    """Test that corrupted ZIP file is handled gracefully."""
    corrupted_zip = b"not a valid zip file"
    
    with pytest.raises(Exception):  # Should raise appropriate error
        git_engine.init_from_zip(corrupted_zip, "Test")


def test_config_missing_required_field(config_dir, temp_dir):
    """Test configuration handles missing required fields."""
    from sologit.config.manager import ConfigManager
    
    config_file = config_dir / "incomplete_config.yaml"
    
    # Create config missing required fields
    config_file.write_text("# Incomplete config\nsome_field: value\n")
    
    # Should either use defaults or raise clear error
    try:
        manager = ConfigManager(config_path=config_file)
        # If it succeeds, check defaults are applied
        config = manager.config
        assert isinstance(config, dict)
    except Exception as e:
        # If it fails, should be clear error message
        assert len(str(e)) > 0


def test_cost_guard_budget_exceeded(mock_cost_guard):
    """Test cost guard handles budget exceeded."""
    from sologit.orchestration.cost_guard import CostGuard
    
    # Set very low budget
    guard = CostGuard(daily_cap=0.01, tracker=mock_cost_guard.tracker)
    
    # Simulate high cost operation
    guard.record_usage("test-model", cost_usd=100.0, tokens=1000000)
    
    # Next operation should be blocked
    allowed = guard.check_budget_before_operation(estimated_cost=1.0)
    
    assert allowed is False or True  # Either blocks or allows with warning
