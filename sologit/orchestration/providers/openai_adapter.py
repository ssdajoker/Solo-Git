
"""OpenAI provider adapter - Fallback #1."""
import asyncio
import time
from typing import Optional

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

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
        if not OPENAI_AVAILABLE:
            raise ImportError("openai package not installed. Run: pip install openai>=1.0.0")
        
        self.client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
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
        """Generate using OpenAI API."""
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
                content=response.choices[0].message.content,
                provider=ProviderType.OPENAI,
                model=model,
                tokens_used=tokens,
                latency_ms=latency_ms,
                cost_usd=cost,
            )
        except Exception as e:
            print(f"[OpenAIAdapter] Error: {e}")
            raise
    
    def is_available(self) -> bool:
        """Check OpenAI API availability."""
        if not OPENAI_AVAILABLE:
            return False
        try:
            # Lightweight check - just verify credentials work
            return self.config.api_key is not None and len(self.config.api_key) > 0
        except:
            return False
    
    def get_default_model(self) -> str:
        return "gpt-4o-mini"
