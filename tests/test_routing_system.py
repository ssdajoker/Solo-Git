"""
Tests for AI routing system with Abacus-first architecture.
"""
import pytest

from sologit.orchestration.providers import (
    ProviderType,
    ProviderConfig,
    ProviderResponse,
    ProviderAdapter,
)
from sologit.orchestration.routing_policy import (
    RoutingStrategy,
    RoutingPolicy,
    PolicyEngine,
)
from sologit.orchestration.commit_message_generator import (
    CommitMessageGenerator,
    CommitMessageRequest,
)


# Mock adapter for testing
class MockAdapter(ProviderAdapter):
    """Mock adapter for testing."""
    
    def __init__(self, config: ProviderConfig, should_fail: bool = False):
        super().__init__(config)
        self.should_fail = should_fail
        self.call_count = 0
    
    async def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> ProviderResponse:
        """Mock generation."""
        self.call_count += 1
        
        if self.should_fail:
            raise RuntimeError(f"Mock {self.provider_type.value} failed")
        
        return ProviderResponse(
            content=f"feat: Add feature (from {self.provider_type.value})",
            provider=self.provider_type,
            model=model or "mock-model",
            tokens_used=50,
            latency_ms=100.0,
            cost_usd=0.001,
        )
    
    def is_available(self) -> bool:
        """Mock availability check."""
        return not self.should_fail
    
    def get_default_model(self) -> str:
        """Mock default model."""
        return f"{self.provider_type.value}-default"


class TestRoutingPolicy:
    """Test RoutingPolicy and PolicyEngine."""
    
    def test_default_policy(self):
        """Test default policy configuration."""
        policy = RoutingPolicy()
        
        assert policy.strategy == RoutingStrategy.ABACUS_FIRST
        assert policy.fallback_chain == [
            ProviderType.ABACUS,
            ProviderType.OPENAI,
            ProviderType.ANTHROPIC,
        ]
        assert policy.max_retries == 2
        assert policy.enable_caching is True
    
    def test_user_specified_strategy(self):
        """Test user-specified routing strategy."""
        policy = RoutingPolicy(
            strategy=RoutingStrategy.USER_SPECIFIED,
            user_preference=ProviderType.OPENAI,
        )
        
        assert policy.strategy == RoutingStrategy.USER_SPECIFIED
        assert policy.user_preference == ProviderType.OPENAI
    
    def test_select_provider_abacus_first(self):
        """Test provider selection with Abacus-first strategy."""
        # Create mock adapters
        abacus_adapter = MockAdapter(
            ProviderConfig(provider_type=ProviderType.ABACUS, api_key="test")
        )
        openai_adapter = MockAdapter(
            ProviderConfig(provider_type=ProviderType.OPENAI, api_key="test")
        )
        anthropic_adapter = MockAdapter(
            ProviderConfig(provider_type=ProviderType.ANTHROPIC, api_key="test")
        )
        
        adapters = {
            ProviderType.ABACUS: abacus_adapter,
            ProviderType.OPENAI: openai_adapter,
            ProviderType.ANTHROPIC: anthropic_adapter,
        }
        
        policy = RoutingPolicy()
        engine = PolicyEngine(policy, adapters)
        
        primary, fallbacks = engine.select_provider()
        
        assert primary.provider_type == ProviderType.ABACUS
        assert len(fallbacks) == 2
        assert fallbacks[0].provider_type == ProviderType.OPENAI
        assert fallbacks[1].provider_type == ProviderType.ANTHROPIC
    
    def test_select_provider_fallback_when_primary_unavailable(self):
        """Test fallback when primary provider is unavailable."""
        # Abacus fails, should fallback to OpenAI
        abacus_adapter = MockAdapter(
            ProviderConfig(provider_type=ProviderType.ABACUS, api_key="test"),
            should_fail=True,
        )
        openai_adapter = MockAdapter(
            ProviderConfig(provider_type=ProviderType.OPENAI, api_key="test")
        )
        
        adapters = {
            ProviderType.ABACUS: abacus_adapter,
            ProviderType.OPENAI: openai_adapter,
        }
        
        policy = RoutingPolicy()
        engine = PolicyEngine(policy, adapters)
        
        primary, fallbacks = engine.select_provider()
        
        # Should select OpenAI since Abacus is unavailable
        assert primary.provider_type == ProviderType.OPENAI
    
    def test_select_provider_no_providers_available(self):
        """Test error when no providers are available."""
        # All adapters fail
        adapters = {
            ProviderType.ABACUS: MockAdapter(
                ProviderConfig(provider_type=ProviderType.ABACUS, api_key="test"),
                should_fail=True,
            ),
        }
        
        policy = RoutingPolicy()
        engine = PolicyEngine(policy, adapters)
        
        with pytest.raises(RuntimeError, match="No AI providers available"):
            engine.select_provider()
    
    def test_should_fallback_on_critical_errors(self):
        """Test fallback decision on critical errors."""
        policy = RoutingPolicy()
        engine = PolicyEngine(policy, {})
        
        # Should fallback on auth errors
        assert engine.should_fallback(Exception("api key invalid"), 0) is True
        assert engine.should_fallback(Exception("unauthorized"), 0) is True
        assert engine.should_fallback(Exception("rate limit exceeded"), 0) is True
        assert engine.should_fallback(Exception("timeout"), 0) is True
        
        # Should fallback on max retries
        assert engine.should_fallback(Exception("random error"), 3) is True
        
        # Should not fallback on transient errors
        assert engine.should_fallback(Exception("random error"), 0) is False


class TestCommitMessageGenerator:
    """Test CommitMessageGenerator."""
    
    @pytest.mark.asyncio
    async def test_generate_with_primary_success(self):
        """Test successful generation with primary provider."""
        # Setup mock adapters
        abacus_adapter = MockAdapter(
            ProviderConfig(provider_type=ProviderType.ABACUS, api_key="test")
        )
        openai_adapter = MockAdapter(
            ProviderConfig(provider_type=ProviderType.OPENAI, api_key="test")
        )
        
        adapters = {
            ProviderType.ABACUS: abacus_adapter,
            ProviderType.OPENAI: openai_adapter,
        }
        
        policy = RoutingPolicy()
        engine = PolicyEngine(policy, adapters)
        generator = CommitMessageGenerator(engine)
        
        # Generate message
        request = CommitMessageRequest(
            diff="+ new feature\n- old code",
            workpad_title="feature-x",
            conventional_commit=True,
        )
        
        response = await generator.generate(request)
        
        assert response.message == "feat: Add feature (from abacus)"
        assert response.provider == ProviderType.ABACUS
        assert response.fallback_used is False
        assert abacus_adapter.call_count == 1
        assert openai_adapter.call_count == 0
    
    @pytest.mark.asyncio
    async def test_generate_with_fallback(self):
        """Test generation with fallback when primary fails."""
        # Create a custom adapter that fails during generation but passes availability check
        class FailingAbacusAdapter(MockAdapter):
            def is_available(self):
                return True  # Passes availability check
            
            async def generate(self, *args, **kwargs):
                raise RuntimeError("API error during generation")
        
        abacus_adapter = FailingAbacusAdapter(
            ProviderConfig(provider_type=ProviderType.ABACUS, api_key="test"),
        )
        openai_adapter = MockAdapter(
            ProviderConfig(provider_type=ProviderType.OPENAI, api_key="test")
        )
        
        adapters = {
            ProviderType.ABACUS: abacus_adapter,
            ProviderType.OPENAI: openai_adapter,
        }
        
        policy = RoutingPolicy()
        engine = PolicyEngine(policy, adapters)
        generator = CommitMessageGenerator(engine)
        
        request = CommitMessageRequest(
            diff="+ fix bug",
            workpad_title="bugfix",
            conventional_commit=True,
        )
        
        response = await generator.generate(request)
        
        # Should use OpenAI as fallback
        assert response.message == "feat: Add feature (from openai)"
        assert response.provider == ProviderType.OPENAI
        assert response.fallback_used is True
        assert openai_adapter.call_count == 1
    
    @pytest.mark.asyncio
    async def test_generate_all_providers_fail(self):
        """Test error when all providers fail."""
        # All adapters fail
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
        
        policy = RoutingPolicy()
        engine = PolicyEngine(policy, adapters)
        generator = CommitMessageGenerator(engine)
        
        request = CommitMessageRequest(
            diff="+ changes",
            workpad_title="test",
        )
        
        with pytest.raises(RuntimeError, match="No AI providers available"):
            await generator.generate(request)
    
    def test_build_prompt_conventional_commit(self):
        """Test prompt building for conventional commits."""
        policy = RoutingPolicy()
        engine = PolicyEngine(policy, {})
        generator = CommitMessageGenerator(engine)
        
        request = CommitMessageRequest(
            diff="+ new feature\n- old code",
            workpad_title="feature-x",
            test_results="All tests passed",
            context="Adding user authentication",
            conventional_commit=True,
        )
        
        prompt = generator._build_prompt(request)
        
        assert "feature-x" in prompt
        assert "new feature" in prompt
        assert "All tests passed" in prompt
        assert "Adding user authentication" in prompt
        assert "Conventional Commits" in prompt
    
    def test_build_prompt_free_form(self):
        """Test prompt building for free-form commits."""
        policy = RoutingPolicy()
        engine = PolicyEngine(policy, {})
        generator = CommitMessageGenerator(engine)
        
        request = CommitMessageRequest(
            diff="+ changes",
            workpad_title="test",
            conventional_commit=False,
        )
        
        prompt = generator._build_prompt(request)
        
        assert "Conventional Commits" not in prompt
    
    def test_build_system_prompt_conventional(self):
        """Test system prompt for conventional commits."""
        policy = RoutingPolicy()
        engine = PolicyEngine(policy, {})
        generator = CommitMessageGenerator(engine)
        
        request = CommitMessageRequest(
            diff="",
            workpad_title="",
            conventional_commit=True,
        )
        
        system_prompt = generator._build_system_prompt(request)
        
        assert "Conventional Commits" in system_prompt
        assert "feat:" in system_prompt
        assert "fix:" in system_prompt
        assert "refactor:" in system_prompt
    
    def test_build_system_prompt_free_form(self):
        """Test system prompt for free-form commits."""
        policy = RoutingPolicy()
        engine = PolicyEngine(policy, {})
        generator = CommitMessageGenerator(engine)
        
        request = CommitMessageRequest(
            diff="",
            workpad_title="",
            conventional_commit=False,
        )
        
        system_prompt = generator._build_system_prompt(request)
        
        assert "Conventional Commits" not in system_prompt
        assert "72 characters" in system_prompt


class TestProviderIntegration:
    """Integration tests for provider adapters."""
    
    def test_abacus_adapter_initialization(self):
        """Test Abacus adapter can be initialized."""
        from sologit.orchestration.providers.abacus_adapter import AbacusAdapter
        
        config = ProviderConfig(
            provider_type=ProviderType.ABACUS,
            api_key="test_key",
        )
        
        adapter = AbacusAdapter(config)
        
        assert adapter.provider_type == ProviderType.ABACUS
        assert adapter.config.api_key == "test_key"
        assert adapter.get_default_model() == "gpt-4o-mini"
    
    def test_openai_adapter_initialization(self):
        """Test OpenAI adapter can be initialized if SDK available."""
        try:
            from sologit.orchestration.providers.openai_adapter import OpenAIAdapter
            
            config = ProviderConfig(
                provider_type=ProviderType.OPENAI,
                api_key="test_key",
            )
            
            adapter = OpenAIAdapter(config)
            
            assert adapter.provider_type == ProviderType.OPENAI
            assert adapter.get_default_model() == "gpt-4o-mini"
        except ImportError:
            pytest.skip("OpenAI SDK not installed")
    
    def test_anthropic_adapter_initialization(self):
        """Test Anthropic adapter can be initialized if SDK available."""
        try:
            from sologit.orchestration.providers.anthropic_adapter import AnthropicAdapter
            
            config = ProviderConfig(
                provider_type=ProviderType.ANTHROPIC,
                api_key="test_key",
            )
            
            adapter = AnthropicAdapter(config)
            
            assert adapter.provider_type == ProviderType.ANTHROPIC
            assert adapter.get_default_model() == "claude-3-5-sonnet-20241022"
        except ImportError:
            pytest.skip("Anthropic SDK not installed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
