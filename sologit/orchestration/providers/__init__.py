"""
Provider adapter interface for AI routing.
Enables Abacus-first architecture with fallback support.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class ProviderType(Enum):
    """Supported AI provider types."""
    ABACUS = "abacus"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"
    LOCAL = "local"  # Future: Ollama


@dataclass
class ProviderConfig:
    """Configuration for a provider."""
    provider_type: ProviderType
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    enabled: bool = True


@dataclass
class ProviderResponse:
    """Standardized provider response."""
    content: str
    provider: ProviderType
    model: str
    tokens_used: int
    latency_ms: float
    cost_usd: float
    cached: bool = False


class ProviderAdapter(ABC):
    """Abstract base class for provider adapters."""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.provider_type = config.provider_type
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> ProviderResponse:
        """Generate text from prompt."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available."""
        pass
    
    @abstractmethod
    def get_default_model(self) -> str:
        """Get default model for this provider."""
        pass


__all__ = [
    "ProviderType",
    "ProviderConfig",
    "ProviderResponse",
    "ProviderAdapter",
]
