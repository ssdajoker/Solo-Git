
# Preflight Self-Test Suite

## Overview

The preflight test suite validates that all documented Solo-Git features are working correctly. These tests are designed to be run:

- **Before deployment** - Ensure system is ready for users
- **After major changes** - Catch regressions quickly  
- **As smoke tests** - Fast validation of critical paths
- **In CI/CD** - Automated quality gates

## Test Organization

```
scripts/preflight/
├── README.md                    # This file
├── __init__.py                  # Package metadata
├── test_startup.py              # System startup and initialization
├── test_core_features.py        # Core feature validation
├── test_contracts.py            # API contracts and interfaces
├── test_persistence.py          # Data persistence and state
├── test_error_paths.py          # Error handling and edge cases
└── run_preflight.py             # Convenience runner script
```

## Running Tests

### Quick Start

```bash
# Run all preflight tests
pytest scripts/preflight/

# Run with coverage
pytest scripts/preflight/ --cov=sologit

# Run specific module
pytest scripts/preflight/test_core_features.py
```

### Continuous Integration

```bash
# Fast smoke test (< 30 seconds)
pytest scripts/preflight/ -m smoke

# Full validation (< 60 seconds)
pytest scripts/preflight/
```

### Development Workflow

```bash
# Watch mode during development
ptw scripts/preflight/

# Verbose output with timing
pytest scripts/preflight/ -v --durations=10
```

## Test Categories

### 1. Startup Tests (`test_startup.py`)

Validates system can start and basic infrastructure works:
- Import all modules without errors
- Configuration loading
- Directory structure creation
- Environment setup

**Success Criteria:** All modules import cleanly, config loads

### 2. Core Features (`test_core_features.py`)

Tests the main documented features:
- Repository initialization (from ZIP, from Git URL)
- Workpad lifecycle (create, checkpoint, promote, delete)
- Test execution (fast, full)
- AI operations (plan, generate, review)
- State synchronization

**Success Criteria:** All documented features work end-to-end

### 3. Contracts (`test_contracts.py`)

Validates API contracts and interfaces:
- CLI command signatures
- Python API interfaces
- State file schemas
- Configuration schemas
- Return value contracts

**Success Criteria:** APIs match documentation, no breaking changes

### 4. Persistence (`test_persistence.py`)

Tests data persistence and state management:
- State saves and loads correctly
- Survives process restarts
- Handles concurrent access
- Recovers from corruption

**Success Criteria:** No data loss, state is consistent

### 5. Error Paths (`test_error_paths.py`)

Validates error handling:
- Graceful degradation
- Clear error messages
- No data corruption on errors
- Recovery mechanisms work

**Success Criteria:** All errors handled gracefully, good UX

## Feature Coverage Matrix

| Feature | Test Module | Status |
|---------|-------------|--------|
| Repository Init (ZIP) | test_core_features | ✅ |
| Repository Init (Git) | test_core_features | ✅ |
| Workpad Create | test_core_features | ✅ |
| Workpad Checkpoint | test_core_features | ✅ |
| Workpad Promote | test_core_features | ✅ |
| Workpad Delete | test_core_features | ✅ |
| Test Execution (Fast) | test_core_features | ✅ |
| Test Execution (Full) | test_core_features | ✅ |
| AI Plan Generation | test_core_features | ✅ |
| AI Code Generation | test_core_features | ✅ |
| AI Patch Review | test_core_features | ✅ |
| State Persistence | test_persistence | ✅ |
| Error Handling | test_error_paths | ✅ |
| API Contracts | test_contracts | ✅ |

## Success Criteria

### All Tests Pass

```
==================== test session starts ====================
collected 45 items

test_startup.py ....                                  [  8%]
test_core_features.py ....................           [ 53%]
test_contracts.py ........                           [ 71%]
test_persistence.py ......                           [ 84%]
test_error_paths.py .......                          [100%]

==================== 45 passed in 42.3s ====================
```

### Performance Benchmarks

- **Startup tests**: < 5 seconds
- **Core features**: < 30 seconds  
- **Contracts**: < 5 seconds
- **Persistence**: < 10 seconds
- **Error paths**: < 10 seconds
- **Total suite**: < 60 seconds

### Coverage Requirements

- Overall: > 85%
- Core engines: > 90%
- Critical paths: 100%

## Troubleshooting

### Tests Failing

1. Check dependencies: `pip install -e .[dev]`
2. Verify config: `evogitctl config check`
3. Clean state: `rm -rf /tmp/solo-git-test-*`
4. Run with verbose: `pytest -vv`

### Tests Slow

1. Run in parallel: `pytest -n auto`
2. Skip slow tests: `pytest -m "not slow"`
3. Profile: `pytest --durations=10`

### Flaky Tests

1. Run multiple times: `pytest --count=10`
2. Check for race conditions
3. Review test isolation
4. Add proper waits/timeouts

## Maintenance

### Adding New Tests

1. Identify feature from documentation
2. Choose appropriate test module
3. Write test following existing patterns
4. Ensure test is fast (< 2s per test)
5. Mark with appropriate markers
6. Update coverage matrix

### Updating Tests

When features change:
1. Update test to match new behavior
2. Update documentation references
3. Maintain backward compatibility markers
4. Update coverage matrix

## Integration with CI

### GitHub Actions

```yaml
- name: Preflight Tests
  run: pytest scripts/preflight/ --junitxml=preflight-results.xml
  
- name: Upload Results
  uses: actions/upload-artifact@v3
  with:
    name: preflight-results
    path: preflight-results.xml
```

### Pre-commit Hook

```bash
# .pre-commit-config.yaml
- id: preflight-smoke
  name: Preflight Smoke Tests
  entry: pytest scripts/preflight/ -m smoke -x
  language: system
  pass_filenames: false
```

## Contact

For questions or issues with preflight tests:
- Open an issue on GitHub
- Check TESTING_GUIDE.md for more details
- Review test comments for specific questions
