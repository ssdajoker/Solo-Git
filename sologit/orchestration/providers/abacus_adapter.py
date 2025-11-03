
"""
Abacus.AI provider adapter - PRIMARY router for Solo-Git.
Uses RouteLLM API for intelligent model routing.
"""
import asyncio
import time
from typing import Optional
from sologit.api.client import AbacusClient
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
        self.client = AbacusClient(api_key=config.api_key)
        self._last_health_check = 0
        self._is_healthy = False
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> ProviderResponse:
        """
        Generate using Abacus.AI RouteLLM.
        RouteLLM automatically selects the best model based on:
        - Complexity estimation
        - Cost optimization
        - User preferences
        """
        start_time = time.time()
        
        try:
            # Construct messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # Call RouteLLM (let Abacus.AI choose model if not specified)
            response = await asyncio.to_thread(
                self.client.chat_completion,
                messages=messages,
                model=model,  # Optional: specify model, else RouteLLM decides
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            return ProviderResponse(
                content=response["content"],
                provider=ProviderType.ABACUS,
                model=response.get("model", model or "routellm-auto"),
                tokens_used=response.get("usage", {}).get("total_tokens", 0),
                latency_ms=latency_ms,
                cost_usd=response.get("cost_usd", 0.0),
            )
        except Exception as e:
            # Log error and re-raise for policy engine to handle
            print(f"[AbacusAdapter] Error: {e}")
            raise
    
    def is_available(self) -> bool:
        """Check if Abacus.AI API is reachable (cached for 60s)."""
        now = time.time()
        if now - self._last_health_check < 60:
            return self._is_healthy
        
        try:
            # Quick health check
            self.client.ping()
            self._is_healthy = True
            self._last_health_check = now
            return True
        except:
            self._is_healthy = False
            self._last_health_check = now
            return False
    
    def get_default_model(self) -> str:
        """Default: Let RouteLLM decide."""
        return "routellm-auto"
