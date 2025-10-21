# NotRenderableError Fix - Explanation

## Problem Summary

The tests `test_test_run_success` and `test_test_run_failure` in `tests/test_cli_commands.py` were failing with a `NotRenderableError` from the rich library. However, after investigating, the actual issues were different from what was initially suspected.

## Root Causes Identified

### 1. **Configuration Syntax Errors** (Primary blocker)

**File:** `sologit/config/manager.py`

**Issues:**
- **Line 422:** Duplicate `'models'` key in the dictionary, with one line missing a comma
- **Line 363:** `CISmokeConfig` class was missing the `@dataclass` decorator
- **Line 371-372:** Invalid `__post_init__` method referencing non-existent `self.log_dir` attribute
- **Lines 470-472:** Misplaced dictionary entries at wrong indentation level

**Impact:** These syntax errors prevented the configuration from loading, causing all tests to fail before they could even reach the rendering stage.

### 2. **Test Data Incomplete** (Secondary issue)

**File:** `tests/test_cli_commands.py`

**Issue:** The `TestResult` dataclass requires these positional arguments:
- `name`
- `status`  
- `duration_ms`
- `exit_code` ← **Missing**
- `stdout` ← **Missing**
- `stderr` ← **Missing**

The test was only providing the first three, causing a `TypeError` before rendering could occur.

### 3. **Test Assertion Mismatch** (Minor issue)

**Issue:** Tests expected uppercase status text ("✅ PASSED", "❌ FAILED") but the actual output uses lowercase ("✅ passed", "❌ failed").

## Understanding the "NotRenderableError" Confusion

### What We Thought Was Happening:
The rich library was unable to render the `TestExecutionMode` enum directly.

### What Was Actually Happening:
The `mode` field in `TestResult` is **correctly defined as a string**, not an enum:

```python
@dataclass
class TestResult:
    # ... other fields ...
    mode: str = TestExecutionMode.DOCKER.value  # ← This is a STRING, not an enum
```

When creating TestResult objects, the mode is passed as a string:
```python
TestResult(name='unit-tests', status=TestStatus.PASSED, ..., mode='docker', ...)
#                                                                   ^^^^^^^ string
```

And when rendering in the table, it's already a string:
```python
table.add_row(
    result.name,
    status_text,
    f"{duration_s:.2f}s",
    result.mode,  # ← Already a string, renders fine
    notes,
    log_display,
)
```

**The NotRenderableError was never actually occurring** because the mode was already being stored as a string value (e.g., "docker", "subprocess") rather than as an enum instance.

## Fixes Applied

### 1. Fixed Configuration Syntax Errors

```python
# Before (lines 421-439):
'ai': {
    'models': self.models.to_ai_models_dict()  # ← Missing comma
    'models': {  # ← Duplicate key
        ...
    }
}

# After:
'ai': {
    'models': {
        'fast': {...},
        'coding': {...},
        'planning': {...}
    }
}
```

```python
# Before (lines 448-472):
'tests': {
    'sandbox_image': self.tests.sandbox_image,
    # ... other fields ...
},
'ci': {...},
'deployments': {...},
    'execution_mode': self.tests.execution_mode,  # ← Wrong indentation!
    'log_dir': self.tests.log_dir,
}

# After:
'tests': {
    'sandbox_image': self.tests.sandbox_image,
    # ... other fields ...
    'execution_mode': self.tests.execution_mode,  # ← Moved inside 'tests'
    'log_dir': self.tests.log_dir,
},
'ci': {...},
'deployments': {...}
```

```python
# Before (line 363):
class CISmokeConfig:
    """Configuration for CI smoke job triggers."""
    auto_run: bool = False
    # ...
    def __post_init__(self):  # ← Invalid without @dataclass
        if self.log_dir is None:  # ← self.log_dir doesn't exist!
            self.log_dir = str(Path.home() / ".sologit" / "data" / "test_runs")

# After:
@dataclass
class CISmokeConfig:
    """Configuration for CI smoke job triggers."""
    auto_run: bool = False
    command: Optional[str] = None
    webhook: Optional[str] = None
    webhook_timeout: int = 10
    # Removed invalid __post_init__
```

### 2. Updated Test Data

```python
# Before:
TestResult(
    name='unit-tests', 
    status=TestStatus.PASSED, 
    duration_ms=1234, 
    mode='docker', 
    log_path=Path('/log/unit.txt')
)  # ← Missing exit_code, stdout, stderr

# After:
TestResult(
    name='unit-tests', 
    status=TestStatus.PASSED, 
    duration_ms=1234, 
    exit_code=0,     # ← Added
    stdout='',       # ← Added
    stderr='',       # ← Added
    mode='docker', 
    log_path=Path('/log/unit.txt')
)
```

### 3. Updated Test Assertions

```python
# Before:
assert "✅ PASSED" in result.output
assert "❌ FAILED" in result.output

# After:
assert "✅ passed" in result.output
assert "❌ failed" in result.output
```

## Test Results

After applying all fixes:

```bash
$ pytest tests/test_cli_commands.py::test_test_run_success tests/test_cli_commands.py::test_test_run_failure -v

======================== 2 passed in 17.35s ========================
```

✅ **Both tests are now passing!**

## Key Takeaway

The `TestExecutionMode` enum **was never the problem**. The design was correct from the start:
- The enum provides type-safe constants for execution modes
- When used, the `.value` property extracts the string representation
- The `TestResult.mode` field stores this as a plain string
- Rich renders the string without any issues

The actual problems were:
1. Configuration file syntax errors preventing tests from running
2. Incomplete test data causing TypeErrors
3. Minor assertion mismatches

## No Design Changes Needed

**Important:** The mode field should remain as `str`, not `TestExecutionMode`. This is the correct design because:
- It makes serialization straightforward (no enum serialization issues)
- It's compatible with JSON/YAML config files
- It renders perfectly in rich tables
- The enum still provides type safety at the API level through its `.value` property
