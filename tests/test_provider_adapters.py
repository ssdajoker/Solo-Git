
"""Tests for provider adapters."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from sologit.orchestration.providers import (
    ProviderType,
    ProviderConfig,
    ProviderResponse,
)


@pytest.fixture
def abacus_config():
    """Create Abacus provider config."""
    return ProviderConfig(
        provider_type=ProviderType.ABACUS,
        api_key="test-abacus-key",
    )


@pytest.fixture
def openai_config():
    """Create OpenAI provider config."""
    return ProviderConfig(
        provider_type=ProviderType.OPENAI,
        api_key="test-openai-key",
    )


@pytest.fixture
def anthropic_config():
    """Create Anthropic provider config."""
    return ProviderConfig(
        provider_type=ProviderType.ANTHROPIC,
        api_key="test-anthropic-key",
    )


@pytest.mark.asyncio
async def test_abacus_adapter_generate(abacus_config):
    """Test Abacus adapter generation."""
    from sologit.orchestration.providers.abacus_adapter import AbacusAdapter
    
    with patch('sologit.orchestration.providers.abacus_adapter.AbacusClient') as mock_client:
        # Mock the chat_completion response
        mock_client.return_value.chat_completion.return_value = {
            "content": "test response",
            "model": "gpt-4",
            "usage": {"total_tokens": 100},
            "cost_usd": 0.002,
        }
        
        adapter = AbacusAdapter(abacus_config)
        response = await adapter.generate(
            prompt="test prompt",
            system_prompt="test system",
        )
        
        assert isinstance(response, ProviderResponse)
        assert response.content == "test response"
        assert response.provider == ProviderType.ABACUS
        assert response.tokens_used == 100


def test_abacus_adapter_is_available(abacus_config):
    """Test Abacus availability check."""
    from sologit.orchestration.providers.abacus_adapter import AbacusAdapter
    
    with patch('sologit.orchestration.providers.abacus_adapter.AbacusClient') as mock_client:
        mock_client.return_value.ping.return_value = True
        
        adapter = AbacusAdapter(abacus_config)
        assert adapter.is_available() is True


def test_abacus_adapter_default_model(abacus_config):
    """Test Abacus default model."""
    from sologit.orchestration.providers.abacus_adapter import AbacusAdapter
    
    with patch('sologit.orchestration.providers.abacus_adapter.AbacusClient'):
        adapter = AbacusAdapter(abacus_config)
        assert adapter.get_default_model() == "routellm-auto"


@pytest.mark.asyncio
async def test_openai_adapter_generate(openai_config):
    """Test OpenAI adapter generation."""
    try:
        from sologit.orchestration.providers.openai_adapter import OpenAIAdapter
    except ImportError:
        pytest.skip("OpenAI package not installed")
    
    with patch('sologit.orchestration.providers.openai_adapter.AsyncOpenAI') as mock_openai:
        # Mock the response
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="openai response"))]
        mock_response.usage = Mock(total_tokens=150)
        mock_response.model = "gpt-4o-mini"
        
        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        adapter = OpenAIAdapter(openai_config)
        response = await adapter.generate(prompt="test")
        
        assert response.content == "openai response"
        assert response.provider == ProviderType.OPENAI
        assert response.tokens_used == 150


@pytest.mark.asyncio
async def test_anthropic_adapter_generate(anthropic_config):
    """Test Anthropic adapter generation."""
    try:
        from sologit.orchestration.providers.anthropic_adapter import AnthropicAdapter
    except ImportError:
        pytest.skip("Anthropic package not installed")
    
    with patch('sologit.orchestration.providers.anthropic_adapter.AsyncAnthropic') as mock_anthropic:
        # Mock the response
        mock_response = Mock()
        mock_response.content = [Mock(text="anthropic response")]
        mock_response.usage = Mock(input_tokens=50, output_tokens=50)
        mock_response.model = "claude-3-5-sonnet-20241022"
        
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client
        
        adapter = AnthropicAdapter(anthropic_config)
        response = await adapter.generate(prompt="test")
        
        assert response.content == "anthropic response"
        assert response.provider == ProviderType.ANTHROPIC
        assert response.tokens_used == 100


def test_provider_config_defaults():
    """Test provider config default values."""
    config = ProviderConfig(
        provider_type=ProviderType.ABACUS,
        api_key="test",
    )
    
    assert config.enabled is True
    assert config.timeout == 30
    assert config.max_retries == 3
    assert config.base_url is None
