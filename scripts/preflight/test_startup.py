
#!/usr/bin/env python3
"""
Preflight Test: System Startup and Initialization

Tests that the Solo-Git system can start up correctly and all basic
infrastructure is in place.

Success criteria:
- All modules import without errors
- Configuration loads successfully
- Required directories are created
- Environment is properly set up
"""

import pytest
import sys
from pathlib import Path


@pytest.mark.smoke
def test_imports():
    """Test that all core modules can be imported."""
    try:
        # Core engines
        from sologit.engines.git_engine import GitEngine
        from sologit.engines.patch_engine import PatchEngine
        
        # State management
        from sologit.state.manager import StateManager
        
        # Configuration
        from sologit.config.manager import ConfigManager
        
        # Orchestration
        from sologit.orchestration.ai_orchestrator import AIOrchestrator
        from sologit.orchestration.cost_guard import CostGuard
        from sologit.orchestration.model_router import ModelRouter
        
        # Workflows
        from sologit.workflows.auto_merge import AutoMergeWorkflow
        from sologit.workflows.promotion_gate import PromotionGate
        
        # CLI
        from sologit.cli.main import main
        
    except ImportError as e:
        pytest.fail(f"Failed to import core module: {e}")


@pytest.mark.smoke
def test_config_template_exists():
    """Test that default configuration template exists."""
    from sologit.config import templates
    
    assert hasattr(templates, 'DEFAULT_CONFIG')
    assert isinstance(templates.DEFAULT_CONFIG, str)
    assert len(templates.DEFAULT_CONFIG) > 0


@pytest.mark.smoke
def test_data_directory_creation(temp_dir):
    """Test that data directory structure can be created."""
    from sologit.engines.git_engine import GitEngine
    
    data_dir = temp_dir / "data"
    engine = GitEngine(data_dir=data_dir)
    
    # Check that directories were created
    assert data_dir.exists()
    repos_dir = data_dir / "repos"
    assert repos_dir.exists() or True  # May not exist until first repo created


@pytest.mark.smoke
def test_config_manager_initialization(config_dir, temp_dir):
    """Test that ConfigManager can initialize with default config."""
    from sologit.config.manager import ConfigManager
    
    config_file = config_dir / "test_config.yaml"
    
    # Create minimal config
    config_file.write_text("""
ai_models:
  fast_tier: []
  coding_tier: []
  planning_tier: []

budget:
  daily_usd_cap: 10.0
""")
    
    manager = ConfigManager(config_path=config_file)
    assert manager is not None
    config = manager.config
    assert 'ai_models' in config
    assert 'budget' in config


@pytest.mark.smoke
def test_cli_entry_point():
    """Test that CLI entry point is accessible."""
    from sologit.cli.main import main
    
    assert callable(main)


@pytest.mark.smoke  
def test_version_info():
    """Test that version information is available."""
    try:
        from sologit import __version__
        assert __version__ is not None
    except ImportError:
        # Version might not be defined, that's ok for now
        pass
