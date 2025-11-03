# Solo-Git Test Suite

Welcome to the Solo-Git test suite! This README provides a comprehensive guide to understanding, running, and contributing to tests.

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Test Organization](#test-organization)
- [Running Tests](#running-tests)
- [Writing Tests](#writing-tests)
- [Test Infrastructure](#test-infrastructure)
- [CI/CD Integration](#cicd-integration)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## 🚀 Quick Start

```bash
# Install test dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run fast tests only
pytest -m "not slow"

# Run with coverage
pytest --cov=sologit --cov-report=html

# Run smoke tests (< 30s)
pytest -m smoke

# Run preflight self-tests
python scripts/preflight/run_preflight.py
```

## 📁 Test Organization

```
tests/
├── README.md                 # This file
├── MARKERS.md               # Pytest marker documentation
├── COVERAGE.md              # Coverage guide
├── conftest.py              # Shared fixtures and configuration
│
├── utils/                   # Test utilities
│   ├── __init__.py
│   ├── assertions.py        # Custom assertion helpers
│   ├── factories.py         # Factory functions for test objects
│   └── helpers.py           # Helper functions
│
├── test_*.py                # Test files (845+ tests)
│
└── [organized by feature]

scripts/preflight/           # Self-test suite
├── README.md
├── test_startup.py          # System initialization tests
├── test_core_features.py    # Feature validation tests
├── test_contracts.py        # API contract tests
├── test_persistence.py      # Data persistence tests
└── test_error_paths.py      # Error handling tests
```

## 🏃 Running Tests

### Basic Commands

```bash
# Run all tests
pytest

# Verbose output
pytest -v

# Stop on first failure
pytest -x

# Run last failed tests
pytest --lf

# Run specific test file
pytest tests/test_git_engine.py

# Run specific test function
pytest tests/test_git_engine.py::test_init_from_zip

# Run tests matching pattern
pytest -k "workpad"
```

### By Test Type

```bash
# Unit tests (fast, isolated)
pytest -m unit

# Integration tests (component interaction)
pytest -m integration

# End-to-end tests (full workflows)
pytest -m e2e

# Smoke tests (critical paths, < 30s)
pytest -m smoke

# All except slow tests
pytest -m "not slow"
```

### By Interface

```bash
# CLI tests
pytest -m cli

# TUI tests
pytest -m tui

# GUI tests
pytest -m gui
```

### With Coverage

```bash
# Basic coverage
pytest --cov=sologit

# Coverage with missing lines
pytest --cov=sologit --cov-report=term-missing

# HTML coverage report
pytest --cov=sologit --cov-report=html
open htmlcov/index.html

# Fail if coverage below 85%
pytest --cov=sologit --cov-fail-under=85
```

### Parallel Execution

```bash
# Run tests in parallel (faster)
pytest -n auto

# Run on 4 cores
pytest -n 4
```

### Advanced Options

```bash
# Show slowest tests
pytest --durations=10

# Verbose with full output
pytest -vv

# Show local variables on failure
pytest -l

# Drop into debugger on failure
pytest --pdb

# Rerun failed tests up to 3 times
pytest --reruns 3
```

## ✍️ Writing Tests

### Test Structure

```python
"""
Test module for [component].

Tests cover:
- [Feature 1]
- [Feature 2]
- [Edge cases]
"""

import pytest
from tests.utils import assert_repo_exists, create_test_repo


@pytest.mark.unit
def test_function_name(fixture_name):
    """Test that function does what it should.
    
    Given: [preconditions]
    When: [action]
    Then: [expected result]
    """
    # Arrange
    input_data = "test"
    
    # Act
    result = function_under_test(input_data)
    
    # Assert
    assert result == expected_value
```

### Using Fixtures

Common fixtures from `conftest.py`:

```python
def test_with_temp_dir(temp_dir):
    """Use temporary directory."""
    test_file = temp_dir / "test.txt"
    test_file.write_text("content")
    assert test_file.exists()


def test_with_git_engine(git_engine, sample_zip):
    """Use GitEngine with sample repository."""
    repo_id = git_engine.init_from_zip(sample_zip, "Test Repo")
    assert_repo_exists(git_engine, repo_id)


def test_with_config(config_manager):
    """Use ConfigManager with test config."""
    value = config_manager.get('test_key')
    assert value is not None
```

### Using Test Utilities

```python
from tests.utils import (
    # Assertions
    assert_repo_exists,
    assert_workpad_exists,
    assert_git_clean,
    
    # Factories
    create_test_repo,
    create_test_workpad,
    create_sample_project,
    
    # Helpers
    wait_for_condition,
    create_file_tree,
    sanitize_output
)


def test_with_utilities(git_engine):
    """Use test utilities."""
    # Create test data
    repo_id = create_test_repo(git_engine, "Test Repo")
    
    # Use custom assertions
    assert_repo_exists(git_engine, repo_id)
    
    # Wait for condition
    wait_for_condition(
        lambda: git_engine.get_repo(repo_id).workpad_count > 0,
        timeout=5.0
    )
```

### Marking Tests

```python
import pytest

@pytest.mark.unit
def test_isolated_function():
    """Fast unit test."""
    pass


@pytest.mark.integration
@pytest.mark.slow
def test_component_interaction():
    """Slower integration test."""
    pass


@pytest.mark.smoke
@pytest.mark.cli
def test_critical_cli_command():
    """Critical smoke test for CLI."""
    pass


@pytest.mark.skipif(not has_api_key(), reason="No API key")
@pytest.mark.ai
def test_ai_feature():
    """Test requiring external API."""
    pass
```

### Testing Exceptions

```python
def test_exception_raised():
    """Test that exception is raised."""
    with pytest.raises(ValueError, match="invalid input"):
        function_that_should_fail("bad input")


def test_exception_not_raised():
    """Test that no exception is raised."""
    try:
        function_that_should_succeed("good input")
    except Exception as e:
        pytest.fail(f"Unexpected exception: {e}")
```

### Async Tests

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    """Test async function."""
    result = await async_function()
    assert result is not None
```

### Parameterized Tests

```python
@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_multiply_by_two(input, expected):
    """Test multiplication with multiple inputs."""
    assert multiply_by_two(input) == expected
```

## 🛠️ Test Infrastructure

### Shared Fixtures (`conftest.py`)

The `conftest.py` file provides shared fixtures:

- **Directory fixtures**: `temp_dir`, `data_dir`, `config_dir`
- **Sample data**: `sample_zip`, `sample_zip_with_tests`, `sample_python_code`
- **Core engines**: `git_engine`, `state_manager`, `config_manager`
- **Mocks**: `mock_ai_client`, `mock_cost_guard`
- **Repository setup**: `initialized_repo`, `repo_with_workpad`, `repo_with_changes`
- **CLI testing**: `cli_runner`, `isolated_cli_env`

### Test Utilities (`tests/utils/`)

Three utility modules:

1. **`assertions.py`** - Custom assertions with better error messages
2. **`factories.py`** - Factory functions to create test objects
3. **`helpers.py`** - Helper functions and context managers

### Pytest Markers

See `MARKERS.md` for complete list. Common markers:

- `@pytest.mark.smoke` - Critical fast tests
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.e2e` - End-to-end tests
- `@pytest.mark.slow` - Tests taking > 1 second
- `@pytest.mark.cli/tui/gui` - Interface-specific tests
- `@pytest.mark.ai` - Tests requiring AI API

### Configuration Files

- **`pytest.ini`** - Pytest configuration
- **`.coveragerc`** - Coverage configuration
- **`.pre-commit-config.yaml`** - Pre-commit hooks
- **`scripts/preflight/`** - Self-test suite

## 🔄 CI/CD Integration

### GitHub Actions

Tests run automatically on:
- Push to main/develop branches
- Pull requests
- Nightly (scheduled at 2 AM UTC)

Workflow stages:
1. **Smoke tests** (< 30s) - Fast critical path validation
2. **Preflight tests** (< 60s) - Feature validation
3. **Unit tests** - Python 3.9-3.12
4. **Integration tests** - Component interaction
5. **CLI tests** - Multi-platform
6. **E2E tests** - Complete workflows
7. **Full coverage** - Main branch only

### Pre-commit Hooks

Install hooks:
```bash
./scripts/setup_hooks.sh
```

Hooks run:
- Code formatting (Black, isort)
- Linting (Ruff)
- Type checking (mypy)
- Smoke tests (on push)

### Coverage Reporting

Coverage reports upload to Codecov:
- View at: https://codecov.io/gh/ssdajoker/Solo-Git
- Badges show current coverage
- PR comments show coverage changes

## ✅ Best Practices

### DO ✅

1. **Write tests first (TDD)**
   ```python
   # Write failing test
   def test_new_feature():
       assert new_feature() == expected
   
   # Implement feature
   # Watch test pass
   ```

2. **Test behavior, not implementation**
   ```python
   # Good
   def test_user_login_succeeds():
       result = login(username, password)
       assert result.success is True
   
   # Bad
   def test_user_login_calls_database():
       login(username, password)
       assert mock_db.query.called
   ```

3. **Use descriptive names**
   ```python
   def test_workpad_promotion_fails_when_tests_are_failing():
       pass  # Clear what's being tested
   ```

4. **Arrange-Act-Assert pattern**
   ```python
   def test_example():
       # Arrange
       setup_data()
       
       # Act
       result = function_under_test()
       
       # Assert
       assert result == expected
   ```

5. **Use appropriate fixtures**
   ```python
   def test_with_fixture(git_engine, sample_zip):
       # Fixtures handle setup/teardown
       pass
   ```

### DON'T ❌

1. **Don't test implementation details**
   ```python
   # Bad - too coupled to implementation
   def test_internal_cache_updated():
       obj._cache['key'] = 'value'
       assert obj._cache['key'] == 'value'
   ```

2. **Don't write flaky tests**
   ```python
   # Bad - depends on timing
   def test_async_operation():
       start_operation()
       time.sleep(1)  # Race condition!
       assert operation_complete()
   ```

3. **Don't skip tests without reason**
   ```python
   # Bad
   @pytest.mark.skip
   def test_broken_feature():
       pass
   
   # Good
   @pytest.mark.skip(reason="Feature not implemented yet - issue #123")
   def test_future_feature():
       pass
   ```

4. **Don't use print for debugging**
   ```python
   # Bad
   def test_example():
       print(f"result: {result}")  # Use logging or pytest -s
       assert result == expected
   ```

5. **Don't make tests depend on each other**
   ```python
   # Bad - test order matters
   def test_create_user():
       global user
       user = create_user()
   
   def test_update_user():
       update_user(user)  # Depends on previous test
   ```

## 🐛 Troubleshooting

### Tests Failing

```bash
# Run with verbose output
pytest -vv

# Show local variables on failure
pytest -l

# Drop into debugger
pytest --pdb

# Run only failed tests
pytest --lf
```

### Tests Hanging

```bash
# Show slow tests
pytest --durations=10

# Add timeout (requires pytest-timeout)
pytest --timeout=30

# Run specific test with verbose
pytest tests/test_slow.py -v
```

### Import Errors

```bash
# Reinstall in editable mode
pip install -e ".[dev]"

# Check Python path
python -c "import sys; print(sys.path)"

# Verify package installed
pip list | grep solo-git
```

### Coverage Not Updating

```bash
# Clean old coverage data
rm -f .coverage .coverage.*
rm -rf htmlcov/

# Run fresh
pytest --cov=sologit --cov-report=html
```

### Flaky Tests

```bash
# Run test multiple times
pytest --count=10 tests/test_flaky.py

# Use pytest-flakefinder
pytest --flake-finder --flake-runs=10
```

### CI Failures

```bash
# Run tests like CI does
pytest -m "smoke" -v --tb=short

# Check specific Python version
pytest --python-version=3.9
```

## 📚 Additional Resources

- **[MARKERS.md](MARKERS.md)** - Pytest marker reference
- **[COVERAGE.md](COVERAGE.md)** - Coverage guide
- **[scripts/preflight/README.md](../scripts/preflight/README.md)** - Preflight tests
- **[docs/TESTING_GUIDE.md](../docs/TESTING_GUIDE.md)** - Comprehensive testing guide

## 🤝 Contributing

When adding new tests:

1. ✅ Place in appropriate directory/file
2. ✅ Use descriptive names
3. ✅ Add appropriate markers
4. ✅ Use shared fixtures when possible
5. ✅ Update coverage to maintain ≥ 85%
6. ✅ Ensure tests pass locally
7. ✅ Run pre-commit hooks

```bash
# Before committing
pytest -m smoke
pytest --cov=sologit --cov-fail-under=85
pre-commit run --all-files
```

## 📊 Test Metrics

Current metrics (check `pytest --cov=sologit`):

- **Total Tests**: 845+
- **Coverage**: ≥ 85% target
- **Smoke Tests**: < 30 seconds
- **Full Suite**: < 5 minutes (without slow tests)
- **Nightly Suite**: < 30 minutes (all tests)

## 🎯 Coverage Goals

| Module | Target | Current |
|--------|--------|---------|
| Core Engines | ≥ 90% | TBD |
| CLI | ≥ 90% | TBD |
| Orchestration | ≥ 85% | TBD |
| UI | ≥ 85% | TBD |
| **Overall** | **≥ 85%** | **TBD** |

Run `pytest --cov=sologit` to see current coverage.

---

*For questions or issues, see [docs/TESTING_GUIDE.md](../docs/TESTING_GUIDE.md) or open an issue.*

**Happy Testing! 🧪**
