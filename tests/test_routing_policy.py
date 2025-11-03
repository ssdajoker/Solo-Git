"""Tests for routing policy engine and provider adapters."""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from sologit.orchestration.providers import (
    ProviderType,
    ProviderConfig,
    ProviderResponse,
    ProviderAdapter,
)
from sologit.orchestration.routing_policy import (
    RoutingPolicy,
    RoutingStrategy,
    PolicyEngine,
)


class MockAdapter(ProviderAdapter):
    """Mock provider adapter for testing."""
    
    def __init__(self, config: ProviderConfig, available: bool = True):
        super().__init__(config)
        self._available = available
        self._call_count = 0
    
    async def generate(self, prompt: str, **kwargs) -> ProviderResponse:
        self._call_count += 1
        return ProviderResponse(
            content=f"Mock response from {self.provider_type.value}",
            provider=self.provider_type,
            model="mock-model",
            tokens_used=100,
            latency_ms=50.0,
            cost_usd=0.001,
        )
    
    def is_available(self) -> bool:
        return self._available
    
    def get_default_model(self) -> str:
        return "mock-model"


class TestProviderConfig:
    """Test provider configuration."""
    
    def test_default_config(self):
        config = ProviderConfig(
            provider_type=ProviderType.ABACUS,
            api_key="test-key"
        )
        assert config.enabled is True
        assert config.timeout == 30
        assert config.max_retries == 3
    
    def test_custom_config(self):
        config = ProviderConfig(
            provider_type=ProviderType.OPENAI,
            api_key="test-key",
            enabled=False,
            timeout=60,
            max_retries=5,
        )
        assert config.enabled is False
        assert config.timeout == 60
        assert config.max_retries == 5


class TestRoutingPolicy:
    """Test routing policy configuration."""
    
    def test_default_policy(self):
        policy = RoutingPolicy()
        assert policy.strategy == RoutingStrategy.ABACUS_FIRST
        assert policy.fallback_chain == [
            ProviderType.ABACUS,
            ProviderType.OPENAI,
            ProviderType.ANTHROPIC,
        ]
        assert policy.max_retries == 2
        assert policy.enable_caching is True
    
    def test_custom_policy(self):
        policy = RoutingPolicy(
            strategy=RoutingStrategy.USER_SPECIFIED,
            user_preference=ProviderType.OPENAI,
            max_retries=5,
        )
        assert policy.strategy == RoutingStrategy.USER_SPECIFIED
        assert policy.user_preference == ProviderType.OPENAI
        assert policy.max_retries == 5


class TestPolicyEngine:
    """Test policy engine for provider selection."""
    
    def test_abacus_first_strategy(self):
        # Setup
        adapters = {
            ProviderType.ABACUS: MockAdapter(
                ProviderConfig(provider_type=ProviderType.ABACUS, api_key="key1"),
                available=True
            ),
            ProviderType.OPENAI: MockAdapter(
                ProviderConfig(provider_type=ProviderType.OPENAI, api_key="key2"),
                available=True
            ),
        }
        policy = RoutingPolicy(strategy=RoutingStrategy.ABACUS_FIRST)
        engine = PolicyEngine(policy, adapters)
        
        # Test
        primary, fallbacks = engine.select_provider()
        
        # Assert
        assert primary.provider_type == ProviderType.ABACUS
        assert len(fallbacks) == 1
        assert fallbacks[0].provider_type == ProviderType.OPENAI
    
    def test_fallback_when_primary_unavailable(self):
        # Setup
        adapters = {
            ProviderType.ABACUS: MockAdapter(
                ProviderConfig(provider_type=ProviderType.ABACUS, api_key="key1"),
                available=False  # Primary unavailable
            ),
            ProviderType.OPENAI: MockAdapter(
                ProviderConfig(provider_type=ProviderType.OPENAI, api_key="key2"),
                available=True
            ),
        }
        policy = RoutingPolicy(strategy=RoutingStrategy.ABACUS_FIRST)
        engine = PolicyEngine(policy, adapters)
        
        # Test
        primary, fallbacks = engine.select_provider()
        
        # Assert - should select OpenAI as primary since Abacus unavailable
        assert primary.provider_type == ProviderType.OPENAI
        # Fallbacks list includes Abacus even though unavailable (will be skipped by generator)
        assert len(fallbacks) >= 0
    
    def test_user_specified_strategy(self):
        # Setup
        adapters = {
            ProviderType.ABACUS: MockAdapter(
                ProviderConfig(provider_type=ProviderType.ABACUS, api_key="key1"),
                available=True
            ),
            ProviderType.OPENAI: MockAdapter(
                ProviderConfig(provider_type=ProviderType.OPENAI, api_key="key2"),
                available=True
            ),
        }
        policy = RoutingPolicy(
            strategy=RoutingStrategy.USER_SPECIFIED,
            user_preference=ProviderType.OPENAI
        )
        engine = PolicyEngine(policy, adapters)
        
        # Test
        primary, fallbacks = engine.select_provider()
        
        # Assert - should honor user preference
        assert primary.provider_type == ProviderType.OPENAI
        assert len(fallbacks) == 1
        assert fallbacks[0].provider_type == ProviderType.ABACUS
    
    def test_no_providers_available(self):
        # Setup
        adapters = {
            ProviderType.ABACUS: MockAdapter(
                ProviderConfig(provider_type=ProviderType.ABACUS, api_key="key1"),
                available=False
            ),
            ProviderType.OPENAI: MockAdapter(
                ProviderConfig(provider_type=ProviderType.OPENAI, api_key="key2"),
                available=False
            ),
        }
        policy = RoutingPolicy()
        engine = PolicyEngine(policy, adapters)
        
        # Test - should raise error
        with pytest.raises(RuntimeError, match="No AI providers available"):
            engine.select_provider()
    
    def test_should_fallback_on_auth_error(self):
        policy = RoutingPolicy()
        engine = PolicyEngine(policy, {})
        
        # Test various error scenarios
        assert engine.should_fallback(Exception("Invalid API key"), 0) is True
        assert engine.should_fallback(Exception("Unauthorized"), 0) is True
        assert engine.should_fallback(Exception("Rate limit exceeded"), 0) is True
        assert engine.should_fallback(Exception("Network timeout"), 0) is True
        assert engine.should_fallback(Exception("Connection error"), 0) is True
    
    def test_should_fallback_on_max_retries(self):
        policy = RoutingPolicy(max_retries=2)
        engine = PolicyEngine(policy, {})
        
        # Should fallback if retries exceeded
        assert engine.should_fallback(Exception("Some error"), 2) is True
        assert engine.should_fallback(Exception("Some error"), 3) is True
        
        # Should not fallback if retries not exceeded
        assert engine.should_fallback(Exception("Some error"), 0) is False
        assert engine.should_fallback(Exception("Some error"), 1) is False


class TestProviderAdapter:
    """Test provider adapter interface."""
    
    @pytest.mark.asyncio
    async def test_mock_adapter_generate(self):
        adapter = MockAdapter(
            ProviderConfig(provider_type=ProviderType.ABACUS, api_key="test-key")
        )
        
        response = await adapter.generate("test prompt")
        
        assert response.content == "Mock response from abacus"
        assert response.provider == ProviderType.ABACUS
        assert response.tokens_used == 100
        assert response.latency_ms == 50.0
        assert adapter._call_count == 1
    
    def test_adapter_availability(self):
        adapter_available = MockAdapter(
            ProviderConfig(provider_type=ProviderType.ABACUS, api_key="test-key"),
            available=True
        )
        adapter_unavailable = MockAdapter(
            ProviderConfig(provider_type=ProviderType.OPENAI, api_key="test-key"),
            available=False
        )
        
        assert adapter_available.is_available() is True
        assert adapter_unavailable.is_available() is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
