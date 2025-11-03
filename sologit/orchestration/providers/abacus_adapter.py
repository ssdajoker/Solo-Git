"""
Abacus.AI provider adapter - PRIMARY router for Solo-Git.
Uses Abacus.AI API for intelligent model routing.
"""
import asyncio
import time
from typing import Optional

from sologit.api.client import AbacusClient, ChatMessage, AbacusAPIConfig
from sologit.orchestration.providers import (
    ProviderAdapter,
    ProviderConfig,
    ProviderResponse,
    ProviderType,
)


class AbacusAdapter(ProviderAdapter):
    """Abacus.AI adapter with RouteLLM support."""
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        
        # Initialize AbacusClient
        abacus_config = AbacusAPIConfig(
            api_key=config.api_key or "",
            endpoint=config.base_url or "https://api.abacus.ai",
        )
        self.client = AbacusClient(abacus_config)
        
        # Store deployment credentials if provided in config
        self.deployment_id = getattr(config, 'deployment_id', None)
        self.deployment_token = getattr(config, 'deployment_token', None)
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> ProviderResponse:
        """
        Generate using Abacus.AI.
        
        Note: Abacus.AI requires deployment credentials for chat operations.
        The deployment ID should be configured in the provider config.
        """
        start_time = time.time()
        
        try:
            # Construct messages
            messages = []
            if system_prompt:
                messages.append(ChatMessage(role="system", content=system_prompt))
            messages.append(ChatMessage(role="user", content=prompt))
            
            # Call Abacus.AI chat API
            response = await asyncio.to_thread(
                self.client.chat,
                messages=messages,
                model=model or self.get_default_model(),
                temperature=temperature,
                max_tokens=max_tokens,
                deployment_id=self.deployment_id,
                deployment_token=self.deployment_token,
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Estimate cost (rough approximation based on tokens)
            # Abacus.AI pricing varies by model, using conservative estimate
            cost_per_1k = 0.01  # $0.01 per 1K tokens (average)
            cost = (response.tokens_used / 1000) * cost_per_1k
            
            return ProviderResponse(
                content=response.content,
                provider=ProviderType.ABACUS,
                model=response.model or model or "abacus-auto",
                tokens_used=response.tokens_used,
                latency_ms=latency_ms,
                cost_usd=cost,
            )
        except Exception as e:
            # Log error and re-raise for policy engine to handle
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"[AbacusAdapter] Error: {e}")
            raise
    
    def is_available(self) -> bool:
        """Check if Abacus.AI API is reachable."""
        try:
            # Quick health check
            return self.client.test_connection()
        except:
            return False
    
    def get_default_model(self) -> str:
        """Default: Let Abacus.AI decide or use configured model."""
        return self.config.model or "gpt-4o"  # Fallback to GPT-4o if no model specified
