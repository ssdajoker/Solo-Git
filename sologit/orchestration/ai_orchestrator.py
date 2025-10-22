"""
AI Orchestrator - Main coordinator for AI operations.

Coordinates planning, code generation, and review operations
with intelligent model selection and cost management.
"""

import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from enum import Enum

from sologit.api.client import AbacusClient, ChatMessage, AbacusAPIError
from sologit.orchestration.model_router import ModelRouter, ModelTier, ComplexityMetrics
from sologit.orchestration.cost_guard import CostGuard, BudgetConfig
from sologit.orchestration.planning_engine import PlanningEngine, CodePlan
from sologit.orchestration.code_generator import CodeGenerator, GeneratedPatch
from sologit.config.manager import ConfigManager
from sologit.utils.logger import get_logger
from sologit.ui.formatter import RichFormatter

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
    
    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        formatter: Optional[RichFormatter] = None,
    ):
        """
        Initialize AI orchestrator.
        
        Args:
            config_manager: Configuration manager (creates new if None)
        """
        self.config_manager = config_manager or ConfigManager()
        self.config = self.config_manager.config
        self.formatter = formatter or RichFormatter()

        # Initialize components
        self.client = AbacusClient(self.config.abacus)
        for name, creds in self.config.deployments.items():
            if creds.deployment_id and creds.deployment_token:
                self.client.register_deployment(name, creds.deployment_id, creds.deployment_token)
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
    
    @contextmanager
    def _progress(self, description: str, total: float = 100.0):
        """Provide a progress context for long-running orchestration steps."""
        if not self.formatter:
            yield None
            return

        with self.formatter.progress(description) as progress:
            task_id = progress.add_task(f"{description} progress", total=total)
            try:
                yield (progress, task_id)
            finally:
                progress.stop_task(task_id)

    @contextmanager
    def _progress_stage(
        self,
        progress,
        task_id: Optional[int],
        description: str,
        advance: float,
    ):
        """Context manager that renders a spinner for a single stage."""
        if not progress or task_id is None:
            yield
            return

        spinner_task = progress.add_task(description, total=None)
        progress.update(task_id, description=description)
        success = False
        start = time.perf_counter()
        try:
            yield
            success = True
        finally:
            progress.remove_task(spinner_task)
            if success and advance:
                progress.advance(task_id, advance)
            if success:
                duration = time.perf_counter() - start
                logger.debug("Stage '%s' completed in %.2fs", description, duration)

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

        model_config = None
        estimated_cost = 0.0
        complexity = None

        with self._progress("AI planning workflow", total=100) as progress_ctx:
            progress, task_id = progress_ctx or (None, None)

            try:
                with self._progress_stage(progress, task_id, "Analyzing task complexity", 20):
                    complexity = self.model_router.analyze_complexity(prompt, repo_context)
                    logger.debug("Complexity analysis: %s", complexity)

                with self._progress_stage(progress, task_id, "Selecting optimal model", 20):
                    if force_model:
                        model_config = self._find_model_by_name(force_model)
                        if not model_config:
                            raise ValueError(f"Model {force_model} not found in configuration")
                    else:
                        remaining_budget = self.cost_guard.get_remaining_budget()
                        model_config = self.model_router.select_model(
                            prompt=prompt,
                            context=repo_context,
                            budget_remaining=remaining_budget,
                        )

                logger.info("Selected model: %s", model_config)

                with self._progress_stage(progress, task_id, "Estimating budget", 10):
                    estimated_tokens = len(prompt.split()) * 4
                    estimated_cost = (estimated_tokens / 1000.0) * model_config.cost_per_1k_tokens * 2

                    if not self.cost_guard.check_budget(estimated_cost):
                        raise Exception(
                            f"Budget exceeded. Remaining: ${self.cost_guard.get_remaining_budget():.2f}"
                        )

                plan: CodePlan
                with self._progress_stage(
                    progress,
                    task_id,
                    f"Generating plan with {model_config.name}",
                    40,
                ):
                    deployment = self._get_deployment_credentials('planning')
                    plan = self.planning_engine.generate_plan(
                        prompt=prompt,
                        repo_context=repo_context,
                        model=model_config.name,
                        deployment_name='planning' if deployment else None,
                        deployment_id=deployment['deployment_id'] if deployment else None,
                        deployment_token=deployment['deployment_token'] if deployment else None,
                    )

                response = self.planning_engine.last_response
                with self._progress_stage(progress, task_id, "Recording cost metrics", 10):
                    if response:
                        prompt_tokens = response.prompt_tokens or estimated_tokens
                        completion_tokens = response.completion_tokens or max(
                            response.total_tokens - prompt_tokens, 0
                        )
                        total_tokens = response.total_tokens or (prompt_tokens + completion_tokens)
                        actual_cost = (total_tokens / 1000.0) * model_config.cost_per_1k_tokens
                        self.cost_guard.record_usage(
                            model=response.model or model_config.name,
                            prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens,
                            cost_per_1k=model_config.cost_per_1k_tokens,
                            task_type=TaskType.PLANNING.value,
                        )
                    else:
                        prompt_tokens = estimated_tokens
                        completion_tokens = estimated_tokens
                        total_tokens = prompt_tokens + completion_tokens
                        actual_cost = (total_tokens / 1000.0) * model_config.cost_per_1k_tokens
                        self.cost_guard.record_usage(
                            model=model_config.name,
                            prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens,
                            cost_per_1k=model_config.cost_per_1k_tokens,
                            task_type=TaskType.PLANNING.value,
                        )

                if progress and task_id is not None:
                    progress.update(task_id, description="Plan ready", completed=100)

                return PlanResponse(
                    plan=plan,
                    model_used=(response.model if response and response.model else model_config.name),
                    cost_usd=actual_cost,
                    complexity=complexity,
                )

            except AbacusAPIError as api_err:
                logger.warning("Planning failed with Abacus error: %s", api_err)
                if progress:
                    progress.update(task_id, description="Retrying with base deployment")

                plan = self.planning_engine.generate_plan(
                    prompt=prompt,
                    repo_context=repo_context,
                    model=(model_config.name if model_config else self.config.models.planning_model),
                )

                fallback_complexity = (
                    complexity or self.model_router.analyze_complexity(prompt, repo_context)
                )

                return PlanResponse(
                    plan=plan,
                    model_used=model_config.name if model_config else self.config.models.planning_model,
                    cost_usd=0.0,
                    complexity=fallback_complexity,
                )

            except Exception as e:
                logger.error("Planning failed: %s", e)
                if progress:
                    progress.update(task_id, description="Evaluating fallback models")

                if model_config is not None:
                    escalated_model = self.model_router.get_escalated_model(
                        model_config,
                        reason="planning_failure",
                    )
                else:
                    escalated_model = None

                if (
                    escalated_model
                    and self.cost_guard.check_budget(max(estimated_cost * 1.5, estimated_cost or 0.0))
                ):
                    logger.info("Escalating to %s", escalated_model)
                    if progress:
                        progress.update(
                            task_id,
                            description=f"Escalating to {escalated_model.name}",
                        )
                    return self.plan(prompt, repo_context, force_model=escalated_model.name)

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

        model_config = None
        estimated_cost = 0.0

        with self._progress("AI code generation", total=100) as progress_ctx:
            progress, task_id = progress_ctx or (None, None)

            try:
                with self._progress_stage(progress, task_id, "Selecting coding model", 20):
                    if force_model:
                        model_config = self._find_model_by_name(force_model)
                        if not model_config:
                            raise ValueError(f"Model {force_model} not found")
                    else:
                        if plan.estimated_complexity == 'low':
                            tier = ModelTier.FAST
                        elif plan.estimated_complexity == 'high':
                            tier = ModelTier.PLANNING
                        else:
                            tier = ModelTier.CODING

                        remaining_budget = self.cost_guard.get_remaining_budget()
                        model_config = self.model_router._get_model_for_tier(tier, remaining_budget)

                logger.info("Selected model for coding: %s", model_config)

                with self._progress_stage(progress, task_id, "Estimating token usage", 15):
                    total_file_size = sum(len(content) for content in (file_contents or {}).values())
                    estimated_tokens = (len(plan.description) + total_file_size) // 4
                    estimated_cost = (estimated_tokens / 1000.0) * model_config.cost_per_1k_tokens * 1.5

                    if not self.cost_guard.check_budget(estimated_cost):
                        raise Exception(
                            f"Budget exceeded. Remaining: ${self.cost_guard.get_remaining_budget():.2f}"
                        )

                patch: GeneratedPatch
                with self._progress_stage(
                    progress,
                    task_id,
                    f"Generating code with {model_config.name}",
                    45,
                ):
                    deployment = self._get_deployment_credentials('coding')
                    patch = self.code_generator.generate_patch(
                        plan=plan,
                        file_contents=file_contents,
                        model=model_config.name,
                        deployment_name='coding' if deployment else None,
                        deployment_id=deployment['deployment_id'] if deployment else None,
                        deployment_token=deployment['deployment_token'] if deployment else None
                    )

                response = self.code_generator.last_response
                with self._progress_stage(progress, task_id, "Recording cost metrics", 15):
                    if response:
                        prompt_tokens = response.prompt_tokens or estimated_tokens
                        completion_tokens = response.completion_tokens or max(
                            response.total_tokens - prompt_tokens, 0
                        )
                        total_tokens = response.total_tokens or (prompt_tokens + completion_tokens)
                        actual_cost = (total_tokens / 1000.0) * model_config.cost_per_1k_tokens
                        self.cost_guard.record_usage(
                            model=response.model or model_config.name,
                            prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens,
                            cost_per_1k=model_config.cost_per_1k_tokens,
                            task_type=TaskType.CODING.value
                        )
                    else:
                        prompt_tokens = estimated_tokens
                        completion_tokens = int(estimated_tokens * 0.5)
                        total_tokens = prompt_tokens + completion_tokens
                        actual_cost = (total_tokens / 1000.0) * model_config.cost_per_1k_tokens
                        self.cost_guard.record_usage(
                            model=model_config.name,
                            prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens,
                            cost_per_1k=model_config.cost_per_1k_tokens,
                            task_type=TaskType.CODING.value
                        )

                if progress and task_id is not None:
                    progress.update(task_id, description="Patch ready", completed=100)

                return PatchResponse(
                    patch=patch,
                    model_used=(response.model if response and response.model else model_config.name),
                    cost_usd=actual_cost
                )

            except AbacusAPIError as api_err:
                logger.warning("Patch generation failed with Abacus error: %s", api_err)
                if progress:
                    progress.update(task_id, description="Retrying with base deployment")

                fallback_model = model_config.name if model_config else self.config.models.coding_model
                patch = self.code_generator.generate_patch(
                    plan=plan,
                    file_contents=file_contents,
                    model=fallback_model
                )
                return PatchResponse(
                    patch=patch,
                    model_used=fallback_model,
                    cost_usd=0.0
                )

            except Exception as e:
                logger.error("Patch generation failed: %s", e)
                if progress:
                    progress.update(task_id, description="Evaluating escalation options")

                if model_config is not None:
                    escalated_model = self.model_router.get_escalated_model(
                        model_config,
                        reason="generation_failure"
                    )
                else:
                    escalated_model = None

                if (
                    escalated_model
                    and self.cost_guard.check_budget(max(estimated_cost * 1.5, estimated_cost or 0.0))
                ):
                    logger.info("Escalating to %s", escalated_model)
                    if progress:
                        progress.update(
                            task_id,
                            description=f"Escalating to {escalated_model.name}",
                        )
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

    def _get_deployment_credentials(self, name: str) -> Optional[Dict[str, str]]:
        """Retrieve deployment credentials if available."""
        creds = self.config.deployments.get(name)
        if not creds or not creds.deployment_id or not creds.deployment_token:
            return None
        return {
            'deployment_id': creds.deployment_id,
            'deployment_token': creds.deployment_token
        }
