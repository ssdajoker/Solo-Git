"""OpenAI provider adapter - Fallback #1."""
import asyncio
import time
from typing import Optional

from sologit.orchestration.providers import (
    ProviderAdapter,
    ProviderConfig,
    ProviderResponse,
    ProviderType,
)


class OpenAIAdapter(ProviderAdapter):
    """OpenAI adapter using official SDK."""
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        
        # Lazy import to avoid dependency if not used
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(
                api_key=config.api_key,
                base_url=config.base_url,
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
        """Generate using OpenAI API."""
        if not self._available or not self.client:
            raise RuntimeError("OpenAI SDK not installed. Install with: pip install openai>=1.0.0")
        
        start_time = time.time()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        model = model or self.get_default_model()
        
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Estimate cost (rough approximations per 1K tokens)
            cost_per_1k = {
                "gpt-4o": 0.005,
                "gpt-4o-mini": 0.0015,
                "gpt-4": 0.03,
                "gpt-4-turbo": 0.01,
                "gpt-3.5-turbo": 0.001,
            }
            tokens = response.usage.total_tokens
            cost = (tokens / 1000) * cost_per_1k.get(model, 0.01)
            
            return ProviderResponse(
                content=response.choices[0].message.content or "",
                provider=ProviderType.OPENAI,
                model=model,
                tokens_used=tokens,
                latency_ms=latency_ms,
                cost_usd=cost,
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"[OpenAIAdapter] Error: {e}")
            raise
    
    def is_available(self) -> bool:
        """Check OpenAI API availability."""
        if not self._available or not self.client:
            return False
        
        try:
            # Quick check - just verify we can instantiate client
            # Actual API check would be too slow for routing decisions
            return bool(self.config.api_key)
        except:
            return False
    
    def get_default_model(self) -> str:
        return self.config.model or "gpt-4o-mini"
