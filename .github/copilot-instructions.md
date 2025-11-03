# Solo Git - Copilot Coding Instructions

## Project Overview

Solo Git is a revolutionary version control system designed for solo developers working with AI assistants. It eliminates traditional Git workflow friction (branches, PRs, manual reviews) with an intelligent, test-driven, auto-merging system where **tests are the ultimate arbiter of correctness**.

### Core Architecture

- **Python Backend**: Core CLI/TUI using Python 3.9+ with async/await patterns
- **Tauri GUI**: Desktop app with Rust backend and React/TypeScript frontend
- **AI-First Design**: Multi-model routing with Abacus AI as primary provider
- **Test-Driven**: 90%+ coverage requirement, tests replace code review
- **Workpad-Based**: Ephemeral sandboxes replace branches

## Python Coding Standards

### Type Hints

Always use type hints for function parameters and return values:

```python
from typing import Optional, List, Dict
from datetime import datetime

async def generate_commit_message(
    diff: str,
    context: Optional[str] = None,
    style: str = "conventional"
) -> str:
    """Generate AI-powered commit message.
    
    Args:
        diff: Git diff to generate message from
        context: Optional context about the changes
        style: Commit message style (conventional, semantic, etc.)
        
    Returns:
        Generated commit message
    """
    pass
```

### Async/Await Patterns

Use async for I/O operations and AI provider calls:

```python
async def route_with_fallback(prompt: str, policy: RoutingPolicy) -> AIResponse:
    """Route request with fallback chain."""
    providers = [policy.primary] + policy.fallback
    
    for provider_name in providers:
        try:
            provider = get_provider(provider_name)
            response = await provider.generate(prompt, timeout=policy.timeout)
            logger.info(f"Successfully routed to {provider_name}")
            return response
        except ProviderError as e:
            logger.warning(f"Provider {provider_name} failed: {e}")
            continue
    
    raise AllProvidersFailedError("All AI providers failed")
```

### Dataclasses for Models

Use dataclasses for data models:

```python
from dataclasses import dataclass
from datetime import datetime
from typing import List

@dataclass
class Workpad:
    """Represents a Solo-Git workpad for managing changes."""
    name: str
    base_branch: str
    patches: List['Patch']
    created_at: datetime
    
    def add_patch(self, patch: 'Patch') -> None:
        """Add a patch to the workpad."""
        self.patches.append(patch)
```

### Error Handling

Implement comprehensive error handling with custom exceptions:

```python
class ProviderError(Exception):
    """Base exception for provider errors."""
    
    def __init__(self, provider: str, message: str, original_error: Optional[Exception] = None):
        self.provider = provider
        self.message = message
        self.original_error = original_error
        super().__init__(f"[{provider}] {message}")
```

### Logging

Use structured logging with proper levels:

```python
import logging

logger = logging.getLogger(__name__)

def log_provider_metrics(provider: str, success: bool, latency: float):
    """Log provider performance metrics."""
    metrics = {
        "provider": provider,
        "success": success,
        "latency_ms": latency * 1000,
        "timestamp": datetime.utcnow().isoformat()
    }
    logger.info("Provider metrics", extra=metrics)
```

## TypeScript/React Patterns

### Component Structure

Use functional components with TypeScript interfaces:

```typescript
interface CommitPanelProps {
  workpadId: string;
  onCommitSuccess: () => void;
}

const CommitPanel: React.FC<CommitPanelProps> = ({ workpadId, onCommitSuccess }) => {
  const { generateCommitMessage } = useSoloGitOperations();
  
  const handleGenerateMessage = async () => {
    try {
      const diff = await getDiff(workpadId);
      const message = await generateCommitMessage(diff);
      toast.success('Commit message generated successfully');
      setCommitMessage(message);
    } catch (error) {
      toast.error(`Failed to generate commit message: ${error.message}`);
      console.error('Commit message generation error:', error);
    }
  };
  
  return <div>{/* Component JSX */}</div>;
};
```

### Custom Hooks Pattern

Create custom hooks for Solo-Git operations:

```typescript
export const useSoloGitOperations = () => {
  const generateCommitMessage = async (diff: string): Promise<string> => {
    return await invoke('generate_commit_message', { diff });
  };
  
  const createWorkpad = async (name: string): Promise<Workpad> => {
    return await invoke('create_workpad', { name });
  };
  
  return { generateCommitMessage, createWorkpad };
};
```

### Tauri Commands

Define Tauri commands for backend communication:

```rust
#[tauri::command]
async fn generate_commit_message(diff: String) -> Result<String, String> {
    match commit_service::generate_message(&diff).await {
        Ok(message) => Ok(message),
        Err(e) => Err(e.to_string())
    }
}
```

## File Naming Conventions

### Python Files
- **Modules**: `snake_case.py` (e.g., `git_engine.py`, `test_orchestrator.py`)
- **Classes**: `PascalCase` (e.g., `GitEngine`, `TestOrchestrator`)
- **Functions**: `snake_case` (e.g., `generate_commit_message`, `apply_patch`)

### TypeScript/React Files
- **Components**: `PascalCase.tsx` (e.g., `CommitPanel.tsx`, `WorkpadList.tsx`)
- **Hooks**: `camelCase.ts` with `use` prefix (e.g., `useSoloGitOperations.ts`)
- **Utils**: `camelCase.ts` (e.g., `formatDiff.ts`, `parseGitStatus.ts`)
- **Types**: `PascalCase.ts` or `types.ts` (e.g., `Workpad.ts`, `types/index.ts`)

### Naming Conventions
- Use descriptive names that reflect Solo-Git domain (e.g., `workpad`, `patch`, `routing_policy`)
- Prefix Tauri commands with action verbs (e.g., `create_workpad`, `apply_patch`, `generate_commit_message`)
- Boolean functions should be `is_*` or `has_*` (e.g., `is_valid_patch`, `has_conflicts`)

## Testing Requirements

### Coverage Goals

- **Minimum**: 90% test coverage for new features
- **Critical Paths**: 100% coverage for AI routing and provider adapters
- **GUI**: Test all Tauri commands and React hooks

### Unit Tests

Test provider adapters independently:

```python
def test_abacus_provider_success():
    """Test successful Abacus AI provider call."""
    provider = AbacusProvider(api_key="test_key")
    response = provider.generate("test prompt")
    assert response.success
    assert response.provider == "abacus"

def test_abacus_provider_fallback():
    """Test fallback when Abacus provider fails."""
    provider = AbacusProvider(api_key="invalid_key")
    with pytest.raises(ProviderError):
        provider.generate("test prompt")
```

Test routing logic:

```python
def test_routing_policy_abacus_first():
    """Test Abacus-first routing policy."""
    policy = RoutingPolicy(primary="abacus", fallback=["openai"])
    router = AIRouter(policy)
    response = router.route("test prompt")
    assert response.provider in ["abacus", "openai"]
```

### Integration Tests

Test end-to-end CLI workflows:

```python
def test_commit_message_generation_cli():
    """Test commit message generation via CLI."""
    result = subprocess.run(
        ["solo-git", "commit-msg", "--json"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "message" in data
```

Test GUI operations:

```typescript
describe('useSoloGitOperations', () => {
  it('should generate commit message', async () => {
    const { generateCommitMessage } = useSoloGitOperations();
    const message = await generateCommitMessage('test diff');
    expect(message).toBeTruthy();
    expect(typeof message).toBe('string');
  });
});
```

### Mocking External APIs

Always mock external API calls in tests:

```python
@patch('solo_git.providers.abacus.AbacusClient')
def test_commit_generator_with_mock(mock_client):
    """Test commit generator with mocked Abacus client."""
    mock_client.return_value.generate.return_value = "feat: add new feature"
    generator = CommitGenerator(provider="abacus")
    message = generator.generate("diff content")
    assert message.startswith("feat:")
```

## AI Routing Patterns

### Abacus-First Architecture

**Always prioritize Abacus AI as the primary provider:**

```python
class RoutingPolicy:
    """Define AI provider routing strategy."""
    
    def __init__(self):
        self.primary = "abacus"
        self.fallback = ["openai"]
        self.timeout = 30  # seconds
```

### Graceful Fallback

Implement cascading fallback with proper error handling:

```python
async def route_with_fallback(prompt: str, policy: RoutingPolicy) -> AIResponse:
    """Route request with fallback chain."""
    providers = [policy.primary] + policy.fallback
    
    for provider_name in providers:
        try:
            provider = get_provider(provider_name)
            response = await provider.generate(prompt, timeout=policy.timeout)
            logger.info(f"Successfully routed to {provider_name}")
            return response
        except ProviderError as e:
            logger.warning(f"Provider {provider_name} failed: {e}")
            continue
    
    raise AllProvidersFailedError("All AI providers failed")
```

### Provider Adapter Pattern

Follow the adapter pattern for consistency:

```python
from abc import ABC, abstractmethod

class ProviderAdapter(ABC):
    """Abstract base class for AI provider adapters."""
    
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> AIResponse:
        """Generate response from AI provider."""
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Validate provider configuration."""
        pass

class AbacusAdapter(ProviderAdapter):
    """Adapter for Abacus AI provider."""
    
    def __init__(self, api_key: str):
        self.client = AbacusClient(api_key=api_key)
    
    async def generate(self, prompt: str, **kwargs) -> AIResponse:
        """Generate response using Abacus AI."""
        try:
            result = await self.client.chat_completion(prompt, **kwargs)
            return AIResponse(
                content=result.content,
                provider="abacus",
                model=result.model,
                success=True
            )
        except Exception as e:
            raise ProviderError("abacus", str(e), e)
```

### Error Handling & Telemetry

Include comprehensive error handling and metrics logging:

```python
def log_provider_metrics(provider: str, success: bool, latency: float):
    """Log provider performance metrics."""
    metrics = {
        "provider": provider,
        "success": success,
        "latency_ms": latency * 1000,
        "timestamp": datetime.utcnow().isoformat()
    }
    logger.info("Provider metrics", extra=metrics)
```

## Solo-Git Specific Conventions

### Workpad-Based Workflow

Workpads are the core workflow unit (not branches):

```python
class Workpad:
    """Represents a Solo-Git workpad for managing changes."""
    
    def __init__(self, name: str, base_branch: str):
        self.name = name
        self.base_branch = base_branch
        self.patches: List[Patch] = []
        self.created_at = datetime.utcnow()
    
    def add_patch(self, patch: Patch) -> None:
        """Add a patch to the workpad."""
        self.patches.append(patch)
    
    def get_combined_diff(self) -> str:
        """Get combined diff of all patches."""
        return "\n".join(patch.diff for patch in self.patches)
```

### Patch Generation & Application

Follow consistent patch patterns:

```python
def generate_patch(workpad: Workpad, files: List[str]) -> Patch:
    """Generate a patch from specified files.
    
    Args:
        workpad: The workpad to generate patch for
        files: List of file paths to include in patch
        
    Returns:
        Patch object containing diff and metadata
    """
    diff = git_diff(files)
    patch = Patch(
        workpad_id=workpad.name,
        files=files,
        diff=diff,
        created_at=datetime.utcnow()
    )
    return patch

def apply_patch(patch: Patch, target_branch: str) -> bool:
    """Apply a patch to target branch.
    
    Args:
        patch: The patch to apply
        target_branch: Branch to apply patch to
        
    Returns:
        True if successful, False otherwise
    """
    try:
        git_checkout(target_branch)
        git_apply(patch.diff)
        return True
    except GitError as e:
        logger.error(f"Failed to apply patch: {e}")
        return False
```

### Commit Message Generation with AI

Use AI assistance for commit messages:

```python
async def generate_commit_message(
    diff: str,
    context: Optional[str] = None,
    style: str = "conventional"
) -> str:
    """Generate AI-powered commit message.
    
    Args:
        diff: Git diff to generate message from
        context: Optional context about the changes
        style: Commit message style (conventional, semantic, etc.)
        
    Returns:
        Generated commit message
    """
    prompt = build_commit_prompt(diff, context, style)
    
    # Use Abacus-first routing
    policy = RoutingPolicy(primary="abacus", fallback=["openai"])
    router = AIRouter(policy)
    
    response = await router.route(prompt)
    message = parse_commit_message(response.content)
    
    return message

def build_commit_prompt(diff: str, context: Optional[str], style: str) -> str:
    """Build prompt for commit message generation."""
    prompt = f"""Generate a {style} commit message for the following changes:

{diff}
"""
    if context:
        prompt += f"\nContext: {context}"
    
    prompt += "\n\nProvide only the commit message, no explanation."
    return prompt
```

### JSON Output Support

Support JSON output from CLI for GUI consumption:

```python
@click.command()
@click.option('--json', is_flag=True, help='Output in JSON format')
def commit_msg(json: bool):
    """Generate commit message from staged changes."""
    try:
        diff = get_staged_diff()
        message = generate_commit_message(diff)
        
        if json:
            output = {
                "success": True,
                "message": message,
                "provider": "abacus"
            }
            click.echo(json.dumps(output))
        else:
            click.echo(message)
    except Exception as e:
        if json:
            output = {
                "success": False,
                "error": str(e)
            }
            click.echo(json.dumps(output))
            sys.exit(1)
        else:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
```

## Configuration Management

Use consistent configuration patterns:

```toml
# ~/.solo-git/config.toml
[ai]
primary_provider = "abacus"
fallback_providers = ["openai"]
timeout = 30

[ai.abacus]
api_key = "${ABACUS_API_KEY}"
model = "gpt-4"

[ai.openai]
api_key = "${OPENAI_API_KEY}"
model = "gpt-4"

[commit]
style = "conventional"
auto_generate = true

[workpad]
default_base_branch = "main"
auto_cleanup = true
```

## Best Practices Summary

1. **Always prioritize Abacus AI** as the primary provider with OpenAI fallback
2. **Write tests first** for new features (TDD approach)
3. **Use type hints** in Python and TypeScript for better code quality
4. **Follow the adapter pattern** for extensibility
5. **Implement comprehensive error handling** with proper logging
6. **Support JSON output** for CLI commands used by GUI
7. **Use custom React hooks** for Tauri command invocations
8. **Document all public APIs** with clear docstrings
9. **Keep workpad operations atomic** and reversible
10. **Log provider metrics** for monitoring and debugging

## Mamba Mentality Principles

- **Excellence**: Aim for 90%+ test coverage, not just passing tests
- **Attention to Detail**: Type hints, docstrings, and error messages matter
- **Continuous Improvement**: Refactor when you see patterns, don't accumulate tech debt
- **Reliability**: Graceful degradation, never crash without helpful error messages
- **Performance**: Async operations where possible, efficient Git operations

## Key Architecture Decisions

- **No Containers**: Solo Git enforces a no-container policy. Use native subprocess execution only.
- **Tests as Review**: Automated testing replaces human code review
- **Fast-Forward Only**: All merges are fast-forward to keep history linear
- **Ephemeral Workpads**: Workpads are disposable, auto-named sandboxes that replace branches
- **Cloud-Native AI**: 100% Abacus.ai RouteLLM API - no local model hosting
