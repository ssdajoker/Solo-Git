"""
Shared pytest fixtures for Solo-Git test suite.

This module provides common test fixtures that can be used across all test files,
reducing duplication and ensuring consistent test setup.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import os
from zipfile import ZipFile
from io import BytesIO
from unittest.mock import Mock, MagicMock
from datetime import datetime

# Import core components
from sologit.engines.git_engine import GitEngine
from sologit.state.manager import StateManager
from sologit.config.manager import ConfigManager
from sologit.orchestration.ai_orchestrator import AIOrchestrator
from sologit.orchestration.cost_guard import CostGuard, CostTracker


# ===========================
# Directory & Path Fixtures
# ===========================

@pytest.fixture
def temp_dir():
    """Create a temporary directory that's cleaned up after test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def data_dir(temp_dir):
    """Create a temporary data directory for Solo-Git state."""
    data_path = temp_dir / "data"
    data_path.mkdir(parents=True, exist_ok=True)
    return data_path


@pytest.fixture
def config_dir(temp_dir):
    """Create a temporary config directory."""
    config_path = temp_dir / "config"
    config_path.mkdir(parents=True, exist_ok=True)
    return config_path


# ===========================
# Sample Data Fixtures
# ===========================

@pytest.fixture
def sample_zip():
    """Create a minimal sample zip file for testing repository initialization."""
    buffer = BytesIO()
    with ZipFile(buffer, 'w') as zf:
        zf.writestr('README.md', '# Test Project\n\nA test project for Solo-Git.\n')
        zf.writestr('main.py', 'print("Hello, World!")\n')
        zf.writestr('tests/test_main.py', 'def test_hello():\n    assert True\n')
    buffer.seek(0)
    return buffer.read()


@pytest.fixture
def sample_zip_with_tests():
    """Create a sample zip with more comprehensive test structure."""
    buffer = BytesIO()
    with ZipFile(buffer, 'w') as zf:
        # Source files
        zf.writestr('README.md', '# Test Project\n')
        zf.writestr('src/__init__.py', '')
        zf.writestr('src/main.py', '''
def add(a, b):
    """Add two numbers."""
    return a + b

def subtract(a, b):
    """Subtract two numbers."""
    return a - b
''')
        # Test files
        zf.writestr('tests/__init__.py', '')
        zf.writestr('tests/test_main.py', '''
import pytest
from src.main import add, subtract

def test_add():
    assert add(1, 2) == 3
    assert add(-1, 1) == 0

def test_subtract():
    assert subtract(5, 3) == 2
    assert subtract(0, 0) == 0
''')
        # Configuration
        zf.writestr('pytest.ini', '[pytest]\ntestpaths = tests\n')
        zf.writestr('requirements.txt', 'pytest>=7.0.0\n')
    buffer.seek(0)
    return buffer.read()


@pytest.fixture
def sample_python_code():
    """Sample Python code for testing code generation/patching."""
    return '''
def hello(name):
    """Greet someone."""
    return f"Hello, {name}!"

def goodbye(name):
    """Say goodbye to someone."""
    return f"Goodbye, {name}!"
'''


# ===========================
# Core Engine Fixtures
# ===========================

@pytest.fixture
def git_engine(data_dir):
    """Create GitEngine instance with temporary data directory."""
    engine = GitEngine(data_dir=data_dir)
    return engine


@pytest.fixture
def state_manager(data_dir):
    """Create StateManager instance with temporary data directory."""
    manager = StateManager(data_dir=data_dir)
    return manager


@pytest.fixture
def config_manager(config_dir, tmp_path):
    """Create ConfigManager with test configuration."""
    config_file = config_dir / "config.yaml"
    
    # Create minimal test config
    config_content = """
# Test configuration for Solo-Git

ai_models:
  fast_tier:
    - model_id: "test-fast"
      name: "Test Fast Model"
      provider: "test"
      cost_per_1k_tokens: 0.001
      complexity_range: [0.0, 0.3]
  coding_tier:
    - model_id: "test-coding"
      name: "Test Coding Model"
      provider: "test"
      cost_per_1k_tokens: 0.01
      complexity_range: [0.3, 0.7]
  planning_tier:
    - model_id: "test-planning"
      name: "Test Planning Model"
      provider: "test"
      cost_per_1k_tokens: 0.1
      complexity_range: [0.7, 1.0]

routing:
  default_tier: "coding_tier"
  security_keywords: ["auth", "crypto", "password"]
  escalation:
    triggers: []

budget:
  daily_usd_cap: 10.0
  alert_threshold: 0.8
  track_by_model: true

test_execution:
  timeout_seconds: 30
  parallel_jobs: 4

promotion_rules:
  require_passing_tests: true
  fast_forward_only: true
  max_changed_files: 50

promote_on_green: true
rollback_on_ci_red: true
"""
    config_file.write_text(config_content)
    return ConfigManager(config_path=config_file)


# ===========================
# AI/Orchestration Fixtures
# ===========================

@pytest.fixture
def mock_ai_client():
    """Create a mock AI client that returns predictable responses."""
    mock = Mock()
    
    def mock_chat_completion(*args, **kwargs):
        prompt = kwargs.get('prompt', '')
        
        # Return different responses based on prompt keywords
        if 'plan' in prompt.lower():
            return {
                'content': '1. Analyze requirements\n2. Write code\n3. Add tests\n4. Run tests',
                'model': 'test-model',
                'usage': {'total_tokens': 100},
                'cost_usd': 0.001
            }
        elif 'patch' in prompt.lower() or 'code' in prompt.lower():
            return {
                'content': '```python\ndef new_function():\n    return True\n```',
                'model': 'test-model',
                'usage': {'total_tokens': 150},
                'cost_usd': 0.0015
            }
        else:
            return {
                'content': 'Test response',
                'model': 'test-model',
                'usage': {'total_tokens': 50},
                'cost_usd': 0.0005
            }
    
    mock.chat_completion = Mock(side_effect=mock_chat_completion)
    return mock


@pytest.fixture
def mock_cost_guard():
    """Create a mock CostGuard that always allows operations."""
    mock = Mock(spec=CostGuard)
    mock.check_budget_before_operation.return_value = True
    mock.record_usage.return_value = None
    mock.get_usage_summary.return_value = {
        'today_usd': 0.50,
        'this_week_usd': 2.00,
        'this_month_usd': 5.00,
        'by_model': {}
    }
    return mock


@pytest.fixture
def orchestrator(config_manager, tmp_path):
    """Create AI orchestrator with isolated cost tracking."""
    orch = AIOrchestrator(config_manager)
    
    # Use test-specific storage path to avoid state sharing between tests
    storage_path = tmp_path / f"usage_{id(orch)}.json"
    orch.cost_guard.tracker = CostTracker(storage_path)
    
    return orch


# ===========================
# Repository Setup Fixtures
# ===========================

@pytest.fixture
def initialized_repo(git_engine, sample_zip):
    """Create and return an initialized repository."""
    repo_id = git_engine.init_from_zip(sample_zip, "Test Repository")
    return git_engine.get_repo(repo_id)


@pytest.fixture
def repo_with_workpad(git_engine, sample_zip):
    """Create a repository with an active workpad."""
    repo_id = git_engine.init_from_zip(sample_zip, "Test Repository")
    workpad_id = git_engine.create_workpad(repo_id, "Test Feature")
    
    repo = git_engine.get_repo(repo_id)
    workpad = git_engine.get_workpad(workpad_id)
    
    return {
        'repo': repo,
        'workpad': workpad,
        'repo_id': repo_id,
        'workpad_id': workpad_id,
        'engine': git_engine
    }


@pytest.fixture
def repo_with_changes(git_engine, sample_zip):
    """Create a repository with a workpad that has uncommitted changes."""
    repo_id = git_engine.init_from_zip(sample_zip, "Test Repository")
    workpad_id = git_engine.create_workpad(repo_id, "Add Feature")
    
    # Make some changes
    repo = git_engine.get_repo(repo_id)
    repo_path = git_engine._get_repo_path(repo_id)
    
    # Add a new file
    new_file = repo_path / "new_feature.py"
    new_file.write_text("def new_feature():\n    return 'New Feature'\n")
    
    # Modify existing file
    main_file = repo_path / "main.py"
    content = main_file.read_text()
    main_file.write_text(content + "\n# Modified\n")
    
    return {
        'repo': repo,
        'repo_id': repo_id,
        'workpad_id': workpad_id,
        'engine': git_engine
    }


# ===========================
# CLI Testing Fixtures
# ===========================

@pytest.fixture
def cli_runner():
    """Create Click CLI test runner."""
    from click.testing import CliRunner
    return CliRunner()


@pytest.fixture
def isolated_cli_env(temp_dir, monkeypatch):
    """
    Set up isolated environment for CLI testing.
    Ensures CLI uses temporary directories for all operations.
    """
    # Set environment variables to use temp directories
    monkeypatch.setenv('SOLOGIT_DATA_DIR', str(temp_dir / 'data'))
    monkeypatch.setenv('SOLOGIT_CONFIG_DIR', str(temp_dir / 'config'))
    
    # Create directories
    (temp_dir / 'data').mkdir(parents=True, exist_ok=True)
    (temp_dir / 'config').mkdir(parents=True, exist_ok=True)
    
    return temp_dir


# ===========================
# CLI Headless Adapter (Tests)
# ===========================

@pytest.fixture(autouse=True)
def _enable_legacy_headless_adapter(monkeypatch):
    """Force CLI to use in-process legacy adapter instead of HTTP in tests.

    This lets existing tests that patch get_git_engine/get_git_sync influence
    CLI behavior while we migrate to the headless-backed commands.
    """
    monkeypatch.setenv("SOLOGIT_CLI_USE_LEGACY_ENGINE", "1")
    # Ensure deterministic environment for tests
    monkeypatch.delenv("SOLOGIT_HEADLESS_BASE_URL", raising=False)


@pytest.fixture(autouse=True)
def _default_isolated_env(tmp_path, monkeypatch):
    """Ensure CLI-related services use per-test isolated directories by default."""
    data_dir = tmp_path / "data"
    config_dir = tmp_path / "config"
    data_dir.mkdir(parents=True, exist_ok=True)
    config_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv('SOLOGIT_DATA_DIR', str(data_dir))
    monkeypatch.setenv('SOLOGIT_CONFIG_DIR', str(config_dir))


# ===========================
# Mock Response Fixtures
# ===========================

@pytest.fixture
def mock_test_results():
    """Create mock test results for testing."""
    return {
        'passed': 10,
        'failed': 2,
        'skipped': 1,
        'total': 13,
        'duration': 5.2,
        'failures': [
            {
                'test': 'test_feature_x',
                'error': 'AssertionError: Expected 5, got 3',
                'category': 'ASSERTION_FAILURE'
            },
            {
                'test': 'test_timeout',
                'error': 'Test exceeded timeout of 5s',
                'category': 'TIMEOUT'
            }
        ]
    }


@pytest.fixture
def mock_git_diff():
    """Create a sample git diff for testing."""
    return """diff --git a/main.py b/main.py
index 1234567..abcdefg 100644
--- a/main.py
+++ b/main.py
@@ -1,3 +1,6 @@
+def new_function():
+    return "Hello"
+
 def hello():
     print("Hello, World!")
"""


# ===========================
# Marker-based Fixtures
# ===========================

@pytest.fixture
def skip_if_no_api_key(monkeypatch):
    """Skip test if API keys are not configured."""
    # Check for actual API keys
    import os
    if not os.getenv('ABACUS_API_KEY'):
        pytest.skip("API keys not configured")


# ===========================
# Cleanup Fixtures
# ===========================

@pytest.fixture(autouse=True)
def cleanup_git_state():
    """Ensure git state is clean before and after each test."""
    # Setup: Nothing to do
    yield
    # Teardown: Clean up any test repositories
    import os
    test_dirs = [
        '/tmp/sologit-test-',
        '/tmp/pytest-of-'
    ]
    # Cleanup is handled by temp_dir fixture


# ===========================
# Performance Testing Fixtures
# ===========================

@pytest.fixture
def benchmark_timer():
    """Simple timer for benchmarking test operations."""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.perf_counter()
        
        def stop(self):
            self.end_time = time.perf_counter()
            return self.elapsed
        
        @property
        def elapsed(self):
            if self.start_time is None:
                return 0
            if self.end_time is None:
                return time.perf_counter() - self.start_time
            return self.end_time - self.start_time
    
    return Timer()


# ===========================
# Async Testing Fixtures
# ===========================

@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ===========================
# Configuration Helpers
# ===========================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests"
    )
    config.addinivalue_line(
        "markers", "cli: marks tests as CLI-specific"
    )
    config.addinivalue_line(
        "markers", "tui: marks tests as TUI-specific"
    )
    config.addinivalue_line(
        "markers", "gui: marks tests as GUI-specific"
    )
    config.addinivalue_line(
        "markers", "ai: marks tests that require AI API access"
    )
    config.addinivalue_line(
        "markers", "smoke: marks tests as smoke tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )


# ===========================
# Test Collection Filters
# ===========================

def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Auto-mark tests based on path
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
        elif "cli" in str(item.fspath):
            item.add_marker(pytest.mark.cli)
        elif "ui" in str(item.fspath) and "tui" in str(item.fspath):
            item.add_marker(pytest.mark.tui)
        
        # Auto-mark slow tests (integration and e2e are typically slow)
        if any(marker in str(item.fspath) for marker in ["integration", "e2e"]):
            item.add_marker(pytest.mark.slow)
