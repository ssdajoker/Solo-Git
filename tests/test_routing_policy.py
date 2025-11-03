
"""Tests for routing policy engine."""
import pytest
from unittest.mock import Mock, AsyncMock
from sologit.orchestration.routing_policy import (
    RoutingStrategy,
    RoutingPolicy,
    PolicyEngine,
)
from sologit.orchestration.providers import ProviderType, ProviderAdapter


class MockAdapter(ProviderAdapter):
    """Mock provider adapter for testing."""
    
    def __init__(self, config, available=True):
        super().__init__(config)
        self._available = available
    
    async def generate(self, prompt, **kwargs):
        return Mock(content="test response")
    
    def is_available(self):
        return self._available
    
    def get_default_model(self):
        return "mock-model"


@pytest.fixture
def mock_adapters():
    """Create mock adapters for all provider types."""
    from sologit.orchestration.providers import ProviderConfig
    
    return {
        ProviderType.ABACUS: MockAdapter(
            ProviderConfig(provider_type=ProviderType.ABACUS, api_key="test"),
            available=True
        ),
        ProviderType.OPENAI: MockAdapter(
            ProviderConfig(provider_type=ProviderType.OPENAI, api_key="test"),
            available=True
        ),
        ProviderType.ANTHROPIC: MockAdapter(
            ProviderConfig(provider_type=ProviderType.ANTHROPIC, api_key="test"),
            available=True
        ),
    }


def test_default_policy_abacus_first():
    """Test default policy selects Abacus first."""
    policy = RoutingPolicy()
    assert policy.strategy == RoutingStrategy.ABACUS_FIRST
    assert policy.fallback_chain[0] == ProviderType.ABACUS


def test_select_provider_abacus_first(mock_adapters):
    """Test Abacus is selected first when available."""
    policy = RoutingPolicy()
    engine = PolicyEngine(policy, mock_adapters)
    
    primary, fallbacks = engine.select_provider()
    
    assert primary.provider_type == ProviderType.ABACUS
    assert len(fallbacks) == 2
    assert fallbacks[0].provider_type == ProviderType.OPENAI
    assert fallbacks[1].provider_type == ProviderType.ANTHROPIC


def test_fallback_when_primary_unavailable(mock_adapters):
    """Test fallback to OpenAI when Abacus is unavailable."""
    # Make Abacus unavailable
    mock_adapters[ProviderType.ABACUS]._available = False
    
    policy = RoutingPolicy()
    engine = PolicyEngine(policy, mock_adapters)
    
    primary, fallbacks = engine.select_provider()
    
    assert primary.provider_type == ProviderType.OPENAI
    # Fallbacks should include both Abacus (even if unavailable) and Anthropic
    assert len(fallbacks) == 2
    # Check that Anthropic is in the fallback chain
    fallback_types = [f.provider_type for f in fallbacks]
    assert ProviderType.ANTHROPIC in fallback_types


def test_user_specified_strategy(mock_adapters):
    """Test user can specify preferred provider."""
    policy = RoutingPolicy(
        strategy=RoutingStrategy.USER_SPECIFIED,
        user_preference=ProviderType.ANTHROPIC
    )
    engine = PolicyEngine(policy, mock_adapters)
    
    primary, fallbacks = engine.select_provider()
    
    assert primary.provider_type == ProviderType.ANTHROPIC


def test_no_providers_available_raises_error(mock_adapters):
    """Test error when no providers are available."""
    # Make all providers unavailable
    for adapter in mock_adapters.values():
        adapter._available = False
    
    policy = RoutingPolicy()
    engine = PolicyEngine(policy, mock_adapters)
    
    with pytest.raises(RuntimeError, match="No AI providers available"):
        engine.select_provider()


def test_should_fallback_on_api_key_error():
    """Test fallback on API key errors."""
    policy = RoutingPolicy()
    engine = PolicyEngine(policy, {})
    
    error = Exception("Invalid API key")
    assert engine.should_fallback(error, retries=0) is True


def test_should_fallback_on_rate_limit():
    """Test fallback on rate limit errors."""
    policy = RoutingPolicy()
    engine = PolicyEngine(policy, {})
    
    error = Exception("Rate limit exceeded (429)")
    assert engine.should_fallback(error, retries=0) is True


def test_should_fallback_on_max_retries():
    """Test fallback when max retries exceeded."""
    policy = RoutingPolicy(max_retries=2)
    engine = PolicyEngine(policy, {})
    
    error = Exception("Some error")
    assert engine.should_fallback(error, retries=2) is True
    assert engine.should_fallback(error, retries=1) is False


def test_fallback_chain_excludes_primary(mock_adapters):
    """Test fallback chain excludes the primary provider."""
    policy = RoutingPolicy()
    engine = PolicyEngine(policy, mock_adapters)
    
    primary, fallbacks = engine.select_provider()
    
    # Ensure primary is not in fallbacks
    fallback_types = [f.provider_type for f in fallbacks]
    assert primary.provider_type not in fallback_types


def test_disabled_provider_not_selected(mock_adapters):
    """Test disabled providers are not selected."""
    # Disable OpenAI
    mock_adapters[ProviderType.OPENAI].config.enabled = False
    
    policy = RoutingPolicy()
    engine = PolicyEngine(policy, mock_adapters)
    
    primary, fallbacks = engine.select_provider()
    
    fallback_types = [f.provider_type for f in fallbacks]
    assert ProviderType.OPENAI not in fallback_types
