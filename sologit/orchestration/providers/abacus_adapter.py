"""
Abacus.AI provider adapter - PRIMARY router for Solo-Git.
Uses RouteLLM API for intelligent model routing.
"""
import asyncio
import time
from typing import Optional

from sologit.api.client import AbacusClient, ChatMessage
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
        # Store deployment credentials if provided
        self.deployment_id = getattr(config, 'deployment_id', None)
        self.deployment_token = getattr(config, 'deployment_token', None)
        self.client = AbacusClient(api_key=config.api_key)
    
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
            # Construct messages using ChatMessage
            messages = []
            if system_prompt:
                messages.append(ChatMessage(role="system", content=system_prompt))
            messages.append(ChatMessage(role="user", content=prompt))
            
            # Use default model if not specified
            model_name = model or self.get_default_model()
            
            # Call Abacus.AI chat API
            response = await asyncio.to_thread(
                self.client.chat,
                messages=messages,
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                deployment_id=self.deployment_id,
                deployment_token=self.deployment_token,
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Calculate total tokens and estimate cost
            total_tokens = response.prompt_tokens + response.completion_tokens
            # Rough cost estimate: $0.001 per 1K tokens
            cost_usd = (total_tokens / 1000) * 0.001
            
            return ProviderResponse(
                content=response.content,
                provider=ProviderType.ABACUS,
                model=response.model,
                tokens_used=total_tokens,
                latency_ms=latency_ms,
                cost_usd=cost_usd,
            )
        except Exception as e:
            # Log error and re-raise for policy engine to handle
            print(f"[AbacusAdapter] Error: {e}")
            raise
    
    def is_available(self) -> bool:
        """Check if Abacus.AI API is reachable."""
        try:
            # Quick health check
            return self.client.ping()
        except:
            return False
    
    def get_default_model(self) -> str:
        """Default: gpt-4o-mini for cost-effective routing."""
        return "gpt-4o-mini"
