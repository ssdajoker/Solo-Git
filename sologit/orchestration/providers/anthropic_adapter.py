"""Anthropic provider adapter - Fallback #2."""
import asyncio
import time
from typing import Optional

try:
    from anthropic import AsyncAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

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
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")
        
        self.client = AsyncAnthropic(
            api_key=config.api_key,
            timeout=config.timeout,
        )
    
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
        
        model = model or self.get_default_model()
        
        try:
            response = await self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt or "",
                messages=[{"role": "user", "content": prompt}],
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Estimate cost
            cost_per_1k = {
                "claude-3-5-sonnet-20241022": 0.015,
                "claude-3-opus": 0.075,
                "claude-3-sonnet": 0.015,
                "claude-3-haiku": 0.001,
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
        if not ANTHROPIC_AVAILABLE:
            return False
        try:
            # Simple check - we have an API key
            return bool(self.config.api_key)
        except:
            return False
    
    def get_default_model(self) -> str:
        return "claude-3-5-sonnet-20241022"
