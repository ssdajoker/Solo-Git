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
        
        # Lazy import to avoid dependency if not used
        try:
            from anthropic import AsyncAnthropic
            self.client = AsyncAnthropic(
                api_key=config.api_key,
                timeout=config.timeout,
            )
            self._available = True
        except ImportError:
            self._available = False
            self.client = None
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> ProviderResponse:
        """Generate using Anthropic API."""
        if not self._available or not self.client:
            raise RuntimeError("Anthropic SDK not installed. Install with: pip install anthropic>=0.8.0")
        
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
            
            # Estimate cost (rough approximations per 1K tokens)
            cost_per_1k = {
                "claude-3-5-sonnet-20241022": 0.015,
                "claude-3-5-sonnet": 0.015,
                "claude-3-opus": 0.075,
                "claude-3-sonnet": 0.015,
                "claude-3-haiku": 0.0025,
            }
            tokens = response.usage.input_tokens + response.usage.output_tokens
            cost = (tokens / 1000) * cost_per_1k.get(model, 0.015)
            
            # Extract text content
            content = ""
            if response.content:
                for block in response.content:
                    if hasattr(block, 'text'):
                        content += block.text
            
            return ProviderResponse(
                content=content,
                provider=ProviderType.ANTHROPIC,
                model=model,
                tokens_used=tokens,
                latency_ms=latency_ms,
                cost_usd=cost,
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"[AnthropicAdapter] Error: {e}")
            raise
    
    def is_available(self) -> bool:
        """Check Anthropic API availability."""
        if not self._available or not self.client:
            return False
        
        try:
            # Quick check - just verify we have API key
            # Actual API check would be too slow for routing decisions
            return bool(self.config.api_key)
        except:
            return False
    
    def get_default_model(self) -> str:
        return self.config.model or "claude-3-5-sonnet-20241022"
