
"""
Abacus.AI provider adapter - PRIMARY router for Solo-Git.
"""
import asyncio
import time
from typing import Optional

from sologit.orchestration.providers import (
    ProviderAdapter,
    ProviderConfig,
    ProviderResponse,
    ProviderType,
)


class AbacusAdapter(ProviderAdapter):
    """Abacus.AI adapter with intelligent routing."""
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.api_key = config.api_key
        self._available = None
        self._last_check = 0
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> ProviderResponse:
        """Generate using Abacus.AI."""
        start_time = time.time()
        
        try:
            # Import here to avoid dependency issues
            import requests
            
            # Construct messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # Call Abacus.AI API
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            
            payload = {
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            
            if model:
                payload["model"] = model
            
            response = await asyncio.to_thread(
                requests.post,
                "https://api.abacus.ai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.config.timeout,
            )
            response.raise_for_status()
            
            data = response.json()
            latency_ms = (time.time() - start_time) * 1000
            
            return ProviderResponse(
                content=data["choices"][0]["message"]["content"],
                provider=ProviderType.ABACUS,
                model=data.get("model", model or "abacus-auto"),
                tokens_used=data.get("usage", {}).get("total_tokens", 0),
                latency_ms=latency_ms,
                cost_usd=data.get("cost_usd", 0.0),
            )
        
        except Exception as e:
            print(f"[AbacusAdapter] Error: {e}")
            raise
    
    def is_available(self) -> bool:
        """Check if Abacus.AI API is reachable."""
        # Cache availability check for 60 seconds
        current_time = time.time()
        if self._available is not None and (current_time - self._last_check) < 60:
            return self._available
        
        try:
            import requests
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.get(
                "https://api.abacus.ai/v1/models",
                headers=headers,
                timeout=5,
            )
            self._available = response.status_code == 200
            self._last_check = current_time
            return self._available
        except:
            self._available = False
            self._last_check = current_time
            return False
    
    def get_default_model(self) -> str:
        """Default: Let Abacus.AI decide."""
        return "abacus-auto"
