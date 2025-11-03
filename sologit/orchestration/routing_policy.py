"""
Routing policy engine for provider selection.
Implements Abacus-first architecture with intelligent fallback.
"""
from typing import List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from sologit.orchestration.providers import ProviderType, ProviderAdapter


class RoutingStrategy(Enum):
    """Routing strategy types."""
    ABACUS_FIRST = "abacus_first"  # Default: Abacus → OpenAI → Anthropic
    COST_OPTIMIZED = "cost_optimized"  # Cheapest available
    LATENCY_OPTIMIZED = "latency_optimized"  # Fastest available
    USER_SPECIFIED = "user_specified"  # User picks provider


@dataclass
class RoutingPolicy:
    """Routing policy configuration."""
    strategy: RoutingStrategy = RoutingStrategy.ABACUS_FIRST
    fallback_chain: List[ProviderType] = field(default_factory=lambda: [
        ProviderType.ABACUS,
        ProviderType.OPENAI,
        ProviderType.ANTHROPIC,
    ])
    max_retries: int = 2
    timeout_seconds: int = 30
    enable_caching: bool = True
    user_preference: Optional[ProviderType] = None


class PolicyEngine:
    """
    Policy engine for routing decisions.
    
    Decision process:
    1. Check user preference (if USER_SPECIFIED strategy)
    2. Apply strategy-specific logic
    3. Check provider availability
    4. Return provider + fallback chain
    """
    
    def __init__(self, policy: RoutingPolicy, adapters: dict):
        """
        Initialize policy engine.
        
        Args:
            policy: Routing policy configuration
            adapters: Dictionary mapping ProviderType to ProviderAdapter instances
        """
        self.policy = policy
        self.adapters = adapters
    
    def select_provider(
        self,
        task_type: str = "general",
        complexity: float = 0.5,
    ) -> Tuple[ProviderAdapter, List[ProviderAdapter]]:
        """
        Select provider and fallback chain.
        
        Args:
            task_type: Type of task (e.g., "commit_message", "code_gen")
            complexity: Task complexity (0.0-1.0)
        
        Returns:
            (primary_provider, fallback_providers)
        
        Raises:
            RuntimeError: If no providers are available
        """
        # USER_SPECIFIED strategy: honor user preference
        if self.policy.strategy == RoutingStrategy.USER_SPECIFIED:
            if self.policy.user_preference:
                primary = self.adapters.get(self.policy.user_preference)
                if primary and primary.is_available():
                    fallbacks = self._get_fallbacks(exclude=self.policy.user_preference)
                    return primary, fallbacks
        
        # Default: ABACUS_FIRST strategy
        # Try each provider in fallback chain order
        for provider_type in self.policy.fallback_chain:
            adapter = self.adapters.get(provider_type)
            if adapter and adapter.config.enabled and adapter.is_available():
                fallbacks = self._get_fallbacks(exclude=provider_type)
                return adapter, fallbacks
        
        # No providers available
        raise RuntimeError(
            "No AI providers available. Check API keys and network. "
            f"Attempted providers: {[p.value for p in self.policy.fallback_chain]}"
        )
    
    def _get_fallbacks(self, exclude: ProviderType) -> List[ProviderAdapter]:
        """Get fallback providers in order, excluding the specified provider."""
        fallbacks = []
        for provider_type in self.policy.fallback_chain:
            if provider_type == exclude:
                continue
            adapter = self.adapters.get(provider_type)
            if adapter and adapter.config.enabled:
                fallbacks.append(adapter)
        return fallbacks
    
    def should_fallback(self, error: Exception, retries: int) -> bool:
        """
        Determine if should fallback to next provider.
        
        Args:
            error: The exception that occurred
            retries: Number of retries attempted so far
        
        Returns:
            True if should try fallback provider
        """
        # Always fallback on network errors, auth errors, rate limits
        error_str = str(error).lower()
        critical_errors = [
            "api key",
            "unauthorized",
            "rate limit",
            "timeout",
            "network",
            "connection",
            "503",
            "502",
            "429",
        ]
        
        if any(err in error_str for err in critical_errors):
            return True
        
        # Fallback if max retries exceeded
        if retries >= self.policy.max_retries:
            return True
        
        return False
