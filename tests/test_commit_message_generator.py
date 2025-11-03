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
    ProviderConfig,
    ProviderAdapter,
    ProviderResponse,
)


class MockAdapter(ProviderAdapter):
    """Mock adapter for testing."""
    
    def __init__(self, config: ProviderConfig, should_fail: bool = False):
        super().__init__(config)
        self._should_fail = should_fail
        self._available = True
    
    async def generate(self, prompt, system_prompt=None, model=None, temperature=0.7, max_tokens=500):
        if self._should_fail:
            raise Exception(f"{self.provider_type.value} failed")
        
        return ProviderResponse(
            content=f"feat: test commit from {self.provider_type.value}",
            provider=self.provider_type,
            model="test-model",
            tokens_used=10,
            latency_ms=100.0,
            cost_usd=0.01,
        )
    
    def is_available(self):
        return self._available
    
    def get_default_model(self):
        return "test-model"


class TestCommitMessageGenerator:
    """Test commit message generator."""
    
    @pytest.mark.asyncio
    async def test_generate_with_primary_provider(self):
        """Test successful generation with primary provider."""
        # Create adapters
        adapters = {
            ProviderType.ABACUS: MockAdapter(
                ProviderConfig(provider_type=ProviderType.ABACUS, api_key="test")
            ),
        }
        
        # Create generator
        policy = RoutingPolicy()
        engine = PolicyEngine(policy, adapters)
        generator = CommitMessageGenerator(engine)
        
        # Create request
        request = CommitMessageRequest(
            diff="+ Added new feature\n- Removed old code",
            workpad_title="feature-branch",
            conventional_commit=True,
        )
        
        # Generate
        response = await generator.generate(request)
        
        # Verify
        assert isinstance(response, CommitMessageResponse)
        assert response.provider == ProviderType.ABACUS
        assert response.fallback_used is False
        assert "feat:" in response.message
    
    @pytest.mark.asyncio
    async def test_generate_with_fallback(self):
        """Test fallback when primary provider fails."""
        # Create adapters (Abacus fails, OpenAI succeeds)
        adapters = {
            ProviderType.ABACUS: MockAdapter(
                ProviderConfig(provider_type=ProviderType.ABACUS, api_key="test"),
                should_fail=True,
            ),
            ProviderType.OPENAI: MockAdapter(
                ProviderConfig(provider_type=ProviderType.OPENAI, api_key="test")
            ),
        }
        
        # Create generator
        policy = RoutingPolicy()
        engine = PolicyEngine(policy, adapters)
        generator = CommitMessageGenerator(engine)
        
        # Create request
        request = CommitMessageRequest(
            diff="+ Fixed bug",
            workpad_title="bugfix",
            conventional_commit=True,
        )
        
        # Generate
        response = await generator.generate(request)
        
        # Verify fallback was used
        assert response.provider == ProviderType.OPENAI
        assert response.fallback_used is True
    
    @pytest.mark.asyncio
    async def test_generate_all_providers_fail(self):
        """Test error when all providers fail."""
        # Create adapters (all fail)
        adapters = {
            ProviderType.ABACUS: MockAdapter(
                ProviderConfig(provider_type=ProviderType.ABACUS, api_key="test"),
                should_fail=True,
            ),
            ProviderType.OPENAI: MockAdapter(
                ProviderConfig(provider_type=ProviderType.OPENAI, api_key="test"),
                should_fail=True,
            ),
        }
        
        # Create generator
        policy = RoutingPolicy()
        engine = PolicyEngine(policy, adapters)
        generator = CommitMessageGenerator(engine)
        
        # Create request
        request = CommitMessageRequest(
            diff="+ Some change",
            workpad_title="test",
        )
        
        # Should raise error
        with pytest.raises(RuntimeError, match="All AI providers failed"):
            await generator.generate(request)
    
    def test_build_prompt_basic(self):
        """Test basic prompt building."""
        adapters = {
            ProviderType.ABACUS: MockAdapter(
                ProviderConfig(provider_type=ProviderType.ABACUS, api_key="test")
            ),
        }
        policy = RoutingPolicy()
        engine = PolicyEngine(policy, adapters)
        generator = CommitMessageGenerator(engine)
        
        request = CommitMessageRequest(
            diff="+ Added feature",
            workpad_title="my-feature",
            conventional_commit=True,
        )
        
        prompt = generator._build_prompt(request)
        
        assert "my-feature" in prompt
        assert "+ Added feature" in prompt
        assert "Conventional Commits" in prompt
    
    def test_build_prompt_with_context(self):
        """Test prompt building with context."""
        adapters = {
            ProviderType.ABACUS: MockAdapter(
                ProviderConfig(provider_type=ProviderType.ABACUS, api_key="test")
            ),
        }
        policy = RoutingPolicy()
        engine = PolicyEngine(policy, adapters)
        generator = CommitMessageGenerator(engine)
        
        request = CommitMessageRequest(
            diff="+ Fixed bug",
            workpad_title="bugfix",
            test_results="All tests passed",
            context="Fixed authentication issue",
            conventional_commit=True,
        )
        
        prompt = generator._build_prompt(request)
        
        assert "All tests passed" in prompt
        assert "Fixed authentication issue" in prompt
    
    def test_build_system_prompt_conventional(self):
        """Test system prompt for conventional commits."""
        adapters = {
            ProviderType.ABACUS: MockAdapter(
                ProviderConfig(provider_type=ProviderType.ABACUS, api_key="test")
            ),
        }
        policy = RoutingPolicy()
        engine = PolicyEngine(policy, adapters)
        generator = CommitMessageGenerator(engine)
        
        request = CommitMessageRequest(
            diff="+ test",
            workpad_title="test",
            conventional_commit=True,
        )
        
        system_prompt = generator._build_system_prompt(request)
        
        assert "Conventional Commits" in system_prompt
        assert "feat:" in system_prompt
        assert "fix:" in system_prompt
    
    def test_build_system_prompt_free_form(self):
        """Test system prompt for free-form commits."""
        adapters = {
            ProviderType.ABACUS: MockAdapter(
                ProviderConfig(provider_type=ProviderType.ABACUS, api_key="test")
            ),
        }
        policy = RoutingPolicy()
        engine = PolicyEngine(policy, adapters)
        generator = CommitMessageGenerator(engine)
        
        request = CommitMessageRequest(
            diff="+ test",
            workpad_title="test",
            conventional_commit=False,
        )
        
        system_prompt = generator._build_system_prompt(request)
        
        assert "Conventional Commits" not in system_prompt
        assert "72 characters" in system_prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
