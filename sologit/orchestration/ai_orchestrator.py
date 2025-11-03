
"""
AI Orchestrator for Solo Git.

Coordinates AI-powered operations including planning, code generation,
patch review, and failure diagnosis.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Iterator, List, Optional

from rich.progress import Progress, TaskID

from sologit.api.client import AbacusClient, ChatResponse
from sologit.config.manager import ConfigManager, SoloGitConfig
from sologit.orchestration.code_generator import CodeGenerator, GeneratedPatch
from sologit.orchestration.cost_guard import CostGuard
from sologit.orchestration.model_router import (
    ComplexityMetrics,
    ModelConfig,
    ModelRouter,
    ModelTier,
)
from sologit.orchestration.planning_engine import PlanningEngine

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Types of AI tasks for cost tracking."""

    PLANNING = "planning"
    CODING = "coding"
    REVIEW = "review"
    DIAGNOSIS = "diagnosis"


@dataclass
class PlanResponse:
    """Response from the planning operation."""

    plan: str
    model_used: str
    tokens_used: int
    cost_usd: float
    complexity: ComplexityMetrics


@dataclass
class PatchResponse:
    """Response from patch generation."""

    patch: GeneratedPatch
    model_used: str
    tokens_used: int
    cost_usd: float


@dataclass
class ReviewResponse:
    """Response from patch review."""

    review: str
    approved: bool
    model_used: str
    tokens_used: int
    cost_usd: float


class AIOrchestrator:
    """
    Orchestrates AI operations with model selection, cost tracking, and error handling.
    """

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the AI orchestrator.

        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.config: SoloGitConfig = config_manager.get_config()
        self.cost_guard = CostGuard(self.config.budget)
        self.model_router = ModelRouter(self.config.to_dict())
        self.planning_engine = PlanningEngine(self.config)
        self.code_generator = CodeGenerator(self.config)

    def plan(
        self,
        task_description: str,
        repo_context: Optional[str] = None,
        force_model: Optional[str] = None,
        escalate_on_failure: bool = False,
        progress: Optional[Progress] = None,
    ) -> PlanResponse:
        """
        Generate an execution plan for a task.

        Args:
            task_description: Description of the task
            repo_context: Optional repository context
            force_model: Force use of a specific model
            escalate_on_failure: Retry with a more capable model on failure
            progress: Optional Rich progress instance

        Returns:
            PlanResponse with the generated plan

        Raises:
            RuntimeError: If planning fails or budget is exceeded
        """
        task_id = None
        if progress:
            task_id = progress.add_task("Planning task...", total=100)

        try:
            with self._progress_stage(progress, task_id, "Analyzing task complexity", 20):
                context = {"repo_context": repo_context} if repo_context else None
                complexity = self.model_router.analyze_complexity(
                    task_description, context=context
                )

            with self._progress_stage(progress, task_id, "Selecting model", 10):
                if force_model:
                    model_config = self._find_model_by_name(force_model)
                    if not model_config:
                        raise ValueError(f"Model '{force_model}' not found in configuration")
                else:
                    select_context = {"task_type": TaskType.PLANNING.value}
                    if repo_context:
                        select_context["repo_context"] = repo_context
                    model_config = self.model_router.select_model(
                        task_description,
                        context=select_context,
                    )

            with self._progress_stage(progress, task_id, "Checking budget", 10):
                estimated_tokens = 2000
                estimated_cost = (estimated_tokens / 1000.0) * model_config.cost_per_1k_tokens
                if not self.cost_guard.check_budget(estimated_cost):
                    raise RuntimeError(
                        f"Insufficient budget for planning. Estimated: ${estimated_cost:.4f}, "
                        f"Remaining: ${self.cost_guard.get_remaining_budget():.4f}"
                    )

            with self._progress_stage(progress, task_id, f"Generating plan with {model_config.name}", 50):
                deployment_creds = self._get_deployment_credentials(model_config.name)

                try:
                    response = self.planning_engine.generate_plan(
                        prompt=task_description,
                        repo_context={"description": task_description, "context": repo_context} if repo_context else None,
                        model=model_config.name,
                        deployment_id=getattr(deployment_creds, 'deployment_id', None) if deployment_creds else None,
                        deployment_token=getattr(deployment_creds, 'deployment_token', None) if deployment_creds else None,
                    )
                except Exception as e:
                    if escalate_on_failure:
                        logger.warning(f"Planning failed with {model_config.name}, escalating: {e}")
                        escalated_model = self.model_router.escalate_model(model_config)
                        if escalated_model:
                            escalated_cost = (estimated_tokens / 1000.0) * escalated_model.cost_per_1k_tokens
                            if self.cost_guard.check_budget(escalated_cost):
                                escalated_creds = self._get_deployment_credentials(escalated_model.name)
                                response = self.planning_engine.generate_plan(
                                    prompt=task_description,
                                    repo_context={"description": task_description, "context": repo_context} if repo_context else None,
                                    model=escalated_model.name,
                                    deployment_id=getattr(escalated_creds, 'deployment_id', None) if escalated_creds else None,
                                    deployment_token=getattr(escalated_creds, 'deployment_token', None) if escalated_creds else None,
                                )
                                model_config = escalated_model
                            else:
                                raise RuntimeError("Insufficient budget for model escalation") from e
                        else:
                            raise RuntimeError("No higher-tier model available for escalation") from e
                    else:
                        raise

            with self._progress_stage(progress, task_id, "Recording usage", 10):
                self.cost_guard.record_usage(
                    model=model_config.name,
                    prompt_tokens=response.prompt_tokens,
                    completion_tokens=response.completion_tokens,
                    cost_per_1k=model_config.cost_per_1k_tokens,
                    task_type=TaskType.PLANNING.value,
                )

            return PlanResponse(
                plan=response.content,
                model_used=model_config.name,
                tokens_used=response.total_tokens,
                cost_usd=(response.total_tokens / 1000.0) * model_config.cost_per_1k_tokens,
                complexity=complexity,
            )

        finally:
            if progress and task_id is not None:
                progress.update(task_id, completed=100)

    def generate_patch(
        self,
        task_description: str,
        plan: Optional[str] = None,
        file_contents: Optional[Dict[str, str]] = None,
        force_model: Optional[str] = None,
        escalate_on_failure: bool = False,
        progress: Optional[Progress] = None,
    ) -> PatchResponse:
        """
        Generate a code patch for a task.

        Args:
            task_description: Description of the task
            plan: Optional execution plan
            file_contents: Optional file contents for context
            force_model: Force use of a specific model
            escalate_on_failure: Retry with a more capable model on failure
            progress: Optional Rich progress instance

        Returns:
            PatchResponse with the generated patch

        Raises:
            RuntimeError: If patch generation fails or budget is exceeded
        """
        task_id = None
        if progress:
            task_id = progress.add_task("Generating patch...", total=100)

        try:
            with self._progress_stage(progress, task_id, "Analyzing complexity", 15):
                context = {}
                if plan:
                    context["plan"] = plan
                if file_contents:
                    context["file_contents"] = file_contents
                complexity = self.model_router.analyze_complexity(
                    task_description, context=context if context else None
                )

            with self._progress_stage(progress, task_id, "Selecting model", 10):
                if force_model:
                    model_config = self._find_model_by_name(force_model)
                    if not model_config:
                        raise ValueError(f"Model '{force_model}' not found in configuration")
                else:
                    select_context = {"task_type": TaskType.CODING.value}
                    if plan:
                        select_context["plan"] = plan
                    if file_contents:
                        select_context["file_contents"] = file_contents
                    model_config = self.model_router.select_model(
                        task_description,
                        context=select_context,
                    )

            with self._progress_stage(progress, task_id, "Estimating cost", 10):
                estimated_tokens = self.model_router.estimate_patch_size(plan or task_description)
                estimated_cost = (estimated_tokens / 1000.0) * model_config.cost_per_1k_tokens
                if not self.cost_guard.check_budget(estimated_cost):
                    raise RuntimeError(
                        f"Insufficient budget for patch generation. Estimated: ${estimated_cost:.4f}, "
                        f"Remaining: ${self.cost_guard.get_remaining_budget():.4f}"
                    )

            with self._progress_stage(progress, task_id, f"Generating code with {model_config.name}", 55):
                client = AbacusClient(self.config.abacus)
                deployment_creds = self._get_deployment_credentials(model_config.name)

                try:
                    patch = self.code_generator.generate_patch(
                        task_description=task_description,
                        plan=plan,
                        file_contents=file_contents,
                        model_config=model_config,
                        client=client,
                        deployment_credentials=deployment_creds,
                    )
                except Exception as e:
                    if escalate_on_failure:
                        logger.warning(f"Patch generation failed with {model_config.name}, escalating: {e}")
                        escalated_model = self.model_router.escalate_model(model_config)
                        if escalated_model:
                            escalated_cost = (estimated_tokens / 1000.0) * escalated_model.cost_per_1k_tokens
                            if self.cost_guard.check_budget(escalated_cost):
                                patch = self.code_generator.generate_patch(
                                    task_description=task_description,
                                    plan=plan,
                                    file_contents=file_contents,
                                    model_config=escalated_model,
                                    client=client,
                                    deployment_credentials=self._get_deployment_credentials(escalated_model.name),
                                )
                                model_config = escalated_model
                            else:
                                raise RuntimeError("Insufficient budget for model escalation") from e
                        else:
                            raise RuntimeError("No higher-tier model available for escalation") from e
                    else:
                        raise

            with self._progress_stage(progress, task_id, "Recording usage", 10):
                token_estimate = estimated_tokens
                self.cost_guard.record_usage(
                    model=model_config.name,
                    prompt_tokens=int(token_estimate * 0.6),
                    completion_tokens=int(token_estimate * 0.4),
                    cost_per_1k=model_config.cost_per_1k_tokens,
                    task_type=TaskType.CODING.value,
                )

            return PatchResponse(
                patch=patch,
                model_used=model_config.name,
                tokens_used=token_estimate,
                cost_usd=(token_estimate / 1000.0) * model_config.cost_per_1k_tokens,
            )

        finally:
            if progress and task_id is not None:
                progress.update(task_id, completed=100)

    def review_patch(
        self,
        patch: GeneratedPatch,
        test_files: Optional[List[str]] = None,
        progress: Optional[Progress] = None,
    ) -> ReviewResponse:
        """
        Review a generated patch.

        Args:
            patch: The patch to review
            test_files: Optional list of test files
            progress: Optional Rich progress instance

        Returns:
            ReviewResponse with the review results
        """
        task_id = None
        if progress:
            task_id = progress.add_task("Reviewing patch...", total=100)

        try:
            with self._progress_stage(progress, task_id, "Selecting review model", 20):
                context = {
                    "task_type": TaskType.REVIEW.value,
                    "files_changed": len(patch.files_changed)
                }
                if test_files:
                    context["test_files"] = test_files
                model_config = self.model_router.select_model(
                    f"Review patch with {len(patch.files_changed)} files",
                    context=context,
                )

            with self._progress_stage(progress, task_id, "Analyzing patch", 60):
                review_prompt = self._build_review_prompt(patch, test_files)
                client = AbacusClient(self.config.abacus)

                response = client.chat(
                    messages=[{"role": "user", "content": review_prompt}],
                    model=model_config.name,
                    max_tokens=model_config.max_tokens,
                )

            with self._progress_stage(progress, task_id, "Recording usage", 20):
                self.cost_guard.record_usage(
                    model=model_config.name,
                    prompt_tokens=response.prompt_tokens,
                    completion_tokens=response.completion_tokens,
                    cost_per_1k=model_config.cost_per_1k_tokens,
                    task_type=TaskType.REVIEW.value,
                )

            approved = "approved" in response.content.lower() or "lgtm" in response.content.lower()

            return ReviewResponse(
                review=response.content,
                approved=approved,
                model_used=model_config.name,
                tokens_used=response.total_tokens,
                cost_usd=(response.total_tokens / 1000.0) * model_config.cost_per_1k_tokens,
            )

        finally:
            if progress and task_id is not None:
                progress.update(task_id, completed=100)

    def diagnose_failure(
        self,
        test_output: str,
        patch: GeneratedPatch,
        context: Optional[Dict[str, Any]] = None,
        progress: Optional[Progress] = None,
    ) -> str:
        """
        Diagnose a test failure.

        Args:
            test_output: The test output
            patch: The patch that was applied
            context: Optional additional context
            progress: Optional Rich progress instance

        Returns:
            Diagnosis string
        """
        task_id = None
        if progress:
            task_id = progress.add_task("Diagnosing failure...", total=100)

        try:
            with self._progress_stage(progress, task_id, "Selecting diagnostic model", 20):
                diag_context = {
                    "task_type": TaskType.DIAGNOSIS.value,
                    "patch": patch,
                }
                if context:
                    diag_context.update(context)
                model_config = self.model_router.select_model(
                    "Diagnose test failure",
                    context=diag_context,
                )

            with self._progress_stage(progress, task_id, "Analyzing failure", 60):
                max_output_lines = 100
                output_lines = test_output.split('\n')
                if len(output_lines) > max_output_lines:
                    trimmed_output = '\n'.join(output_lines[-max_output_lines:])
                    truncated_output = f"[... {len(output_lines) - max_output_lines} lines omitted ...]\n{trimmed_output}"
                else:
                    truncated_output = test_output

                analysis_context = context or {}
                insights = []
                recommendations = []

                if "AssertionError" in test_output:
                    insights.append("Assertion failure detected - expected vs actual value mismatch")
                if "ImportError" in test_output or "ModuleNotFoundError" in test_output:
                    insights.append("Import error - missing dependency or incorrect module path")
                if "timeout" in test_output.lower():
                    insights.append("Test timeout - possible infinite loop or performance issue")

                insight_section = "\n".join(f"• {item}" for item in insights) if insights else "No specific patterns detected."

                base_actions = [
                    "Review the test output for specific error messages and stack traces.",
                    "Verify that the patch changes align with the test expectations.",
                    "Check if any test setup or teardown logic needs adjustment.",
                ]

                recommendations.extend(base_actions)

                for insight in insights:
                    if "Assertion" in insight:
                        recommendations.append("Double-check assertions and expected values in the affected tests.")
                    elif "Import" in insight:
                        recommendations.append("Ensure required packages are installed and module paths are correct.")
                    elif "timeout" in insight.lower():
                        recommendations.append("Profile the test for performance regressions or external dependencies.")

                if analysis_context.get('rerun_command'):
                    recommendations.append(
                        f"Re-run using the suggested command: {analysis_context['rerun_command']}"
                    )

            with self._progress_stage(progress, task_id, "Recording diagnostic metrics", 10):
                if model_config is None:
                    raise RuntimeError("Diagnostic model configuration missing")

                token_estimate = max(len(trimmed_output.split('\n')), 80)
                estimated_cost = (token_estimate / 1000.0) * model_config.cost_per_1k_tokens
                self.cost_guard.record_usage(
                    model=model_config.name,
                    prompt_tokens=int(token_estimate * 0.7),
                    completion_tokens=int(token_estimate * 0.3),
                    cost_per_1k=model_config.cost_per_1k_tokens,
                    task_type=TaskType.DIAGNOSIS.value,
                )

            with self._progress_stage(progress, task_id, "Formatting diagnosis", 10):
                pass

        finally:
            if progress and task_id is not None:
                progress.update(task_id, completed=100)

        recommendation_section = "\n".join(
            f"{idx}. {item}" for idx, item in enumerate(dict.fromkeys(recommendations), start=1)
        )

        patch_summary = (
            f"Files Changed: {', '.join(patch.files_changed) or 'Unknown'}\n"
            f"Additions: {patch.additions} | Deletions: {patch.deletions}"
        )

        diagnosis = (
            "Test Failure Diagnosis:\n\n"
            f"Test Output Summary:\n{truncated_output}\n\n"
            f"Patch Context:\n{patch_summary}\n\n"
            f"Insights:\n{insight_section}\n\n"
            f"Suggested Actions:\n{recommendation_section}\n\n"
            f"Estimated Review Cost: ${estimated_cost:.4f}"
        )

        return diagnosis
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get orchestrator status including budget and model info.
        
        Returns:
            Status dictionary
        """
        api_key = self.config.abacus.api_key
        api_configured = bool(api_key and api_key.strip())
        
        return {
            'budget': self.cost_guard.get_status(),
            'models': {
                'fast': [m.name for m in self.model_router.models[ModelTier.FAST]],
                'coding': [m.name for m in self.model_router.models[ModelTier.CODING]],
                'planning': [m.name for m in self.model_router.models[ModelTier.PLANNING]],
            },
            'api_configured': api_configured
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
            'deployment_token': creds.deployment_token,
        }

    def _build_review_prompt(self, patch: GeneratedPatch, test_files: Optional[List[str]] = None) -> str:
        """Build a prompt for patch review."""
        prompt = f"Review the following code patch:\n\n{patch.diff}\n\n"
        prompt += f"Files changed: {', '.join(patch.files_changed)}\n"
        prompt += f"Additions: {patch.additions}, Deletions: {patch.deletions}\n\n"

        if test_files:
            prompt += f"Test files included: {', '.join(test_files)}\n\n"
        else:
            prompt += "Note: No test files were included with this patch.\n\n"

        prompt += (
            "Please review this patch for:\n"
            "1. Code quality and best practices\n"
            "2. Potential bugs or issues\n"
            "3. Test coverage\n"
            "4. Overall correctness\n\n"
            "Provide your review and indicate if the patch is approved (LGTM) or needs changes."
        )

        return prompt

    @contextmanager
    def _progress_stage(
        self, progress: Optional[Progress], task_id: Optional[TaskID], description: str, advance: int
    ) -> Iterator[None]:
        """Context manager for progress updates."""
        if progress and task_id is not None:
            progress.update(task_id, description=description)
        try:
            yield
        finally:
            if progress and task_id is not None:
                progress.advance(task_id, advance)
