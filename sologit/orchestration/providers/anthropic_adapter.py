
"""Anthropic provider adapter - Fallback #2."""
import asyncio
import time
from typing import Optional

from sologit.orchestration.providers import (
    ProviderAdapter,
    ProviderConfig,
    ProviderResponse,
    ProviderType,
)


class AnthropicAdapter(ProviderAdapter):
    """Anthropic Claude adapter."""
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.api_key = config.api_key
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> ProviderResponse:
        """Generate using Anthropic API."""
        start_time = time.time()
        
        try:
            from anthropic import AsyncAnthropic
            
            client = AsyncAnthropic(api_key=self.api_key)
            model = model or self.get_default_model()
            
            response = await client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt or "",
                messages=[{"role": "user", "content": prompt}],
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Cost estimation
            cost_per_1k = {
                "claude-3-5-sonnet-20241022": 0.015,
                "claude-3-opus-20240229": 0.075,
                "claude-3-haiku-20240307": 0.0025,
            }
            tokens = response.usage.input_tokens + response.usage.output_tokens
            cost = (tokens / 1000) * cost_per_1k.get(model, 0.015)
            
            return ProviderResponse(
                content=response.content[0].text,
                provider=ProviderType.ANTHROPIC,
                model=model,
                tokens_used=tokens,
                latency_ms=latency_ms,
                cost_usd=cost,
            )
        
        except Exception as e:
            print(f"[AnthropicAdapter] Error: {e}")
            raise
    
    def is_available(self) -> bool:
        """Check Anthropic API availability."""
        try:
            from anthropic import Anthropic
            client = Anthropic(api_key=self.api_key)
            # Simple check - try to list models
            return True  # Anthropic doesn't have a models.list() endpoint
        except:
            return False
    
    def get_default_model(self) -> str:
        return "claude-3-5-sonnet-20241022"
