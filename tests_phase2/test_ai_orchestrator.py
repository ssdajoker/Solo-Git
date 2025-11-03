from unittest.mock import Mock, patch

import pytest

from sologit.api.client import ChatResponse
from sologit.config.manager import DeploymentCredentials, SoloGitConfig
from sologit.orchestration.ai_orchestrator import AIOrchestrator, PlanResponse
from sologit.orchestration.model_router import ComplexityMetrics, ModelConfig, ModelTier
from sologit.orchestration.planning_engine import CodePlan, FileChange


@pytest.fixture
def orchestrator_fixture():
    config = SoloGitConfig()
    config.deployments = {
        "model-A": DeploymentCredentials("dep-1", "tok-1"),
        "model-B": DeploymentCredentials("dep-2", "tok-2"),
    }
    config_manager = Mock()
    config_manager.get_config.return_value = config

    cost_guard = Mock()
    cost_guard.check_budget.return_value = True
    cost_guard.get_remaining_budget.return_value = 5.0

    model_router = Mock()
    model_router.models = {
        ModelTier.FAST: [ModelConfig(name="fast", tier=ModelTier.FAST, max_tokens=1000, temperature=0.1, cost_per_1k_tokens=0.1)],
        ModelTier.CODING: [ModelConfig(name="model-A", tier=ModelTier.CODING, max_tokens=2000, temperature=0.1, cost_per_1k_tokens=0.2)],
        ModelTier.PLANNING: [ModelConfig(name="model-B", tier=ModelTier.PLANNING, max_tokens=3000, temperature=0.1, cost_per_1k_tokens=0.3)],
    }
    model_router.analyze_complexity.return_value = ComplexityMetrics(
        score=0.2,
        security_sensitive=False,
        estimated_patch_size=10,
        file_count=1,
        has_tests=True,
        requires_architecture=False,
    )
    model_router.select_model.return_value = ModelConfig(
        name="model-A",
        tier=ModelTier.CODING,
        max_tokens=2000,
        temperature=0.1,
        cost_per_1k_tokens=0.2,
    )

    plan = CodePlan(
        title="Add feature",
        description="Implement feature",
        file_changes=[FileChange(path="app.py", action="modify", reason="update logic")],
        test_strategy="pytest",
        risks=["regression"],
    )
    planning_engine = Mock()
    planning_engine.generate_plan.return_value = plan
    planning_engine.last_response = ChatResponse(
        content="Plan",
        model="model-A",
        prompt_tokens=30,
        completion_tokens=60,
    )

    code_generator = Mock()

    with patch("sologit.orchestration.ai_orchestrator.CostGuard", return_value=cost_guard), patch(
        "sologit.orchestration.ai_orchestrator.ModelRouter", return_value=model_router
    ), patch("sologit.orchestration.ai_orchestrator.PlanningEngine", return_value=planning_engine), patch(
        "sologit.orchestration.ai_orchestrator.CodeGenerator", return_value=code_generator
    ):
        orchestrator = AIOrchestrator(config_manager)

    return orchestrator, cost_guard, model_router, planning_engine, plan


def test_plan_happy_path(orchestrator_fixture):
    orchestrator, cost_guard, model_router, planning_engine, _ = orchestrator_fixture
    response = orchestrator.plan("Implement feature")

    assert isinstance(response, PlanResponse)
    assert "File Changes" in response.plan
    cost_guard.record_usage.assert_called_once()
    planning_engine.generate_plan.assert_called_once()


def test_plan_escalates_on_failure(orchestrator_fixture):
    orchestrator, cost_guard, model_router, planning_engine, plan = orchestrator_fixture
    escalated_model = ModelConfig(
        name="model-B",
        tier=ModelTier.PLANNING,
        max_tokens=4000,
        temperature=0.1,
        cost_per_1k_tokens=0.25,
    )
    model_router.select_model.return_value = ModelConfig(
        name="model-A",
        tier=ModelTier.CODING,
        max_tokens=2000,
        temperature=0.1,
        cost_per_1k_tokens=0.2,
    )
    model_router.escalate_model.return_value = escalated_model
    cost_guard.check_budget.side_effect = [True, True]
    planning_engine.generate_plan.side_effect = [RuntimeError("fail"), plan]

    response = orchestrator.plan("Implement feature", escalate_on_failure=True)

    assert response.model_used == "model-B"
    assert planning_engine.generate_plan.call_count == 2
    model_router.escalate_model.assert_called_once()


def test_plan_raises_when_budget_exceeded(orchestrator_fixture):
    orchestrator, cost_guard, _, _, _ = orchestrator_fixture
    cost_guard.check_budget.return_value = False

    with pytest.raises(RuntimeError, match="Insufficient budget"):
        orchestrator.plan("Implement feature")


def test_plan_with_force_model_validates_name(orchestrator_fixture):
    orchestrator, _, model_router, _, _ = orchestrator_fixture
    model_router.models = {tier: [] for tier in ModelTier}

    with pytest.raises(ValueError, match="Model 'unknown'"):
        orchestrator.plan("Implement", force_model="unknown")


def test_get_status_includes_budget(orchestrator_fixture):
    orchestrator, cost_guard, model_router, _, _ = orchestrator_fixture
    cost_guard.get_status.return_value = {"remaining": 5}

    status = orchestrator.get_status()

    assert status["budget"] == {"remaining": 5}
    assert "fast" in status["models"]


def test_get_deployment_credentials_filters_missing(orchestrator_fixture):
    orchestrator, _, _, _, _ = orchestrator_fixture
    creds = orchestrator._get_deployment_credentials("model-A")
    assert creds == {"deployment_id": "dep-1", "deployment_token": "tok-1"}
    assert orchestrator._get_deployment_credentials("missing") is None
