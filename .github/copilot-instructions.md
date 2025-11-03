# GitHub Copilot Instructions for Solo-Git

**Project**: Solo-Git - AI-assisted Git workflow manager  
**Version**: 1.0.0  
**Last Updated**: November 3, 2025

---

## Project Overview

Solo-Git is a Git workflow management tool that eliminates branching complexity through ephemeral "workpads" and provides AI-assisted development features. The system uses **Abacus.AI as the primary AI provider** with intelligent fallback routing to OpenAI and Anthropic.

### Core Architecture

- **Frontend**: Heaven GUI (Tauri + React + TypeScript + Tailwind CSS)
- **Backend**: Python 3.9+ with async/await patterns
- **AI Routing**: Abacus-first architecture with intelligent fallback chain
- **State Management**: JSON-based persistent state with bidirectional Git sync
- **Testing**: Pytest with 90%+ coverage target

### "Triangle Offense" Development Methodology

1. **Understand** - Read existing code patterns before writing new code
2. **Align** - Match existing conventions and architectural patterns
3. **Test** - Write tests alongside implementation (test-driven)

---

## 1. Python Coding Standards

### File Organization

```
sologit/
├── cli/              # CLI commands and main entry point
├── ui/               # TUI and formatters (Rich, Textual)
├── state/            # State management and persistence
├── config/           # Configuration management
├── api/              # External API clients (Abacus.AI)
├── core/             # Domain models (Repository, Workpad)
├── engines/          # Execution engines (Git, Patch, Test)
├── orchestration/    # AI orchestration and routing
│   └── providers/    # AI provider adapters
├── analysis/         # Test analysis
├── workflows/        # Automated workflows
└── utils/            # Shared utilities
```

### Code Conventions

#### 1. Imports
```python
"""Module docstring explaining purpose."""
import asyncio
import time
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path

from sologit.config.manager import ConfigManager
from sologit.utils.logger import get_logger

logger = get_logger(__name__)
```

- **Order**: stdlib → third-party → local
- **Grouping**: Separate groups with blank lines
- Always use absolute imports from `sologit.`
- Use `get_logger(__name__)` for module-level logging

#### 2. Data Classes
```python
@dataclass
class CommitMessageRequest:
    """Request for generating a commit message."""
    diff: str
    workpad_title: str
    conventional_commit: bool = True
    max_length: int = 72
    metadata: Dict[str, Any] = field(default_factory=dict)
```

- Use `@dataclass` for data structures
- Include docstrings
- Use `field(default_factory=...)` for mutable defaults
- Type all fields

#### 3. Async Patterns
```python
async def generate(
    self,
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
) -> ProviderResponse:
    """Generate response using AI provider."""
    start_time = time.time()
    
    try:
        response = await asyncio.to_thread(
            self.client.chat,
            messages=[...],
            temperature=temperature,
        )
        
        latency_ms = (time.time() - start_time) * 1000
        return ProviderResponse(...)
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        raise
```

- Use `async def` for I/O-bound operations
- Use `asyncio.to_thread()` for blocking calls
- Always track latency for AI operations
- Include comprehensive error handling

#### 4. Error Handling
```python
class GitEngineError(Exception):
    """Base exception for Git engine errors."""
    pass

class WorkpadNotFoundError(GitEngineError):
    """Raised when workpad does not exist."""
    pass

# Usage
try:
    result = git_engine.promote_workpad(workpad_id)
except WorkpadNotFoundError as e:
    logger.error(f"Workpad not found: {e}")
    return ErrorResponse(
        error="workpad_not_found",
        message=f"Workpad '{workpad_id}' does not exist",
        details={"workpad_id": workpad_id}
    )
```

- Create specific exception classes
- Use descriptive error messages
- Return uniform error responses (error/message/details structure)
- Log errors with context

#### 5. CLI Patterns
```python
@click.command()
@click.option('--json', 'json_output', is_flag=True, help='Output as JSON')
@click.option('--workpad', '-w', required=True, help='Workpad ID')
def commit_msg(workpad: str, json_output: bool) -> None:
    """Generate AI-assisted commit message."""
    try:
        result = generate_commit_message(workpad)
        
        if json_output:
            click.echo(json.dumps({
                "message": result.message,
                "provider": result.provider.value,
                "model": result.model,
                "cost_usd": result.cost_usd,
            }))
        else:
            formatter.print_success("Commit Message Generated", result.message)
    except Exception as e:
        if json_output:
            click.echo(json.dumps({"error": str(e)}))
            sys.exit(1)
        else:
            abort_with_error("Generation failed", str(e))
```

- Support `--json` flag for all commands that output data
- Use `click.option()` with short flags (e.g., `-w`)
- Use `formatter` for rich console output
- Handle both JSON and human-readable output modes

---

## 2. AI Provider Patterns

### Abacus-First Architecture

**CRITICAL**: Abacus.AI is the PRIMARY provider. All AI operations must route through Abacus first.

```python
# Default fallback chain (NEVER change this order without discussion)
fallback_chain: List[ProviderType] = [
    ProviderType.ABACUS,    # PRIMARY
    ProviderType.OPENAI,    # Fallback #1
    ProviderType.ANTHROPIC, # Fallback #2
]
```

### Provider Adapter Interface

All AI providers must implement the `ProviderAdapter` interface:

```python
class MyAdapter(ProviderAdapter):
    """Provider adapter following standard interface."""
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.client = MyClient(api_key=config.api_key)
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> ProviderResponse:
        """Generate response."""
        # Track start time for latency
        start_time = time.time()
        
        # Make API call
        response = await self._call_api(...)
        
        # Calculate metrics
        latency_ms = (time.time() - start_time) * 1000
        
        return ProviderResponse(
            content=response.content,
            provider=self.provider_type,
            model=response.model,
            tokens_used=response.total_tokens,
            latency_ms=latency_ms,
            cost_usd=self._estimate_cost(response.total_tokens),
        )
    
    def is_available(self) -> bool:
        """Check if provider is available."""
        return self.config.enabled and self.config.api_key is not None
    
    def get_default_model(self) -> str:
        """Get default model name."""
        return self.config.default_model
```

### Routing and Fallback

```python
# Use PolicyEngine for provider selection
policy = RoutingPolicy(
    strategy=RoutingStrategy.ABACUS_FIRST,
    fallback_chain=[ProviderType.ABACUS, ProviderType.OPENAI, ProviderType.ANTHROPIC],
    max_retries=2,
)
engine = PolicyEngine(policy, adapters)

# Select provider with fallback chain
primary, fallbacks = engine.select_provider()

# Try primary, fallback on failure
for attempt, provider in enumerate([primary] + fallbacks):
    try:
        response = await provider.generate(prompt)
        break
    except Exception as e:
        if engine.should_fallback(e, attempt):
            logger.warning(f"Provider {provider.provider_type} failed, trying fallback")
            continue
        raise
```

---

## 3. TypeScript/React Coding Standards

### File Organization

```
heaven-gui/src/
├── components/       # React components
├── hooks/           # Custom hooks
├── types/           # TypeScript type definitions
├── pages/           # Page components
├── utils/           # Utility functions
├── config/          # Configuration
└── styles/          # CSS and Tailwind
```

### Code Conventions

#### 1. Component Structure
```typescript
import { useState, useCallback, useEffect } from 'react'
import { invoke } from '@tauri-apps/api/tauri'
import type { WorkpadState, CommitMessageResponse } from '../types/soloGit'

interface WorkpadCardProps {
  workpad: WorkpadState
  onSelect: (id: string) => void
  onDelete: (id: string) => Promise<void>
}

export default function WorkpadCard({ workpad, onSelect, onDelete }: WorkpadCardProps) {
  const [loading, setLoading] = useState(false)
  
  const handleDelete = useCallback(async () => {
    try {
      setLoading(true)
      await onDelete(workpad.id)
    } catch (error) {
      console.error('Failed to delete workpad:', error)
    } finally {
      setLoading(false)
    }
  }, [workpad.id, onDelete])
  
  return (
    <div className="workpad-card">
      <h3>{workpad.title}</h3>
      <button onClick={handleDelete} disabled={loading}>
        Delete
      </button>
    </div>
  )
}
```

- Use functional components with hooks
- Use `useCallback` for event handlers
- Type all props with interfaces
- Handle loading and error states
- Use Tailwind CSS classes

#### 2. Custom Hooks Pattern
```typescript
import { useCallback } from 'react'
import { invoke } from '@tauri-apps/api/tauri'
import type { CommitMessageResponse } from '../types/soloGit'

interface UseSoloGitOperationsOptions {
  onStateUpdated?: () => Promise<void> | void
}

export function useSoloGitOperations({ onStateUpdated }: UseSoloGitOperationsOptions = {}) {
  const generateCommitMessage = useCallback(async (workpadId: string) => {
    try {
      const response = await invoke<CommitMessageResponse>('generate_commit_message', {
        workpad_id: workpadId,
      })
      
      if (onStateUpdated) {
        await onStateUpdated()
      }
      
      return response
    } catch (error) {
      throw toError(error)
    }
  }, [onStateUpdated])
  
  return {
    generateCommitMessage,
  }
}

const toError = (error: unknown): Error => {
  if (error instanceof Error) return error
  if (typeof error === 'string') return new Error(error)
  return new Error(JSON.stringify(error))
}
```

- Use `useCallback` for functions that may be dependencies
- Call `onStateUpdated` after mutations
- Convert Tauri errors to Error objects
- Type Tauri invoke calls

#### 3. Toast Notifications
```typescript
const addNotification = useCallback((
  message: string,
  type: 'success' | 'error' | 'warning' | 'info' = 'info'
) => {
  const notification: Notification = {
    id: Date.now().toString(),
    type,
    message,
    duration: 5000,
  }
  setNotifications(prev => [...prev, notification])
}, [])

// Usage
try {
  await createWorkpad({ repoId, title })
  addNotification('Workpad created successfully', 'success')
} catch (error) {
  addNotification(`Failed to create workpad: ${getErrorMessage(error)}`, 'error')
}
```

- Use toast notifications for user feedback
- Success on operations complete
- Error with descriptive messages
- Warning for non-critical issues
- Info for status updates

#### 4. Type Definitions
```typescript
// types/soloGit.ts

export interface WorkpadState {
  id: string
  title: string
  created_at: string
  status: 'active' | 'completed' | 'failed'
  test_results?: TestResult[]
  ai_metadata?: AIMetadata
}

export interface CommitMessageResponse {
  message: string
  provider: string
  model: string
  cost_usd: number
  latency_ms: number
  fallback_used: boolean
}

export interface TestResult {
  id: string
  status: 'passed' | 'failed' | 'skipped'
  duration_ms: number
  error?: string
}
```

- Define all backend types in `types/soloGit.ts`
- Use exact backend field names (snake_case)
- Mark optional fields with `?`
- Use union types for enums

---

## 4. Testing Standards

### Test File Organization

```
tests/
├── test_git_engine.py              # Engine tests
├── test_commit_message_generator.py # AI orchestration tests
├── test_model_router.py            # Routing tests
├── test_provider_adapters.py       # Provider tests
└── test_cli_commands.py            # CLI tests
```

- Test files mirror source structure
- Name: `test_<module_name>.py`
- Group tests by functionality

### Test Patterns

#### 1. Basic Test Structure
```python
"""Tests for commit message generator."""
import pytest
from unittest.mock import Mock, AsyncMock, patch

from sologit.orchestration.commit_message_generator import (
    CommitMessageGenerator,
    CommitMessageRequest,
)

class TestCommitMessageGenerator:
    """Test commit message generator."""
    
    @pytest.mark.asyncio
    async def test_generate_with_primary_provider(self):
        """Test successful generation with primary provider."""
        # Arrange
        generator = create_test_generator()
        request = CommitMessageRequest(
            diff="+ Added feature\n- Removed code",
            workpad_title="feature-branch",
        )
        
        # Act
        response = await generator.generate(request)
        
        # Assert
        assert response.provider == ProviderType.ABACUS
        assert response.fallback_used is False
        assert "feat:" in response.message
```

- Use pytest class organization
- Descriptive test method names
- Arrange-Act-Assert pattern
- Use `@pytest.mark.asyncio` for async tests

#### 2. Mocking Patterns
```python
class MockAdapter(ProviderAdapter):
    """Mock adapter for testing."""
    
    def __init__(self, config: ProviderConfig, should_fail: bool = False):
        super().__init__(config)
        self._should_fail = should_fail
    
    async def generate(self, prompt, **kwargs):
        if self._should_fail:
            raise Exception("Provider failed")
        
        return ProviderResponse(
            content="test response",
            provider=self.provider_type,
            model="test-model",
            tokens_used=10,
            latency_ms=100.0,
            cost_usd=0.01,
        )
```

- Create mock classes for complex interfaces
- Support failure scenarios with flags
- Return realistic test data

#### 3. Coverage Requirements
- **Target**: 90%+ overall coverage
- **Critical paths**: 100% coverage (AI routing, state management, Git operations)
- **Every PR**: Must maintain or improve coverage
- **Test types**: Unit, integration, edge cases

```bash
# Run tests with coverage
pytest --cov=sologit --cov-report=html --cov-report=term

# Check coverage
pytest --cov=sologit --cov-fail-under=90
```

---

## 5. Error Handling Patterns

### Uniform Error Response Structure

All errors should follow this structure:

```python
@dataclass
class ErrorResponse:
    """Standardized error response."""
    error: str          # Machine-readable error code
    message: str        # Human-readable message
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
```

### CLI Error Handling

```python
def abort_with_error(
    message: str,
    details: Optional[str] = None,
    *,
    help_text: Optional[str] = None,
    suggestions: Optional[List[str]] = None,
) -> None:
    """Display formatted error and abort."""
    formatter.print_error(
        "Command Error",
        message,
        help_text=help_text or "Use --help for more information",
        suggestions=suggestions or ["Check command syntax", "Verify repository state"],
        details=details,
    )
    raise click.Abort()

# Usage
try:
    result = perform_operation()
except WorkpadNotFoundError as e:
    abort_with_error(
        f"Workpad '{workpad_id}' not found",
        help_text="List available workpads with: sologit workpad list",
        suggestions=["Check workpad ID spelling", "Create workpad first"],
    )
```

### GUI Error Handling

```typescript
const handleOperation = async () => {
  try {
    await performOperation()
    addNotification('Operation completed', 'success')
  } catch (error) {
    const message = getErrorMessage(error)
    console.error('Operation failed:', error)
    addNotification(`Operation failed: ${message}`, 'error')
  }
}

const getErrorMessage = (error: unknown): string => {
  if (error instanceof Error) return error.message
  if (typeof error === 'string') return error
  try {
    return JSON.stringify(error)
  } catch {
    return 'Unknown error'
  }
}
```

---

## 6. Documentation Standards

### Python Docstrings

Use Google-style docstrings:

```python
def promote_workpad(
    self,
    workpad_id: str,
    run_tests: bool = True,
    force: bool = False,
) -> PromotionResult:
    """
    Promote workpad changes to trunk (fast-forward only).
    
    This operation applies the workpad's changes to the main branch
    using a fast-forward merge. If tests fail or promotion rules
    are violated, the operation is aborted.
    
    Args:
        workpad_id: Unique workpad identifier
        run_tests: Whether to run tests before promotion
        force: Skip promotion rules (dangerous!)
    
    Returns:
        PromotionResult with status and metadata
    
    Raises:
        WorkpadNotFoundError: Workpad does not exist
        PromotionRulesError: Promotion rules violated
        TestFailureError: Tests failed
    
    Example:
        >>> result = git_engine.promote_workpad("feat-123")
        >>> if result.success:
        ...     print(f"Promoted in {result.duration_ms}ms")
    """
```

### TypeScript Documentation

```typescript
/**
 * Generate AI-assisted commit message for a workpad.
 * 
 * Uses the Abacus-first routing strategy to generate a conventional
 * commit message based on the workpad's diff and metadata.
 * 
 * @param workpadId - Unique workpad identifier
 * @returns Promise resolving to commit message response
 * @throws Error if workpad not found or generation fails
 * 
 * @example
 * const response = await generateCommitMessage('feat-123')
 * console.log(`Message: ${response.message}`)
 * console.log(`Provider: ${response.provider}`)
 */
async function generateCommitMessage(workpadId: string): Promise<CommitMessageResponse> {
  // ...
}
```

### README and Guides

- Keep README.md updated with new features
- Update CHANGELOG.md for every release
- Document breaking changes prominently
- Include examples for complex features

---

## 7. Git and Version Control

### Commit Message Format

Use Conventional Commits:

```
feat: add AI-assisted commit message generation

- Implement Abacus-first routing strategy
- Add fallback to OpenAI and Anthropic
- Include cost tracking and latency metrics

Closes #123
```

Types:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation only
- `style:` - Code style (formatting, no logic change)
- `refactor:` - Code restructuring (no behavior change)
- `test:` - Add or update tests
- `chore:` - Maintenance tasks

### Branch Naming

For repository development (not user-facing workpads):

- `feat/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation updates
- `refactor/description` - Code refactoring

---

## 8. Key Files Reference

### Backend Entry Points

- `sologit/cli/main.py` - CLI entry point
- `sologit/cli/commands.py` - Core CLI commands
- `sologit/state/manager.py` - State management
- `sologit/orchestration/commit_message_generator.py` - AI commit messages
- `sologit/orchestration/model_router.py` - AI routing logic
- `sologit/orchestration/providers/abacus_adapter.py` - Abacus.AI provider

### Frontend Entry Points

- `heaven-gui/src/App.tsx` - Main application
- `heaven-gui/src/hooks/useSoloGitOperations.ts` - Operations hook
- `heaven-gui/src/types/soloGit.ts` - Type definitions
- `heaven-gui/src/components/` - React components

### Configuration

- `requirements.txt` - Python dependencies
- `setup.py` - Package configuration
- `pytest.ini` - Test configuration
- `heaven-gui/package.json` - Frontend dependencies
- `heaven-gui/tsconfig.json` - TypeScript configuration

---

## 9. Development Workflow

### Before Writing Code

1. **Search** for existing implementations:
   ```bash
   grep -r "similar_function" sologit/
   ```

2. **Read** relevant files to understand patterns

3. **Check** tests to understand expected behavior

### Writing New Code

1. **Match** existing patterns (imports, structure, naming)
2. **Type** everything (Python type hints, TypeScript types)
3. **Document** with docstrings/comments
4. **Test** alongside implementation (TDD preferred)

### After Writing Code

1. **Run tests**:
   ```bash
   pytest tests/ -v
   pytest --cov=sologit --cov-report=term
   ```

2. **Check formatting**:
   ```bash
   # Python (if using black/ruff)
   black sologit/
   
   # TypeScript
   cd heaven-gui && npm run lint
   ```

3. **Update docs** if adding new features

4. **Test manually** in both CLI and GUI

---

## 10. Common Patterns Quick Reference

### Async Function with Error Handling

```python
async def operation(self, param: str) -> Result:
    """Perform operation."""
    start_time = time.time()
    logger.info(f"Starting operation: {param}")
    
    try:
        result = await self._execute(param)
        latency_ms = (time.time() - start_time) * 1000
        logger.info(f"Operation completed in {latency_ms:.2f}ms")
        return result
    except SpecificError as e:
        logger.error(f"Operation failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise OperationError(f"Failed to perform operation: {e}") from e
```

### React Component with Tauri Invoke

```typescript
const [data, setData] = useState<DataType | null>(null)
const [loading, setLoading] = useState(false)
const [error, setError] = useState<string | null>(null)

const loadData = useCallback(async () => {
  try {
    setLoading(true)
    setError(null)
    const result = await invoke<DataType>('command_name', { param })
    setData(result)
  } catch (err) {
    setError(getErrorMessage(err))
  } finally {
    setLoading(false)
  }
}, [param])

useEffect(() => {
  void loadData()
}, [loadData])
```

### CLI Command with JSON Output

```python
@click.command()
@click.option('--json', is_flag=True)
@click.argument('workpad_id')
def info(workpad_id: str, json: bool) -> None:
    """Show workpad information."""
    try:
        data = get_workpad_info(workpad_id)
        
        if json:
            click.echo(json.dumps(data.to_dict()))
        else:
            formatter.print_info("Workpad Info", data.title)
            formatter.print_key_value("Status", data.status)
            formatter.print_key_value("Created", data.created_at)
    except Exception as e:
        if json:
            click.echo(json.dumps({"error": str(e)}))
            sys.exit(1)
        else:
            abort_with_error("Failed to get workpad info", str(e))
```

---

## 11. Critical Reminders

### ⚠️ ALWAYS

- Use Abacus.AI as PRIMARY AI provider
- Maintain 90%+ test coverage
- Type all function parameters and returns
- Handle errors gracefully with user-friendly messages
- Add docstrings to all public functions
- Use `get_logger(__name__)` for logging
- Follow existing patterns in the codebase
- Test both success and failure cases
- Update state after mutations in GUI
- Show toast notifications for user operations

### ⚠️ NEVER

- Change AI provider fallback order without discussion
- Skip error handling for external API calls
- Use mutable default arguments (use `field(default_factory=...)`)
- Commit code without tests
- Use `print()` for logging (use `logger`)
- Hardcode API keys or secrets
- Break backward compatibility without version bump
- Merge branches (Solo-Git uses fast-forward only)
- Ignore type hints or TypeScript errors

---

## 12. Getting Help

### Documentation

- **Architecture**: `ARCHITECTURE.md`
- **Features**: `FEATURES.md`
- **Project Structure**: `PROJECT_STRUCTURE.md`
- **Installation**: `INSTALL.md`
- **Quick Start**: `QUICKSTART.md`

### Code Examples

- **AI Routing**: `sologit/orchestration/commit_message_generator.py`
- **React Hooks**: `heaven-gui/src/hooks/useSoloGitOperations.ts`
- **CLI Commands**: `sologit/cli/commands.py`
- **Tests**: `tests/test_commit_message_generator.py`

### Debugging

- Enable verbose logging: `export SOLOGIT_LOG_LEVEL=DEBUG`
- Check state: `cat .sologit/state.json | jq`
- View test coverage: `open htmlcov/index.html`

---

**Remember**: When in doubt, search for existing patterns in the codebase. Consistency is key to maintainability!
