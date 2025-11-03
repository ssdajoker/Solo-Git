
"""Tests for commit message generator."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from sologit.orchestration.commit_message_generator import (
    CommitMessageGenerator,
    CommitMessageRequest,
    CommitMessageResponse,
)
from sologit.orchestration.routing_policy import PolicyEngine, RoutingPolicy
from sologit.orchestration.providers import (
    ProviderType,
    ProviderResponse,
    ProviderConfig,
)


class MockPolicyEngine:
    """Mock policy engine for testing."""
    
    def __init__(self, primary_adapter, fallback_adapters=None):
        self.primary = primary_adapter
        self.fallbacks = fallback_adapters or []
    
    def select_provider(self, task_type=None, complexity=None):
        return self.primary, self.fallbacks


class MockProviderAdapter:
    """Mock provider adapter."""
    
    def __init__(self, provider_type, should_fail=False):
        self.provider_type = provider_type
        self.should_fail = should_fail
        self.config = ProviderConfig(provider_type=provider_type, api_key="test")
    
    async def generate(self, prompt, system_prompt=None, **kwargs):
        if self.should_fail:
            raise Exception("Provider failed")
        
        return ProviderResponse(
            content="feat: implement amazing feature",
            provider=self.provider_type,
            model="test-model",
            tokens_used=100,
            latency_ms=500,
            cost_usd=0.001,
        )
    
    def is_available(self):
        return not self.should_fail


@pytest.mark.asyncio
async def test_generate_success():
    """Test successful message generation."""
    adapter = MockProviderAdapter(ProviderType.ABACUS)
    policy_engine = MockPolicyEngine(adapter)
    generator = CommitMessageGenerator(policy_engine)
    
    request = CommitMessageRequest(
        diff="+ def foo(): pass",
        workpad_title="add-feature",
        conventional_commit=True,
    )
    
    response = await generator.generate(request)
    
    assert response.message == "feat: implement amazing feature"
    assert response.provider == ProviderType.ABACUS
    assert response.fallback_used is False


@pytest.mark.asyncio
async def test_fallback_on_primary_failure():
    """Test fallback when primary provider fails."""
    primary = MockProviderAdapter(ProviderType.ABACUS, should_fail=True)
    fallback = MockProviderAdapter(ProviderType.OPENAI, should_fail=False)
    policy_engine = MockPolicyEngine(primary, [fallback])
    generator = CommitMessageGenerator(policy_engine)
    
    request = CommitMessageRequest(
        diff="+ def bar(): pass",
        workpad_title="fix-bug",
    )
    
    response = await generator.generate(request)
    
    assert response.provider == ProviderType.OPENAI
    assert response.fallback_used is True


@pytest.mark.asyncio
async def test_all_providers_fail():
    """Test error when all providers fail."""
    primary = MockProviderAdapter(ProviderType.ABACUS, should_fail=True)
    fallback1 = MockProviderAdapter(ProviderType.OPENAI, should_fail=True)
    fallback2 = MockProviderAdapter(ProviderType.ANTHROPIC, should_fail=True)
    policy_engine = MockPolicyEngine(primary, [fallback1, fallback2])
    generator = CommitMessageGenerator(policy_engine)
    
    request = CommitMessageRequest(
        diff="+ def baz(): pass",
        workpad_title="refactor",
    )
    
    with pytest.raises(RuntimeError, match="All AI providers failed"):
        await generator.generate(request)


def test_build_prompt_basic():
    """Test prompt building with basic request."""
    policy_engine = Mock()
    generator = CommitMessageGenerator(policy_engine)
    
    request = CommitMessageRequest(
        diff="+ def foo(): pass",
        workpad_title="add-feature",
    )
    
    prompt = generator._build_prompt(request)
    
    assert "add-feature" in prompt
    assert "+ def foo(): pass" in prompt
    assert "Conventional Commits" in prompt


def test_build_prompt_with_context():
    """Test prompt building with additional context."""
    policy_engine = Mock()
    generator = CommitMessageGenerator(policy_engine)
    
    request = CommitMessageRequest(
        diff="+ def foo(): pass",
        workpad_title="add-feature",
        test_results="All tests passing",
        context="Part of larger refactoring",
    )
    
    prompt = generator._build_prompt(request)
    
    assert "All tests passing" in prompt
    assert "Part of larger refactoring" in prompt


def test_build_system_prompt_conventional():
    """Test system prompt for conventional commits."""
    policy_engine = Mock()
    generator = CommitMessageGenerator(policy_engine)
    
    request = CommitMessageRequest(
        diff="test",
        workpad_title="test",
        conventional_commit=True,
    )
    
    system_prompt = generator._build_system_prompt(request)
    
    assert "Conventional Commits" in system_prompt
    assert "feat:" in system_prompt
    assert "fix:" in system_prompt


def test_build_system_prompt_free_form():
    """Test system prompt for free-form commits."""
    policy_engine = Mock()
    generator = CommitMessageGenerator(policy_engine)
    
    request = CommitMessageRequest(
        diff="test",
        workpad_title="test",
        conventional_commit=False,
    )
    
    system_prompt = generator._build_system_prompt(request)
    
    assert "Conventional Commits" not in system_prompt
    assert "72 characters" in system_prompt


@pytest.mark.asyncio
async def test_diff_truncation():
    """Test that large diffs are truncated."""
    adapter = MockProviderAdapter(ProviderType.ABACUS)
    policy_engine = MockPolicyEngine(adapter)
    generator = CommitMessageGenerator(policy_engine)
    
    # Create a large diff
    large_diff = "+" + ("x" * 5000)
    
    request = CommitMessageRequest(
        diff=large_diff,
        workpad_title="large-change",
    )
    
    prompt = generator._build_prompt(request)
    
    # Verify diff was truncated to 2000 chars (including the "+" prefix)
    # The diff content should be in the prompt but truncated
    assert "xxx" in prompt
    # Verify full diff is not in prompt (should be truncated)
    assert ("x" * 3000) not in prompt
