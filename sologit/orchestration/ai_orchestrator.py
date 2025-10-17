"""
AI Orchestrator - Main coordinator for AI operations.

Coordinates planning, code generation, and review operations
with intelligent model selection and cost management.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from enum import Enum

from sologit.api.client import AbacusClient, ChatMessage
from sologit.orchestration.model_router import ModelRouter, ModelTier, ComplexityMetrics
from sologit.orchestration.cost_guard import CostGuard, BudgetConfig
from sologit.orchestration.planning_engine import PlanningEngine, CodePlan
from sologit.orchestration.code_generator import CodeGenerator, GeneratedPatch
from sologit.config.manager import ConfigManager
from sologit.utils.logger import get_logger

logger = get_logger(__name__)


class TaskType(Enum):
    """Types of AI tasks."""
    PLANNING = "planning"
    CODING = "coding"
    REVIEW = "review"
    DIAGNOSIS = "diagnosis"


@dataclass
class PlanResponse:
    """Response from planning operation."""
    plan: CodePlan
    model_used: str
    cost_usd: float
    complexity: ComplexityMetrics


@dataclass
class PatchResponse:
    """Response from patch generation operation."""
    patch: GeneratedPatch
    model_used: str
    cost_usd: float


@dataclass
class ReviewResponse:
    """Response from code review operation."""
    approved: bool
    issues: List[str]
    suggestions: List[str]
    model_used: str
    cost_usd: float


class AIOrchestrator:
    """
    Main orchestrator for AI operations in Solo Git.
    
    Coordinates between model router, cost guard, planning engine,
    and code generator to provide intelligent AI-driven workflows.
    """
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        Initialize AI orchestrator.
        
        Args:
            config_manager: Configuration manager (creates new if None)
        """
        self.config_manager = config_manager or ConfigManager()
        self.config = self.config_manager.config
        
        # Initialize components
        self.client = AbacusClient(self.config.abacus)
        self.model_router = ModelRouter(self.config.to_dict())
        
        budget_config = BudgetConfig(
            daily_usd_cap=self.config.budget.daily_usd_cap,
            alert_threshold=self.config.budget.alert_threshold,
            track_by_model=self.config.budget.track_by_model
        )
        self.cost_guard = CostGuard(budget_config)
        
        self.planning_engine = PlanningEngine(self.client)
        self.code_generator = CodeGenerator(self.client)
        
        logger.info("AIOrchestrator initialized")
    
    def plan(
        self,
        prompt: str,
        repo_context: Optional[Dict[str, Any]] = None,
        force_model: Optional[str] = None
    ) -> PlanResponse:
        """
        Generate an implementation plan from a user prompt.
        
        Args:
            prompt: User's request
            repo_context: Context about the repository
            force_model: Force a specific model (overrides auto-selection)
        
        Returns:
            Planning response with plan and metadata
        
        Raises:
            Exception: If planning fails or budget exceeded
        """
        logger.info("Starting planning for: %s", prompt[:100])
        
        # Analyze complexity
        complexity = self.model_router.analyze_complexity(prompt, repo_context)
        logger.debug("Complexity analysis: %s", complexity)
        
        # Select model
        if force_model:
            # Use specified model
            model_config = self._find_model_by_name(force_model)
            if not model_config:
                raise ValueError(f"Model {force_model} not found in configuration")
        else:
            # Auto-select based on complexity
            remaining_budget = self.cost_guard.get_remaining_budget()
            model_config = self.model_router.select_model(
                prompt=prompt,
                context=repo_context,
                budget_remaining=remaining_budget
            )
        
        logger.info("Selected model: %s", model_config)
        
        # Estimate cost
        estimated_tokens = len(prompt.split()) * 4  # Rough estimate
        estimated_cost = (estimated_tokens / 1000.0) * model_config.cost_per_1k_tokens * 2  # x2 for response
        
        # Check budget
        if not self.cost_guard.check_budget(estimated_cost):
            raise Exception(
                f"Budget exceeded. Remaining: ${self.cost_guard.get_remaining_budget():.2f}"
            )
        
        # Generate plan
        try:
            plan = self.planning_engine.generate_plan(
                prompt=prompt,
                repo_context=repo_context,
                model=model_config.name,
                # Note: deployment_id and deployment_token would come from config in production
            )
            
            # Record usage (using actual or estimated tokens)
            actual_tokens = estimated_tokens * 2  # Placeholder - would come from API response
            self.cost_guard.record_usage(
                model=model_config.name,
                prompt_tokens=estimated_tokens,
                completion_tokens=estimated_tokens,
                cost_per_1k=model_config.cost_per_1k_tokens,
                task_type=TaskType.PLANNING.value
            )
            
            return PlanResponse(
                plan=plan,
                model_used=model_config.name,
                cost_usd=estimated_cost,
                complexity=complexity
            )
            
        except Exception as e:
            logger.error("Planning failed: %s", e)
            
            # Try to escalate to a smarter model
            escalated_model = self.model_router.get_escalated_model(
                model_config,
                reason="planning_failure"
            )
            
            if escalated_model and self.cost_guard.check_budget(estimated_cost * 1.5):
                logger.info("Escalating to %s", escalated_model)
                return self.plan(prompt, repo_context, force_model=escalated_model.name)
            
            # Re-raise if no escalation possible
            raise
    
    def generate_patch(
        self,
        plan: CodePlan,
        file_contents: Optional[Dict[str, str]] = None,
        force_model: Optional[str] = None
    ) -> PatchResponse:
        """
        Generate a code patch from a plan.
        
        Args:
            plan: Implementation plan
            file_contents: Contents of existing files
            force_model: Force a specific model
        
        Returns:
            Patch response with generated code
        
        Raises:
            Exception: If generation fails or budget exceeded
        """
        logger.info("Generating patch for: %s", plan.title)
        
        # Select model (default to CODING tier for patch generation)
        if force_model:
            model_config = self._find_model_by_name(force_model)
            if not model_config:
                raise ValueError(f"Model {force_model} not found")
        else:
            # For coding, check if it's a simple or complex task
            if plan.estimated_complexity == 'low':
                tier = ModelTier.FAST
            elif plan.estimated_complexity == 'high':
                tier = ModelTier.PLANNING  # Use smart model for complex code
            else:
                tier = ModelTier.CODING
            
            remaining_budget = self.cost_guard.get_remaining_budget()
            model_config = self.model_router._get_model_for_tier(tier, remaining_budget)
        
        logger.info("Selected model for coding: %s", model_config)
        
        # Estimate cost
        total_file_size = sum(len(content) for content in (file_contents or {}).values())
        estimated_tokens = (len(plan.description) + total_file_size) // 4
        estimated_cost = (estimated_tokens / 1000.0) * model_config.cost_per_1k_tokens * 1.5
        
        # Check budget
        if not self.cost_guard.check_budget(estimated_cost):
            raise Exception(
                f"Budget exceeded. Remaining: ${self.cost_guard.get_remaining_budget():.2f}"
            )
        
        # Generate patch
        try:
            patch = self.code_generator.generate_patch(
                plan=plan,
                file_contents=file_contents,
                model=model_config.name
            )
            
            # Record usage
            actual_tokens = estimated_tokens * 1.5  # Placeholder
            self.cost_guard.record_usage(
                model=model_config.name,
                prompt_tokens=estimated_tokens,
                completion_tokens=int(estimated_tokens * 0.5),
                cost_per_1k=model_config.cost_per_1k_tokens,
                task_type=TaskType.CODING.value
            )
            
            return PatchResponse(
                patch=patch,
                model_used=model_config.name,
                cost_usd=estimated_cost
            )
            
        except Exception as e:
            logger.error("Patch generation failed: %s", e)
            
            # Try to escalate
            escalated_model = self.model_router.get_escalated_model(
                model_config,
                reason="generation_failure"
            )
            
            if escalated_model and self.cost_guard.check_budget(estimated_cost * 1.5):
                logger.info("Escalating to %s", escalated_model)
                return self.generate_patch(plan, file_contents, force_model=escalated_model.name)
            
            raise
    
    def review_patch(
        self,
        patch: GeneratedPatch,
        context: Optional[Dict[str, Any]] = None
    ) -> ReviewResponse:
        """
        AI review of a generated patch.
        
        Args:
            patch: Generated patch to review
            context: Additional context
        
        Returns:
            Review response with issues and suggestions
        """
        logger.info("Reviewing patch with %d files", len(patch.files_changed))
        
        # Use planning-tier model for reviews (need good reasoning)
        remaining_budget = self.cost_guard.get_remaining_budget()
        model_config = self.model_router._get_model_for_tier(
            ModelTier.PLANNING,
            remaining_budget
        )
        
        # For Phase 2, return a mock review
        # Full implementation would call the AI model
        logger.warning("Using mock review for Phase 2")
        
        issues = []
        suggestions = []
        
        # Basic heuristics for mock review
        if patch.additions > 200:
            issues.append("Large patch - consider breaking into smaller changes")
        
        if not any('test' in f.lower() for f in patch.files_changed):
            suggestions.append("Consider adding tests for these changes")
        
        # Mock cost
        estimated_cost = 0.01  # Small cost for review
        
        return ReviewResponse(
            approved=len(issues) == 0,
            issues=issues,
            suggestions=suggestions,
            model_used=model_config.name,
            cost_usd=estimated_cost
        )
    
    def diagnose_failure(
        self,
        test_output: str,
        patch: GeneratedPatch,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Diagnose test failures and suggest fixes.
        
        Args:
            test_output: Test failure output
            patch: The patch that was tested
            context: Additional context
        
        Returns:
            Diagnosis and suggested fixes
        """
        logger.info("Diagnosing test failures")
        
        # Use planning-tier model for diagnosis (needs reasoning)
        remaining_budget = self.cost_guard.get_remaining_budget()
        model_config = self.model_router._get_model_for_tier(
            ModelTier.PLANNING,
            remaining_budget
        )
        
        # For Phase 2, return a basic diagnosis
        logger.warning("Using basic diagnosis for Phase 2")
        
        diagnosis = f"""Test Failure Diagnosis:

Test Output:
{test_output[:500]}

Patch Applied:
{patch}

Suggested Actions:
1. Review the test output for specific error messages
2. Check if the patch introduced syntax errors
3. Verify that all imports are correct
4. Ensure test setup/teardown is working

This is a basic diagnosis. Full AI-powered diagnosis will be available in production."""
        
        return diagnosis
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get orchestrator status including budget and model info.
        
        Returns:
            Status dictionary
        """
        return {
            'budget': self.cost_guard.get_status(),
            'models': {
                'fast': [m.name for m in self.model_router.models[ModelTier.FAST]],
                'coding': [m.name for m in self.model_router.models[ModelTier.CODING]],
                'planning': [m.name for m in self.model_router.models[ModelTier.PLANNING]],
            },
            'api_configured': bool(self.config.abacus.api_key)
        }
    
    def _find_model_by_name(self, name: str):
        """Find a model configuration by name."""
        for tier_models in self.model_router.models.values():
            for model in tier_models:
                if model.name == name:
                    return model
        return None
