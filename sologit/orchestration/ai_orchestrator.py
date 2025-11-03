"""Coordinate AI-driven planning, coding, review, and diagnosis workflows."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Iterator, List, Mapping, Optional, Tuple, Union

from rich.progress import Progress, TaskID

from sologit.api.client import AbacusAPIError, AbacusClient, ChatResponse
from sologit.config.manager import (
    ConfigManager,
    DeploymentCredentials,
    SoloGitConfig,
)
from sologit.orchestration.code_generator import CodeGenerator, GeneratedPatch
from sologit.orchestration.cost_guard import BudgetConfig, CostGuard
from sologit.orchestration.model_router import (
    ComplexityMetrics,
    ModelConfig,
    ModelRouter,
    ModelTier,
)
from sologit.orchestration.planning_engine import CodePlan, FileChange, PlanningEngine

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Task categories tracked for cost accounting."""

    PLANNING = "planning"
    CODING = "coding"
    REVIEW = "review"
    DIAGNOSIS = "diagnosis"


@dataclass
class PlanResponse:
    """Structured response returned from planning."""

    plan: CodePlan
    model_used: str
    cost_usd: float
    complexity: ComplexityMetrics
    tokens_used: int = 0


@dataclass
class PatchResponse:
    """Structured response returned from patch generation."""

    patch: GeneratedPatch
    model_used: str
    cost_usd: float
    tokens_used: int = 0


@dataclass
class ReviewResponse:
    """Structured response returned from patch review."""

    approved: bool
    issues: List[str]
    suggestions: List[str]
    model_used: str
    cost_usd: float
    review: str = ""
    tokens_used: int = 0


class AIOrchestrator:
    """High level coordinator for planning, coding, review, and diagnostics."""

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager

        raw_config = None
        getter = getattr(config_manager, "get_config", None)
        if callable(getter):  # pragma: no branch - simple accessor
            try:
                raw_config = getter()
            except Exception:  # pragma: no cover - defensive
                raw_config = None
        if raw_config is None:
            raw_config = getattr(config_manager, "config", None)

        config_dict: Dict[str, Any]
        if isinstance(raw_config, SoloGitConfig):
            self.config = raw_config
            config_dict = self.config.to_dict()
        else:
            self.config = SoloGitConfig()
            config_dict = self.config.to_dict()
            if raw_config is not None:
                if hasattr(raw_config, "to_dict"):
                    try:
                        custom_dict = raw_config.to_dict()
                        if isinstance(custom_dict, dict):
                            config_dict = custom_dict
                    except Exception:  # pragma: no cover - defensive
                        pass
                if hasattr(raw_config, "budget"):
                    budget_obj = raw_config.budget
                    budget_kwargs: Dict[str, Any] = {}
                    daily_cap = getattr(budget_obj, "daily_usd_cap", None)
                    if isinstance(daily_cap, (int, float)):
                        budget_kwargs["daily_usd_cap"] = float(daily_cap)
                    alert_threshold = getattr(budget_obj, "alert_threshold", None)
                    if isinstance(alert_threshold, (int, float)):
                        budget_kwargs["alert_threshold"] = float(alert_threshold)
                    track_by_model = getattr(budget_obj, "track_by_model", None)
                    if isinstance(track_by_model, bool):
                        budget_kwargs["track_by_model"] = track_by_model
                    if budget_kwargs:
                        self.config.budget = BudgetConfig(**budget_kwargs)
                if hasattr(raw_config, "abacus"):
                    abacus = raw_config.abacus
                    endpoint = getattr(abacus, "endpoint", None)
                    api_key = getattr(abacus, "api_key", None)
                    if isinstance(endpoint, str):
                        self.config.abacus.endpoint = endpoint
                    if isinstance(api_key, str):
                        self.config.abacus.api_key = api_key
                if hasattr(raw_config, "deployments"):
                    self.config.deployments = raw_config.deployments

        self.client = AbacusClient(self.config.abacus)
        self.cost_guard = CostGuard(self.config.budget)
        self.model_router = ModelRouter(config_dict)
        self.planning_engine = PlanningEngine(self.client)
        self.code_generator = CodeGenerator(self.client)

    # ------------------------------------------------------------------
    # Planning
    # ------------------------------------------------------------------
    def plan(
        self,
        task_description: Optional[str] = None,
        *,
        prompt: Optional[str] = None,
        repo_context: Optional[Dict[str, Any]] = None,
        force_model: Optional[str] = None,
        escalate_on_failure: bool = True,
        progress: Optional[Progress] = None,
    ) -> PlanResponse:
        """Generate an implementation plan for a requested task."""

        description = (prompt or task_description or "").strip()
        if not description:
            raise ValueError("Task description is required")

        context = dict(repo_context or {})
        select_context = {
            "task_type": TaskType.PLANNING.value,
            **({"repo_context": context} if context else {}),
        }

        with self._progress_stage(progress, None, "Analyzing task", 0):
            complexity = self.model_router.analyze_complexity(
                description, context=select_context
            )

        forced_tier = None if force_model else ModelTier.PLANNING
        model_config = self._select_model(
            description, select_context, force_model, force_tier=forced_tier
        )
        estimated_tokens = self._estimate_plan_tokens(description, complexity)

        plan: Optional[CodePlan] = None
        chat_response: Optional[ChatResponse] = None
        attempted_live = False

        for attempt in range(3):
            estimated_cost = (estimated_tokens / 1000.0) * model_config.cost_per_1k_tokens
            if not self.cost_guard.check_budget(estimated_cost):
                remaining = self.cost_guard.get_remaining_budget()
                raise RuntimeError(
                    "Budget exceeded for planning. "
                    f"Estimated ${estimated_cost:.4f}, Remaining ${remaining:.4f}"
                )

            deployment_name, creds = self._get_deployment_credentials(model_config)
            use_credentials = bool(
                deployment_name and creds and getattr(creds, "has_token", True)
            )

            try:
                generated_plan = self.planning_engine.generate_plan(
                    prompt=description,
                    repo_context=context,
                    model=model_config.name,
                    deployment_name=deployment_name if use_credentials else None,
                    deployment_id=getattr(creds, "deployment_id", None)
                    if use_credentials
                    else None,
                    deployment_token=getattr(creds, "deployment_token", None)
                    if use_credentials
                    else None,
                )
                plan, _ = self._ensure_code_plan(generated_plan)
                chat_response = getattr(self.planning_engine, "last_response", None)
                attempted_live = attempted_live or use_credentials
                break
            except AbacusAPIError as exc:  # pragma: no cover - exercised via tests
                logger.warning("Planning via Abacus failed: %s", exc)
                attempted_live = True
                generated_plan = self.planning_engine.generate_plan(
                    prompt=description,
                    repo_context=context,
                    model=model_config.name,
                )
                plan, _ = self._ensure_code_plan(generated_plan)
                chat_response = getattr(self.planning_engine, "last_response", None)
                break
            except Exception as exc:  # pragma: no cover - escalated in tests
                if not escalate_on_failure:
                    raise
                escalated = self._escalate_model(model_config)
                if escalated and escalated != model_config:
                    model_config = escalated
                    continue
                if attempt < 2:
                    continue
                raise
        else:  # pragma: no cover - defensive
            raise RuntimeError("Planning failed after escalation attempts")

        assert plan is not None  # For type checkers
        estimated_tokens = self._estimate_plan_tokens(description, complexity, plan)
        allow_estimate = not attempted_live
        tokens_used, cost_usd = self._record_usage_from_response(
            model_name=chat_response.model if chat_response else model_config.name,
            task_type=TaskType.PLANNING,
            cost_per_1k=model_config.cost_per_1k_tokens,
            response=chat_response,
            estimated_tokens=estimated_tokens,
            allow_estimate=allow_estimate,
        )

        model_used = chat_response.model if chat_response else model_config.name

        return PlanResponse(
            plan=plan,
            model_used=model_used,
            cost_usd=cost_usd,
            complexity=complexity,
            tokens_used=tokens_used,
        )

    # ------------------------------------------------------------------
    # Patch generation
    # ------------------------------------------------------------------
    def generate_patch(
        self,
        plan: Union[CodePlan, str],
        file_contents: Optional[Dict[str, str]] = None,
        force_model: Optional[str] = None,
        escalate_on_failure: bool = True,
        progress: Optional[Progress] = None,
        repo_context: Optional[str] = None,
    ) -> PatchResponse:
        """Generate a code patch from a plan or textual description."""

        code_plan, task_description = self._ensure_code_plan(plan)
        analysis_context: Dict[str, Any] = {
            "task_type": TaskType.CODING.value,
            "plan": str(code_plan),
            "file_count": max(len(code_plan.file_changes), 1),
        }
        if file_contents:
            analysis_context["file_contents"] = {
                path: len(content) for path, content in file_contents.items()
            }
        if repo_context:
            analysis_context["repo_context"] = repo_context

        with self._progress_stage(progress, None, "Analyzing complexity", 0):
            complexity = self.model_router.analyze_complexity(
                task_description, context=analysis_context
            )

        estimated_complexity_level = getattr(
            code_plan, "estimated_complexity", ""
        ).lower()
        if force_model:
            forced_tier = None
        elif estimated_complexity_level == "high":
            forced_tier = ModelTier.PLANNING
        elif estimated_complexity_level == "medium":
            forced_tier = ModelTier.CODING
        else:
            forced_tier = ModelTier.FAST
            if self._has_deployment_for_tier(ModelTier.CODING):
                forced_tier = ModelTier.CODING

        model_config = self._select_model(
            task_description, analysis_context, force_model, force_tier=forced_tier
        )
        estimated_tokens = self._estimate_patch_tokens(code_plan, file_contents)

        patch: Optional[GeneratedPatch] = None
        chat_response: Optional[ChatResponse] = None
        attempted_live = False

        for attempt in range(3):
            estimated_cost = (estimated_tokens / 1000.0) * model_config.cost_per_1k_tokens
            if not self.cost_guard.check_budget(estimated_cost):
                remaining = self.cost_guard.get_remaining_budget()
                raise RuntimeError(
                    "Budget exceeded for patch generation. "
                    f"Estimated ${estimated_cost:.4f}, Remaining ${remaining:.4f}"
                )

            deployment_name, creds = self._get_deployment_credentials(model_config)
            has_token = getattr(creds, "has_token", True) if creds else True
            use_credentials = bool(deployment_name and creds and has_token)
            call_kwargs = {
                "plan": code_plan,
                "file_contents": file_contents,
                "model": model_config.name,
                "deployment_name": deployment_name if use_credentials else None,
                "deployment_id": (
                    getattr(creds, "deployment_id", None) if use_credentials else None
                ),
                "deployment_token": (
                    getattr(creds, "deployment_token", None)
                    if use_credentials
                    else None
                ),
            }

            try:
                patch = self.code_generator.generate_patch(**call_kwargs)
                chat_response = getattr(self.code_generator, "last_response", None)
                attempted_live = attempted_live or use_credentials
                break
            except AbacusAPIError as exc:  # pragma: no cover - exercised in tests
                logger.warning("Patch generation via Abacus failed: %s", exc)
                attempted_live = True
                call_kwargs.update(
                    {
                        "deployment_name": None,
                        "deployment_id": None,
                        "deployment_token": None,
                    }
                )
                patch = self.code_generator.generate_patch(**call_kwargs)
                chat_response = getattr(self.code_generator, "last_response", None)
                break
            except Exception:
                if not escalate_on_failure:
                    raise
                escalated = self._escalate_model(model_config)
                if escalated and escalated != model_config:
                    model_config = escalated
                    continue
                if attempt < 2:
                    continue
                raise
        else:  # pragma: no cover - defensive
            raise RuntimeError("Patch generation failed after escalation attempts")

        assert patch is not None
        estimated_tokens = self._estimate_patch_tokens(code_plan, file_contents, patch)
        allow_estimate = not attempted_live
        tokens_used, cost_usd = self._record_usage_from_response(
            model_name=chat_response.model if chat_response else model_config.name,
            task_type=TaskType.CODING,
            cost_per_1k=model_config.cost_per_1k_tokens,
            response=chat_response,
            estimated_tokens=estimated_tokens,
            allow_estimate=allow_estimate,
        )

        model_used = chat_response.model if chat_response else model_config.name
        return PatchResponse(
            patch=patch,
            model_used=model_used,
            cost_usd=cost_usd,
            tokens_used=tokens_used,
        )

    # ------------------------------------------------------------------
    # Review
    # ------------------------------------------------------------------
    def review_patch(
        self,
        patch: GeneratedPatch,
        test_files: Optional[List[str]] = None,
        progress: Optional[Progress] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ReviewResponse:
        """Provide a lightweight, heuristic-driven review of a patch."""

        review_context = dict(context or {})
        selection_context = {
            "task_type": TaskType.REVIEW.value,
            "file_count": max(len(patch.files_changed), 1),
            **review_context,
        }

        model_config = self._select_model(
            f"Review patch touching {len(patch.files_changed)} files",
            selection_context,
            force_model=None,
        )

        deployment_name, creds = self._get_deployment_credentials(model_config)
        use_credentials = bool(
            deployment_name and creds and getattr(creds, "has_token", True)
        )

        chat_response: Optional[ChatResponse] = None
        attempted_live = False
        review_text = ""

        if use_credentials:
            attempted_live = True
            try:
                chat_response = self.client.chat(
                    messages=[{"role": "user", "content": self._build_review_prompt(patch, test_files)}],
                    model=model_config.name,
                    max_tokens=model_config.max_tokens,
                    deployment=deployment_name,
                    deployment_id=creds.deployment_id,
                    deployment_token=creds.deployment_token,
                )
                review_text = chat_response.content
            except (AbacusAPIError, ValueError) as exc:  # pragma: no cover
                logger.warning("Remote review failed, using heuristics: %s", exc)
                chat_response = None
                review_text = ""

        heuristic_review, issues, suggestions, heuristic_approved = self._heuristic_review(
            patch,
            test_files=test_files,
            context=review_context,
        )

        if not review_text:
            review_text = heuristic_review

        if chat_response:
            approved = "approved" in review_text.lower() or "lgtm" in review_text.lower()
            if not approved:
                approved = heuristic_approved
        else:
            approved = heuristic_approved

        estimated_tokens = self._estimate_review_tokens(patch, review_text)
        allow_estimate = not attempted_live
        tokens_used, cost_usd = self._record_usage_from_response(
            model_name=chat_response.model if chat_response else model_config.name,
            task_type=TaskType.REVIEW,
            cost_per_1k=model_config.cost_per_1k_tokens,
            response=chat_response,
            estimated_tokens=estimated_tokens,
            allow_estimate=allow_estimate,
        )

        model_used = chat_response.model if chat_response else model_config.name
        return ReviewResponse(
            approved=approved,
            issues=issues,
            suggestions=suggestions,
            model_used=model_used,
            cost_usd=cost_usd,
            review=review_text,
            tokens_used=tokens_used,
        )

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------
    def diagnose_failure(
        self,
        test_output: str,
        patch: GeneratedPatch,
        context: Optional[Dict[str, Any]] = None,
        progress: Optional[Progress] = None,
    ) -> str:
        """Summarise a failing test run and provide next steps."""

        analysis_context = {"task_type": TaskType.DIAGNOSIS.value, **(context or {})}
        model_config = self._select_model(
            "Diagnose test failure", analysis_context, None
        )

        lines = test_output.splitlines()
        max_output_lines = 100
        if len(lines) > max_output_lines:
            trimmed_output = "\n".join(lines[-max_output_lines:])
            truncated_output = (
                f"[... {len(lines) - max_output_lines} lines omitted ...]\n{trimmed_output}"
            )
        else:
            trimmed_output = test_output
            truncated_output = test_output

        insights = []
        if "AssertionError" in test_output:
            insights.append("Assertion failure detected – expected vs actual mismatch.")
        if "ImportError" in test_output or "ModuleNotFoundError" in test_output:
            insights.append("Import error detected – check dependencies or module paths.")
        if "timeout" in test_output.lower():
            insights.append("Test timeout observed – investigate long running operations.")

        if context and context.get("previous_failures"):
            insights.append(
                f"Failure has occurred {context['previous_failures']} time(s) recently."
            )

        recommendations: List[str] = [
            "Review stack traces for the exact failure point.",
            "Verify recent changes align with test expectations.",
            "Re-run the impacted test locally to reproduce.",
        ]
        if any("assertion" in insight.lower() for insight in insights):
            recommendations.append("Double-check the expected values used in assertions.")
        if any("import" in insight.lower() for insight in insights):
            recommendations.append("Ensure required packages are installed and import paths are correct.")
        if any("timeout" in insight.lower() for insight in insights):
            recommendations.append("Look for infinite loops or slow operations introduced by the patch.")
        if context and context.get("rerun_command"):
            recommendations.append(
                f"Rerun the suite with: {context['rerun_command']}"
            )

        token_estimate = max(len(trimmed_output.split()), 80)
        tokens_used, cost_usd = self._record_usage_from_response(
            model_name=model_config.name,
            task_type=TaskType.DIAGNOSIS,
            cost_per_1k=model_config.cost_per_1k_tokens,
            response=None,
            estimated_tokens=token_estimate,
            allow_estimate=True,
        )

        insights_block = "\n".join(f"• {text}" for text in insights) or "No specific patterns detected."
        recommendation_block = "\n".join(
            f"{idx}. {step}" for idx, step in enumerate(dict.fromkeys(recommendations), 1)
        )
        patch_summary = (
            f"Files Changed: {', '.join(patch.files_changed) or 'Unknown'}\n"
            f"Additions: {patch.additions} | Deletions: {patch.deletions}"
        )

        diagnosis = (
            "Test Failure Diagnosis:\n\n"
            f"Test Output Summary:\n{truncated_output}\n\n"
            f"Patch Context:\n{patch_summary}\n\n"
            f"Insights:\n{insights_block}\n\n"
            f"Suggested Actions:\n{recommendation_block}\n\n"
            f"Estimated Analysis Cost: ${cost_usd:.4f}"
        )
        return diagnosis

    # ------------------------------------------------------------------
    # Status helpers
    # ------------------------------------------------------------------
    def get_status(self) -> Dict[str, Any]:
        """Expose current budget and model status."""

        api_key = self.config.abacus.api_key
        api_configured = bool(api_key and api_key.strip())

        return {
            "budget": self.cost_guard.get_status(),
            "models": {
                "fast": [m.name for m in self.model_router.models[ModelTier.FAST]],
                "coding": [m.name for m in self.model_router.models[ModelTier.CODING]],
                "planning": [m.name for m in self.model_router.models[ModelTier.PLANNING]],
            },
            "api_configured": api_configured,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _select_model(
        self,
        description: str,
        context: Dict[str, Any],
        force_model: Optional[str],
        force_tier: Optional[ModelTier] = None,
    ) -> ModelConfig:
        if force_model:
            model = self._find_model_by_name(force_model)
            if not model:
                raise ValueError(f"Model '{force_model}' not found in configuration")
            return model
        budget_remaining = self.cost_guard.get_remaining_budget()
        return self.model_router.select_model(
            description,
            context=context,
            force_tier=force_tier,
            budget_remaining=budget_remaining,
        )

    def _escalate_model(self, current_model: ModelConfig) -> Optional[ModelConfig]:
        escalated = self.model_router.get_escalated_model(current_model, reason="failure")
        if escalated:
            logger.info(
                "Escalating from %s to %s", current_model.name, escalated.name
            )
        return escalated

    def _ensure_code_plan(
        self, plan: Union[CodePlan, str, Mapping[str, Any]]
    ) -> Tuple[CodePlan, str]:
        if plan is None:
            raise ValueError("Plan is required")

        if isinstance(plan, CodePlan):
            description = f"{plan.title}\n\n{plan.description}".strip()
            return plan, description

        nested_plan = getattr(plan, "plan", None)
        if isinstance(nested_plan, CodePlan):
            normalized = nested_plan
            description = f"{normalized.title}\n\n{normalized.description}".strip()
            return normalized, description

        if isinstance(plan, Mapping):
            plan_dict = dict(plan)
            title = (
                str(plan_dict.get("title") or "Generated Plan").strip()
                or "Generated Plan"
            )
            description = str(
                plan_dict.get("description") or "Implementation plan"
            ).strip()
            file_changes: List[FileChange] = []
            for item in plan_dict.get("file_changes", []) or []:
                if isinstance(item, FileChange):
                    file_changes.append(item)
                    continue
                if not isinstance(item, Mapping):
                    continue
                item_dict = dict(item)
                path = str(item_dict.get("path") or "").strip()
                if not path:
                    continue
                action = str(item_dict.get("action") or "modify")
                reason = str(item_dict.get("reason") or "")
                estimated_raw = item_dict.get("estimated_lines", 0)
                try:
                    estimated_lines = int(estimated_raw)
                except (TypeError, ValueError):
                    estimated_lines = 0
                file_changes.append(
                    FileChange(
                        path=path,
                        action=action,
                        reason=reason,
                        estimated_lines=max(estimated_lines, 0),
                    )
                )
            test_strategy = str(plan_dict.get("test_strategy") or "Standard testing")
            risks = [str(risk) for risk in plan_dict.get("risks", []) or []]
            dependencies = [
                str(dep) for dep in plan_dict.get("dependencies", []) or []
            ]
            estimated_complexity = str(
                plan_dict.get("estimated_complexity") or "medium"
            )
            normalized = CodePlan(
                title=title,
                description=description or "Implementation plan",
                file_changes=file_changes,
                test_strategy=test_strategy,
                risks=risks,
                dependencies=dependencies,
                estimated_complexity=estimated_complexity,
            )
            normalized_description = (
                f"{normalized.title}\n\n{normalized.description}"
            ).strip()
            return normalized, normalized_description

        description = str(plan).strip()
        if not description:
            raise ValueError("Plan description cannot be empty")

        minimal_plan = CodePlan(
            title="Generated Plan",
            description=description,
            file_changes=[],
            test_strategy="Standard testing",
            risks=[],
        )
        return minimal_plan, description

    def _estimate_plan_tokens(
        self,
        description: str,
        complexity: ComplexityMetrics,
        plan: Optional[CodePlan] = None,
    ) -> int:
        base = 200 + len(description.split())
        base += int(complexity.estimated_patch_size * 1.5)
        base += complexity.file_count * 40
        if complexity.security_sensitive:
            base += 120
        if plan:
            base += len(str(plan).splitlines())
        return max(base, 200)

    def _estimate_patch_tokens(
        self,
        plan: CodePlan,
        file_contents: Optional[Dict[str, str]] = None,
        patch: Optional[GeneratedPatch] = None,
    ) -> int:
        file_change_lines = sum(fc.estimated_lines for fc in plan.file_changes)
        base = 300 + file_change_lines * 3 + len(plan.description.split())
        if file_contents:
            base += sum(len(content) for content in file_contents.values()) // 20
        if patch:
            base += len(patch.diff.splitlines())
        return max(base, 250)

    def _estimate_review_tokens(self, patch: GeneratedPatch, review_text: str) -> int:
        diff_lines = len(patch.diff.splitlines()) if patch.diff else 0
        base = 150 + diff_lines + len(review_text.split())
        base += len(patch.files_changed) * 30
        return max(base, 150)

    def _record_usage_from_response(
        self,
        *,
        model_name: str,
        task_type: TaskType,
        cost_per_1k: float,
        response: Optional[ChatResponse],
        estimated_tokens: int,
        allow_estimate: bool,
    ) -> Tuple[int, float]:
        if response:
            prompt_tokens = response.prompt_tokens or max(response.total_tokens * 2 // 3, 0)
            completion_tokens = response.completion_tokens or max(
                response.total_tokens - prompt_tokens, 0
            )
            total_tokens = response.total_tokens or (prompt_tokens + completion_tokens)
        elif allow_estimate and estimated_tokens > 0:
            total_tokens = estimated_tokens
            prompt_tokens = max(int(total_tokens * 0.6), 1)
            completion_tokens = max(total_tokens - prompt_tokens, 0)
        else:
            return 0, 0.0

        if total_tokens <= 0:
            return 0, 0.0

        self.cost_guard.record_usage(
            model=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_per_1k=cost_per_1k,
            task_type=task_type.value,
        )
        cost_usd = (total_tokens / 1000.0) * cost_per_1k
        return total_tokens, cost_usd

    def _get_deployment_credentials(
        self, model: ModelConfig
    ) -> Tuple[Optional[str], Optional[DeploymentCredentials]]:
        deployments = self.config.deployments or {}
        if model.name in deployments:
            return model.name, deployments[model.name]
        tier_key = getattr(model.tier, "value", None)
        if tier_key and tier_key in deployments:
            return tier_key, deployments[tier_key]
        getter = getattr(self.config_manager, "get_deployment_credentials", None)
        if callable(getter):
            if model.name:
                creds = getter(model.name)
                if creds:
                    return model.name, creds
            if tier_key:
                creds = getter(tier_key)
                if creds:
                    return tier_key, creds
        return None, None

    def _has_deployment_for_tier(self, tier: ModelTier) -> bool:
        deployments = self.config.deployments or {}
        if tier.value in deployments:
            return True
        getter = getattr(self.config_manager, "get_deployment_credentials", None)
        if callable(getter):
            return getter(tier.value) is not None
        return False

    def _heuristic_review(
        self,
        patch: GeneratedPatch,
        *,
        test_files: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, List[str], List[str], bool]:
        context = context or {}
        issues: List[str] = []
        suggestions: List[str] = []

        total_changes = patch.additions + patch.deletions
        if total_changes > 200 or len(patch.files_changed) > 5:
            issues.append("Patch is large and may require manual review.")
        if 0 < patch.confidence < 0.5:
            issues.append("Model reported low confidence in the generated patch.")
        if context.get("security_sensitive"):
            issues.append("Security sensitive change – ensure threat modelling is complete.")

        has_test_file = any("test" in path.lower() for path in patch.files_changed)
        if test_files:
            has_test_file = True
        if not has_test_file:
            suggestions.append("Add or update automated tests to cover these changes.")
        if context.get("requires_docs"):
            suggestions.append("Update related documentation to describe the change.")

        review_lines = [
            "Patch Review Summary:",
            f"Files changed: {', '.join(patch.files_changed) or 'None'}",
            f"Additions: {patch.additions} | Deletions: {patch.deletions}",
            f"Confidence: {patch.confidence:.2f}",
        ]
        if test_files:
            review_lines.append(f"Test files provided: {', '.join(test_files)}")
        elif has_test_file:
            review_lines.append("Detected updates to existing test files.")
        else:
            review_lines.append("No explicit test files provided.")
        if suggestions:
            review_lines.append("")
            review_lines.append("Suggested Actions:")
            review_lines.extend(f"- {s}" for s in suggestions)
        if issues:
            review_lines.append("")
            review_lines.append("Concerns:")
            review_lines.extend(f"- {issue}" for issue in issues)

        review_text = "\n".join(review_lines)
        approved = not issues
        return review_text, issues, suggestions, approved

    @contextmanager
    def _progress_stage(
        self,
        progress: Optional[Progress],
        task_id: Optional[TaskID],
        description: str,
        advance: int,
    ) -> Iterator[None]:
        if progress and task_id is not None:
            progress.update(task_id, description=description)
        try:
            yield
        finally:
            if progress and task_id is not None:
                progress.advance(task_id, advance)

    def _find_model_by_name(self, name: str) -> Optional[ModelConfig]:
        for tier_models in self.model_router.models.values():
            for model in tier_models:
                if model.name == name:
                    return model
        return None
