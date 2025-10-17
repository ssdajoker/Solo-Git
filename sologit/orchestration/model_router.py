
"""
Model Router for intelligent AI model selection.

Routes requests to the optimal model based on task complexity,
security sensitivity, and budget constraints.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any
import re

from sologit.utils.logger import get_logger

logger = get_logger(__name__)


class ModelTier(Enum):
    """Model tier classification."""
    FAST = "fast"           # Quick operations (Llama 3.1 8B, Gemma 2 9B)
    CODING = "coding"       # Specialized coding (DeepSeek, CodeLlama)
    PLANNING = "planning"   # Complex reasoning (GPT-4, Claude 3.5)


@dataclass
class ModelConfig:
    """Configuration for a specific model."""
    name: str
    tier: ModelTier
    max_tokens: int
    temperature: float
    cost_per_1k_tokens: float
    provider: str = "abacus"
    
    def __str__(self) -> str:
        return f"{self.name} ({self.tier.value})"


@dataclass
class ComplexityMetrics:
    """Metrics for assessing task complexity."""
    score: float                    # 0.0 to 1.0
    security_sensitive: bool
    estimated_patch_size: int      # Lines of code
    file_count: int
    has_tests: bool
    requires_architecture: bool
    
    def __str__(self) -> str:
        return (
            f"ComplexityMetrics(score={self.score:.2f}, "
            f"security={self.security_sensitive}, "
            f"patch_lines={self.estimated_patch_size}, "
            f"files={self.file_count})"
        )


class ModelRouter:
    """
    Intelligent model router that selects the optimal AI model
    for each task based on complexity, security, and budget.
    """
    
    # Security-sensitive keywords
    SECURITY_KEYWORDS = [
        'auth', 'authentication', 'password', 'token', 'jwt',
        'crypto', 'encrypt', 'decrypt', 'secret', 'key',
        'security', 'permission', 'authorization', 'oauth',
        'session', 'cookie', 'cors', 'xss', 'csrf', 'sql'
    ]
    
    # Architecture-related keywords
    ARCHITECTURE_KEYWORDS = [
        'architecture', 'design', 'refactor', 'restructure',
        'migrate', 'framework', 'pattern', 'system', 'database',
        'api design', 'schema', 'model', 'interface'
    ]
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize model router.
        
        Args:
            config: Configuration dictionary with model settings
        """
        self.config = config
        self.models: Dict[ModelTier, List[ModelConfig]] = self._load_models()
        self.escalation_rules = config.get('escalation', {})
        
        logger.info("ModelRouter initialized with %d models", 
                   sum(len(models) for models in self.models.values()))
    
    def _load_models(self) -> Dict[ModelTier, List[ModelConfig]]:
        """Load model configurations from config."""
        models = {
            ModelTier.FAST: [],
            ModelTier.CODING: [],
            ModelTier.PLANNING: []
        }
        
        model_configs = self.config.get('ai', {}).get('models', {})
        
        # Fast models
        if 'fast' in model_configs:
            fast_config = model_configs['fast']
            models[ModelTier.FAST].append(ModelConfig(
                name=fast_config.get('primary', 'llama-3.1-8b-instruct'),
                tier=ModelTier.FAST,
                max_tokens=fast_config.get('max_tokens', 1024),
                temperature=fast_config.get('temperature', 0.1),
                cost_per_1k_tokens=0.0001  # Very cheap
            ))
            if 'fallback' in fast_config:
                models[ModelTier.FAST].append(ModelConfig(
                    name=fast_config['fallback'],
                    tier=ModelTier.FAST,
                    max_tokens=fast_config.get('max_tokens', 1024),
                    temperature=fast_config.get('temperature', 0.1),
                    cost_per_1k_tokens=0.0001
                ))
        
        # Coding models
        if 'coding' in model_configs:
            coding_config = model_configs['coding']
            models[ModelTier.CODING].append(ModelConfig(
                name=coding_config.get('primary', 'deepseek-coder-33b'),
                tier=ModelTier.CODING,
                max_tokens=coding_config.get('max_tokens', 2048),
                temperature=coding_config.get('temperature', 0.1),
                cost_per_1k_tokens=0.0005
            ))
            if 'fallback' in coding_config:
                models[ModelTier.CODING].append(ModelConfig(
                    name=coding_config['fallback'],
                    tier=ModelTier.CODING,
                    max_tokens=coding_config.get('max_tokens', 2048),
                    temperature=coding_config.get('temperature', 0.1),
                    cost_per_1k_tokens=0.0005
                ))
        
        # Planning models
        if 'planning' in model_configs:
            planning_config = model_configs['planning']
            models[ModelTier.PLANNING].append(ModelConfig(
                name=planning_config.get('primary', 'gpt-4o'),
                tier=ModelTier.PLANNING,
                max_tokens=planning_config.get('max_tokens', 4096),
                temperature=planning_config.get('temperature', 0.2),
                cost_per_1k_tokens=0.03
            ))
            if 'fallback' in planning_config:
                models[ModelTier.PLANNING].append(ModelConfig(
                    name=planning_config['fallback'],
                    tier=ModelTier.PLANNING,
                    max_tokens=planning_config.get('max_tokens', 4096),
                    temperature=planning_config.get('temperature', 0.2),
                    cost_per_1k_tokens=0.02
                ))
        
        return models
    
    def select_model(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        force_tier: Optional[ModelTier] = None,
        budget_remaining: float = 100.0
    ) -> ModelConfig:
        """
        Select the optimal model for a given task.
        
        Args:
            prompt: User prompt or task description
            context: Additional context (repo size, file list, etc.)
            force_tier: Force a specific tier (overrides auto-selection)
            budget_remaining: Remaining budget in USD
        
        Returns:
            Selected model configuration
        """
        if force_tier:
            logger.debug("Forced model tier: %s", force_tier.value)
            return self._get_model_for_tier(force_tier, budget_remaining)
        
        # Analyze task complexity
        complexity = self.analyze_complexity(prompt, context)
        logger.debug("Task complexity: %s", complexity)
        
        # Apply escalation rules
        tier = self._select_tier(complexity, budget_remaining)
        logger.info("Selected tier: %s for task", tier.value)
        
        return self._get_model_for_tier(tier, budget_remaining)
    
    def analyze_complexity(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ComplexityMetrics:
        """
        Analyze the complexity of a task.
        
        Args:
            prompt: User prompt
            context: Additional context
        
        Returns:
            Complexity metrics
        """
        prompt_lower = prompt.lower()
        context = context or {}
        
        # Check for security-sensitive keywords
        security_sensitive = any(
            keyword in prompt_lower 
            for keyword in self.SECURITY_KEYWORDS
        )
        
        # Check for architecture-related keywords
        requires_architecture = any(
            keyword in prompt_lower
            for keyword in self.ARCHITECTURE_KEYWORDS
        )
        
        # Estimate patch size from prompt
        estimated_patch_size = self._estimate_patch_size(prompt, context)
        
        # Estimate file count
        file_count = context.get('file_count', 1)
        if 'multiple files' in prompt_lower or 'several files' in prompt_lower:
            file_count = max(file_count, 3)
        
        # Check if tests are mentioned
        has_tests = 'test' in prompt_lower or 'spec' in prompt_lower
        
        # Calculate complexity score (0.0 to 1.0)
        score = 0.0
        
        # Size contribution (0.0 to 0.3)
        if estimated_patch_size < 50:
            score += 0.0
        elif estimated_patch_size < 100:
            score += 0.1
        elif estimated_patch_size < 200:
            score += 0.2
        else:
            score += 0.3
        
        # File count contribution (0.0 to 0.2)
        score += min(file_count * 0.05, 0.2)
        
        # Security contribution (0.0 to 0.3)
        if security_sensitive:
            score += 0.3
        
        # Architecture contribution (0.0 to 0.2)
        if requires_architecture:
            score += 0.2
        
        # Clamp to [0.0, 1.0]
        score = min(max(score, 0.0), 1.0)
        
        return ComplexityMetrics(
            score=score,
            security_sensitive=security_sensitive,
            estimated_patch_size=estimated_patch_size,
            file_count=file_count,
            has_tests=has_tests,
            requires_architecture=requires_architecture
        )
    
    def _estimate_patch_size(
        self,
        prompt: str,
        context: Dict[str, Any]
    ) -> int:
        """Estimate the patch size in lines of code."""
        # Simple heuristic based on prompt length and keywords
        base_size = len(prompt.split()) * 2  # Rough estimate
        
        # Adjust based on keywords
        prompt_lower = prompt.lower()
        
        if any(kw in prompt_lower for kw in ['add', 'create', 'implement', 'new']):
            base_size = int(base_size * 1.5)
        
        if any(kw in prompt_lower for kw in ['refactor', 'redesign', 'restructure']):
            base_size = int(base_size * 2.0)
        
        if 'simple' in prompt_lower or 'quick' in prompt_lower:
            base_size = int(base_size * 0.5)
        
        return min(base_size, 500)  # Cap at 500 lines
    
    def _select_tier(
        self,
        complexity: ComplexityMetrics,
        budget_remaining: float
    ) -> ModelTier:
        """
        Select the appropriate model tier based on complexity and budget.
        
        Args:
            complexity: Task complexity metrics
            budget_remaining: Remaining budget
        
        Returns:
            Selected model tier
        """
        # Get escalation rules
        triggers = self.escalation_rules.get('triggers', [])
        
        # Check explicit escalation triggers
        if complexity.security_sensitive:
            logger.debug("Security-sensitive task, escalating to PLANNING")
            return ModelTier.PLANNING
        
        if complexity.requires_architecture:
            logger.debug("Architecture task, escalating to PLANNING")
            return ModelTier.PLANNING
        
        if complexity.estimated_patch_size > 200:
            logger.debug("Large patch size, escalating to PLANNING")
            return ModelTier.PLANNING
        
        # Check complexity score thresholds
        if complexity.score >= 0.7:
            return ModelTier.PLANNING
        elif complexity.score >= 0.3:
            return ModelTier.CODING
        else:
            return ModelTier.FAST
    
    def _get_model_for_tier(
        self,
        tier: ModelTier,
        budget_remaining: float
    ) -> ModelConfig:
        """
        Get the primary or fallback model for a tier based on budget.
        
        Args:
            tier: Model tier
            budget_remaining: Remaining budget
        
        Returns:
            Model configuration
        """
        models = self.models.get(tier, [])
        
        if not models:
            logger.warning("No models configured for tier %s, using FAST", tier.value)
            return self.models[ModelTier.FAST][0]
        
        # If budget is low, prefer cheaper models
        if budget_remaining < 1.0 and len(models) > 1:
            # Sort by cost and pick the cheapest
            models_sorted = sorted(models, key=lambda m: m.cost_per_1k_tokens)
            return models_sorted[0]
        
        # Otherwise use primary model (first in list)
        return models[0]
    
    def get_escalated_model(
        self,
        current_model: ModelConfig,
        reason: str = "failure"
    ) -> Optional[ModelConfig]:
        """
        Get an escalated model after a failure.
        
        Args:
            current_model: Current model that failed
            reason: Reason for escalation
        
        Returns:
            Escalated model or None if already at highest tier
        """
        logger.info("Escalating from %s due to %s", current_model.name, reason)
        
        # Escalation path: FAST -> CODING -> PLANNING
        if current_model.tier == ModelTier.FAST:
            return self._get_model_for_tier(ModelTier.CODING, 100.0)
        elif current_model.tier == ModelTier.CODING:
            return self._get_model_for_tier(ModelTier.PLANNING, 100.0)
        else:
            # Already at highest tier
            return None

