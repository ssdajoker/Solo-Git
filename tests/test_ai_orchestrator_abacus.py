import json
from pathlib import Path
from unittest.mock import Mock

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
    return manager


@pytest.fixture
def fake_abacus_client():
    return Mock(spec=AbacusClient)


def test_plan_records_usage_from_abacus(config_manager, tmp_path, fake_abacus_client):
    call_history = []

    config_manager.set_deployment_credentials('llama-3.1-8b-instruct', 'dep-plan', 'token-plan')

    def fake_chat(*_, **kwargs):
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
            model='llama-3.1-8b-instruct',
            prompt_tokens=120,
            completion_tokens=80,
            total_tokens=200,
            finish_reason='stop',
        )

    fake_abacus_client.chat.side_effect = fake_chat

    orchestrator = AIOrchestrator(config_manager, abacus_client=fake_abacus_client)
    orchestrator.cost_guard.tracker = CostTracker(tmp_path / 'usage_plan.json')

    response = orchestrator.plan("Implement feature")

    assert call_history[0]['deployment'] == 'llama-3.1-8b-instruct'
    assert call_history[0]['deployment_id'] == 'dep-plan'
    assert call_history[0]['deployment_token'] == 'token-plan'
    assert response.model_used == 'llama-3.1-8b-instruct'
    total_cost = orchestrator.cost_guard.tracker.current_usage.total_cost_usd
    assert response.cost_usd == pytest.approx(total_cost, rel=1e-6)
    assert total_cost > 0
    assert orchestrator.cost_guard.tracker.current_usage.total_tokens == 200


def test_generate_patch_records_usage(config_manager, tmp_path, fake_abacus_client):
    call_history = []

    config_manager.set_deployment_credentials('llama-3.1-8b-instruct', 'dep-code', 'token-code')

    def fake_chat(*_, **kwargs):
        call_history.append(kwargs)
        diff = """```diff\n--- a/test.py\n+++ b/test.py\n+print('hi')\n```"""
        return ChatResponse(
            content=diff,
            model='llama-3.1-8b-instruct',
            prompt_tokens=100,
            completion_tokens=80,
            total_tokens=180,
            finish_reason='stop',
        )

    fake_abacus_client.chat.side_effect = fake_chat

    orchestrator = AIOrchestrator(config_manager, abacus_client=fake_abacus_client)
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

    assert call_history[0]['deployment'] == 'llama-3.1-8b-instruct'
    assert call_history[0]['deployment_id'] == 'dep-code'
    assert call_history[0]['deployment_token'] == 'token-code'
    assert response.model_used == 'llama-3.1-8b-instruct'
    assert orchestrator.cost_guard.tracker.current_usage.total_tokens > 0
    assert "print('hi')" in response.patch.diff


def test_plan_falls_back_on_abacus_error(config_manager, tmp_path, fake_abacus_client):
    def fake_chat(*_, **kwargs):
        raise AbacusAPIError('rate limit')

    fake_abacus_client.chat.side_effect = fake_chat

    orchestrator = AIOrchestrator(config_manager, abacus_client=fake_abacus_client)
    orchestrator.cost_guard.tracker = CostTracker(tmp_path / 'usage_fail_plan.json')

    response = orchestrator.plan("Implement feature")

    assert not fake_abacus_client.chat.called
    assert isinstance(response.plan, str)


def test_generate_patch_falls_back_on_abacus_error(config_manager, tmp_path, fake_abacus_client):
    def fake_chat(*_, **kwargs):
        raise AbacusAPIError('rate limit')

    fake_abacus_client.chat.side_effect = fake_chat

    orchestrator = AIOrchestrator(config_manager, abacus_client=fake_abacus_client)
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

    assert not fake_abacus_client.chat.called
    assert isinstance(response.patch.diff, str)
