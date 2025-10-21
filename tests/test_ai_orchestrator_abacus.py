import json
from pathlib import Path

import pytest

from sologit.api.client import AbacusAPIError, AbacusClient, ChatResponse
from sologit.config.manager import ConfigManager
from sologit.orchestration.ai_orchestrator import AIOrchestrator
from sologit.orchestration.cost_guard import CostTracker
from sologit.orchestration.planning_engine import CodePlan, FileChange


@pytest.fixture
def config_manager(tmp_path: Path) -> ConfigManager:
    config_path = tmp_path / "config.yaml"
    manager = ConfigManager(config_path=config_path)
    manager.set_abacus_credentials(
        api_key="test-key",
        endpoint="https://api.abacus.ai/api/v0",
    )
    manager.set_deployment_credentials('planning', 'dep-plan', 'token-plan')
    manager.set_deployment_credentials('coding', 'dep-code', 'token-code')
    return manager


def test_plan_records_usage_from_abacus(monkeypatch, config_manager, tmp_path):
    call_history = []

    def fake_chat(self, messages, model, **kwargs):
        call_history.append(kwargs)
        plan_payload = {
            'title': 'Add Feature',
            'description': 'Implement new feature',
            'file_changes': [
                {
                    'path': 'module.py',
                    'action': 'modify',
                    'reason': 'Implement feature',
                    'estimated_lines': 10,
                }
            ],
            'test_strategy': 'Add tests',
            'risks': [],
            'estimated_complexity': 'medium',
        }
        return ChatResponse(
            content=json.dumps(plan_payload),
            model='abacus-planner',
            prompt_tokens=120,
            completion_tokens=80,
            total_tokens=200,
            finish_reason='stop',
        )

    monkeypatch.setattr(AbacusClient, 'chat', fake_chat)

    orchestrator = AIOrchestrator(config_manager)
    orchestrator.cost_guard.tracker = CostTracker(tmp_path / 'usage_plan.json')

    response = orchestrator.plan("Implement feature")

    assert call_history[0]['deployment'] == 'planning'
    assert call_history[0]['deployment_id'] == 'dep-plan'
    assert call_history[0]['deployment_token'] == 'token-plan'
    assert response.model_used == 'abacus-planner'
    total_cost = orchestrator.cost_guard.tracker.current_usage.total_cost_usd
    assert response.cost_usd == pytest.approx(total_cost, rel=1e-6)
    assert total_cost > 0
    assert orchestrator.cost_guard.tracker.current_usage.total_tokens == 200


def test_generate_patch_records_usage(monkeypatch, config_manager, tmp_path):
    call_history = []

    def fake_chat(self, messages, model, **kwargs):
        call_history.append(kwargs)
        diff = """```diff\n--- a/test.py\n+++ b/test.py\n+print('hi')\n```"""
        return ChatResponse(
            content=diff,
            model='abacus-coder',
            prompt_tokens=100,
            completion_tokens=80,
            total_tokens=180,
            finish_reason='stop',
        )

    monkeypatch.setattr(AbacusClient, 'chat', fake_chat)

    orchestrator = AIOrchestrator(config_manager)
    orchestrator.cost_guard.tracker = CostTracker(tmp_path / 'usage_patch.json')

    plan = CodePlan(
        title='Test Plan',
        description='Do work',
        file_changes=[
            FileChange(path='test.py', action='create', reason='New file', estimated_lines=5)
        ],
        test_strategy='Add tests',
        risks=[],
        estimated_complexity='low',
    )

    response = orchestrator.generate_patch(plan)

    assert call_history[0]['deployment'] == 'coding'
    assert call_history[0]['deployment_id'] == 'dep-code'
    assert call_history[0]['deployment_token'] == 'token-code'
    assert response.model_used == 'abacus-coder'
    assert orchestrator.cost_guard.tracker.current_usage.total_tokens == 180
    assert "print('hi')" in response.patch.diff


def test_plan_falls_back_on_abacus_error(monkeypatch, config_manager, tmp_path):
    def fake_chat(self, messages, model, **kwargs):
        raise AbacusAPIError('rate limit')

    monkeypatch.setattr(AbacusClient, 'chat', fake_chat)

    orchestrator = AIOrchestrator(config_manager)
    orchestrator.cost_guard.tracker = CostTracker(tmp_path / 'usage_fail_plan.json')

    response = orchestrator.plan("Implement feature")

    assert response.cost_usd == 0.0
    assert orchestrator.cost_guard.tracker.current_usage.total_tokens == 0


def test_generate_patch_falls_back_on_abacus_error(monkeypatch, config_manager, tmp_path):
    def fake_chat(self, messages, model, **kwargs):
        raise AbacusAPIError('rate limit')

    monkeypatch.setattr(AbacusClient, 'chat', fake_chat)

    orchestrator = AIOrchestrator(config_manager)
    orchestrator.cost_guard.tracker = CostTracker(tmp_path / 'usage_fail_patch.json')

    plan = CodePlan(
        title='Test Plan',
        description='Do work',
        file_changes=[
            FileChange(path='test.py', action='create', reason='New file', estimated_lines=5)
        ],
        test_strategy='Add tests',
        risks=[],
        estimated_complexity='low',
    )

    response = orchestrator.generate_patch(plan)

    assert response.cost_usd == 0.0
    assert orchestrator.cost_guard.tracker.current_usage.total_tokens == 0
