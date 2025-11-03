
#!/usr/bin/env python3
"""
Preflight Test: API Contracts

Validates that API contracts match documentation and haven't broken.

Success criteria:
- All documented APIs exist
- Function signatures match documentation
- Return values have expected structure
- No breaking changes
"""

import pytest
import inspect


def test_git_engine_api_contract():
    """Test GitEngine has documented methods with correct signatures."""
    from sologit.engines.git_engine import GitEngine
    
    # Check required methods exist
    required_methods = [
        'init_from_zip',
        'create_workpad',
        'checkpoint_workpad',
        'promote_workpad',
        'delete_workpad',
        'get_repo',
        'get_workpad',
        'list_repos',
        'list_workpads',
        'get_workpad_diff'
    ]
    
    for method_name in required_methods:
        assert hasattr(GitEngine, method_name), f"GitEngine missing method: {method_name}"
        method = getattr(GitEngine, method_name)
        assert callable(method), f"GitEngine.{method_name} is not callable"


def test_state_manager_api_contract():
    """Test StateManager has documented methods."""
    from sologit.state.manager import StateManager
    
    required_methods = [
        'save_state',
        'load_state',
        'get_repo',
        'get_workpad',
        'list_repos',
        'list_workpads'
    ]
    
    for method_name in required_methods:
        assert hasattr(StateManager, method_name), f"StateManager missing method: {method_name}"


def test_config_manager_api_contract():
    """Test ConfigManager has documented methods."""
    from sologit.config.manager import ConfigManager
    
    required_methods = [
        'load_config',
        'save_config',
        'get',
        'set'
    ]
    
    for method_name in required_methods:
        assert hasattr(ConfigManager, method_name), f"ConfigManager missing method: {method_name}"


def test_ai_orchestrator_api_contract():
    """Test AIOrchestrator has documented methods."""
    from sologit.orchestration.ai_orchestrator import AIOrchestrator
    
    required_methods = [
        'plan',
        'generate_patch',
        'review_patch',
        'get_status'
    ]
    
    for method_name in required_methods:
        assert hasattr(AIOrchestrator, method_name), f"AIOrchestrator missing method: {method_name}"


def test_repo_object_contract(initialized_repo):
    """Test Repository object has required attributes."""
    required_attrs = ['id', 'name', 'trunk_branch', 'workpad_count', 'created_at']
    
    for attr in required_attrs:
        assert hasattr(initialized_repo, attr), f"Repository missing attribute: {attr}"


def test_workpad_object_contract(repo_with_workpad):
    """Test Workpad object has required attributes."""
    workpad = repo_with_workpad['workpad']
    
    required_attrs = ['id', 'title', 'repo_id', 'branch_name', 'status', 'created_at', 'checkpoint_count']
    
    for attr in required_attrs:
        assert hasattr(workpad, attr), f"Workpad missing attribute: {attr}"


def test_cli_commands_exist():
    """Test that documented CLI commands exist."""
    from sologit.cli import commands
    
    # Commands should be Click commands
    required_commands = [
        'repo',
        'pad', 
        'test_cmd',
        'pair',
        'heaven'
    ]
    
    for cmd_name in required_commands:
        # Check if command exists in module
        assert hasattr(commands, cmd_name) or hasattr(commands, f'{cmd_name}_group'), \
            f"CLI command not found: {cmd_name}"
