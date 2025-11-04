"""
Preflight Test Configuration

This conftest.py serves as a bridge to import shared fixtures from the main
test suite (tests/conftest.py) so that preflight tests can use them.

This solves the fixture discovery issue where pytest cannot find fixtures
defined in a parent directory's conftest.py when running tests from a
subdirectory like scripts/preflight/.

Fixtures imported:
- Directory & Path: temp_dir, data_dir, config_dir
- Sample Data: sample_zip, sample_zip_with_tests, sample_python_code
- Core Engines: git_engine, state_manager, config_manager
- AI/Orchestration: mock_ai_client, mock_cost_guard, orchestrator
- Repository Setup: initialized_repo, repo_with_workpad, repo_with_changes
- CLI Testing: cli_runner, isolated_cli_env
"""

import sys
from pathlib import Path

# Add tests directory to Python path so we can import from tests.conftest
tests_dir = Path(__file__).parent.parent.parent / "tests"
if str(tests_dir) not in sys.path:
    sys.path.insert(0, str(tests_dir))

# Import all fixtures from the main test conftest
# This makes them available to preflight tests
from conftest import (
    # Directory & Path Fixtures
    temp_dir,
    data_dir,
    config_dir,
    
    # Sample Data Fixtures
    sample_zip,
    sample_zip_with_tests,
    sample_python_code,
    
    # Core Engine Fixtures
    git_engine,
    state_manager,
    config_manager,
    
    # AI/Orchestration Fixtures (if they exist)
    mock_ai_client,
    mock_cost_guard,
)

# Try to import additional fixtures that may or may not exist
try:
    from conftest import (
        orchestrator,
        initialized_repo,
        repo_with_workpad,
        repo_with_changes,
        cli_runner,
        isolated_cli_env,
    )
except ImportError:
    # These fixtures might not exist yet, that's okay
    pass

# Re-export all imported fixtures so they're available to preflight tests
__all__ = [
    'temp_dir',
    'data_dir',
    'config_dir',
    'sample_zip',
    'sample_zip_with_tests',
    'sample_python_code',
    'git_engine',
    'state_manager',
    'config_manager',
    'mock_ai_client',
    'mock_cost_guard',
]
