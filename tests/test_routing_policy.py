"""Tests for routing policy engine."""
import pytest

from sologit.orchestration.routing_policy import (
    RoutingStrategy,
    RoutingPolicy,
    PolicyEngine,
)
from sologit.orchestration.providers import (
    ProviderType,
    ProviderConfig,
    ProviderAdapter,
    ProviderResponse,
)


class MockAdapter(ProviderAdapter):
    """Mock adapter for testing."""
    
    def __init__(self, config: ProviderConfig, available: bool = True):
        super().__init__(config)
        self._available = available
    
    async def generate(self, prompt, system_prompt=None, model=None, temperature=0.7, max_tokens=500):
        return ProviderResponse(
            content="Test response",
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


class TestRoutingPolicy:
    """Test routing policy configuration."""
    
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
        assert policy.timeout_seconds == 30
        assert policy.enable_caching is True
        assert policy.user_preference is None
    
    def test_custom_policy(self):
        """Test custom policy configuration."""
        policy = RoutingPolicy(
            strategy=RoutingStrategy.USER_SPECIFIED,
            fallback_chain=[ProviderType.OPENAI, ProviderType.ABACUS],
            max_retries=5,
            user_preference=ProviderType.OPENAI,
        )
        
        assert policy.strategy == RoutingStrategy.USER_SPECIFIED
        assert policy.fallback_chain == [ProviderType.OPENAI, ProviderType.ABACUS]
        assert policy.max_retries == 5
        assert policy.user_preference == ProviderType.OPENAI


class TestPolicyEngine:
    """Test policy engine."""
    
    def test_select_provider_abacus_first(self):
        """Test provider selection with ABACUS_FIRST strategy."""
        # Create adapters
        adapters = {
            ProviderType.ABACUS: MockAdapter(
                ProviderConfig(provider_type=ProviderType.ABACUS, api_key="test")
            ),
            ProviderType.OPENAI: MockAdapter(
                ProviderConfig(provider_type=ProviderType.OPENAI, api_key="test")
            ),
        }
        
        # Create policy engine
        policy = RoutingPolicy()
        engine = PolicyEngine(policy, adapters)
        
        # Select provider
        primary, fallbacks = engine.select_provider()
        
        # Should select Abacus first
        assert primary.provider_type == ProviderType.ABACUS
        assert len(fallbacks) == 1
        assert fallbacks[0].provider_type == ProviderType.OPENAI
    
    def test_select_provider_fallback_when_primary_unavailable(self):
        """Test fallback when primary provider is unavailable."""
        # Create adapters (Abacus unavailable)
        adapters = {
            ProviderType.ABACUS: MockAdapter(
                ProviderConfig(provider_type=ProviderType.ABACUS, api_key="test"),
                available=False,
            ),
            ProviderType.OPENAI: MockAdapter(
                ProviderConfig(provider_type=ProviderType.OPENAI, api_key="test")
            ),
        }
        
        # Create policy engine
        policy = RoutingPolicy()
        engine = PolicyEngine(policy, adapters)
        
        # Select provider
        primary, fallbacks = engine.select_provider()
        
        # Should select OpenAI as fallback
        assert primary.provider_type == ProviderType.OPENAI
    
    def test_select_provider_user_specified(self):
        """Test USER_SPECIFIED strategy."""
        # Create adapters
        adapters = {
            ProviderType.ABACUS: MockAdapter(
                ProviderConfig(provider_type=ProviderType.ABACUS, api_key="test")
            ),
            ProviderType.OPENAI: MockAdapter(
                ProviderConfig(provider_type=ProviderType.OPENAI, api_key="test")
            ),
        }
        
        # Create policy engine with user preference
        policy = RoutingPolicy(
            strategy=RoutingStrategy.USER_SPECIFIED,
            user_preference=ProviderType.OPENAI,
        )
        engine = PolicyEngine(policy, adapters)
        
        # Select provider
        primary, fallbacks = engine.select_provider()
        
        # Should select user's preferred provider
        assert primary.provider_type == ProviderType.OPENAI
    
    def test_select_provider_no_providers_available(self):
        """Test error when no providers are available."""
        # Create policy engine with no adapters
        policy = RoutingPolicy()
        engine = PolicyEngine(policy, {})
        
        # Should raise error
        with pytest.raises(RuntimeError, match="No AI providers available"):
            engine.select_provider()
    
    def test_should_fallback_on_critical_errors(self):
        """Test fallback logic for critical errors."""
        policy = RoutingPolicy()
        engine = PolicyEngine(policy, {})
        
        # Test critical errors
        critical_errors = [
            Exception("Invalid API key"),
            Exception("Unauthorized access"),
            Exception("Rate limit exceeded"),
            Exception("Request timeout"),
            Exception("Network error"),
        ]
        
        for error in critical_errors:
            assert engine.should_fallback(error, 0) is True
    
    def test_should_fallback_on_max_retries(self):
        """Test fallback when max retries exceeded."""
        policy = RoutingPolicy(max_retries=2)
        engine = PolicyEngine(policy, {})
        
        # Should not fallback before max retries
        assert engine.should_fallback(Exception("Some error"), 0) is False
        assert engine.should_fallback(Exception("Some error"), 1) is False
        
        # Should fallback when max retries reached
        assert engine.should_fallback(Exception("Some error"), 2) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
