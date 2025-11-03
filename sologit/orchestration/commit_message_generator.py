
"""
Commit message generator with Abacus-first routing.
Uses policy engine for intelligent provider selection and fallback.
"""
import asyncio
from typing import Optional
from dataclasses import dataclass
from sologit.orchestration.routing_policy import PolicyEngine, RoutingPolicy
from sologit.orchestration.providers import ProviderResponse, ProviderType
from sologit.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CommitMessageRequest:
    """Request for commit message generation."""
    diff: str
    workpad_title: str
    test_results: Optional[str] = None
    context: Optional[str] = None
    conventional_commit: bool = True


@dataclass
class CommitMessageResponse:
    """Response from commit message generation."""
    message: str
    provider: ProviderType
    model: str
    latency_ms: float
    cost_usd: float
    fallback_used: bool = False


class CommitMessageGenerator:
    """
    Generates commit messages using AI with intelligent routing.
    
    Architecture:
    1. Validate request
    2. Build prompt from diff + context
    3. Policy engine selects provider
    4. Attempt generation with retries
    5. Fallback to next provider if needed
    6. Return normalized response
    """
    
    def __init__(self, policy_engine: PolicyEngine):
        self.policy_engine = policy_engine
    
    async def generate(self, request: CommitMessageRequest) -> CommitMessageResponse:
        """
        Generate commit message with automatic fallback.
        
        Flow:
        1. Build prompt
        2. Select provider (via policy)
        3. Try primary provider
        4. On failure, try fallbacks in order
        5. Return result
        """
        prompt = self._build_prompt(request)
        system_prompt = self._build_system_prompt(request)
        
        # Select provider
        primary, fallbacks = self.policy_engine.select_provider(
            task_type="commit_message",
            complexity=0.3,  # Low complexity task
        )
        
        # Try primary provider
        logger.info(f"Generating commit message with {primary.provider_type.value}")
        try:
            response = await primary.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=200,
            )
            
            return CommitMessageResponse(
                message=response.content.strip(),
                provider=response.provider,
                model=response.model,
                latency_ms=response.latency_ms,
                cost_usd=response.cost_usd,
                fallback_used=False,
            )
        except Exception as e:
            logger.warning(f"Primary provider failed: {e}")
            
            # Try fallbacks
            for i, fallback_adapter in enumerate(fallbacks):
                if not fallback_adapter.is_available():
                    continue
                
                logger.info(f"Trying fallback #{i+1}: {fallback_adapter.provider_type.value}")
                try:
                    response = await fallback_adapter.generate(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        temperature=0.7,
                        max_tokens=200,
                    )
                    
                    return CommitMessageResponse(
                        message=response.content.strip(),
                        provider=response.provider,
                        model=response.model,
                        latency_ms=response.latency_ms,
                        cost_usd=response.cost_usd,
                        fallback_used=True,
                    )
                except Exception as fallback_error:
                    logger.warning(f"Fallback #{i+1} failed: {fallback_error}")
                    continue
            
            # All providers failed
            raise RuntimeError("All AI providers failed. Cannot generate commit message.")
    
    def _build_prompt(self, request: CommitMessageRequest) -> str:
        """Build generation prompt from request."""
        parts = [
            "Generate a concise commit message for the following changes:",
            "",
            f"Workpad: {request.workpad_title}",
            "",
            "Diff:",
            "```",
            request.diff[:2000],  # Limit diff size
            "```",
        ]
        
        if request.test_results:
            parts.extend([
                "",
                f"Test Results: {request.test_results}",
            ])
        
        if request.context:
            parts.extend([
                "",
                f"Context: {request.context}",
            ])
        
        if request.conventional_commit:
            parts.extend([
                "",
                "Format: Use Conventional Commits (e.g., 'feat:', 'fix:', 'refactor:')",
            ])
        
        return "\n".join(parts)
    
    def _build_system_prompt(self, request: CommitMessageRequest) -> str:
        """Build system prompt."""
        if request.conventional_commit:
            return """You are an expert at writing concise, descriptive commit messages.
Follow Conventional Commits format:
- feat: New feature
- fix: Bug fix
- refactor: Code refactoring
- docs: Documentation changes
- test: Test additions/changes
- chore: Maintenance tasks

Keep messages under 72 characters for the subject line.
Add a body if needed for complex changes."""
        
        return """You are an expert at writing concise, descriptive commit messages.
Keep the message under 72 characters.
Focus on WHAT changed and WHY, not HOW."""
