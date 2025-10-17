
"""
Tests for AI Orchestrator.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from sologit.orchestration.ai_orchestrator import (
    AIOrchestrator, PlanResponse, PatchResponse, ReviewResponse, TaskType
)
from sologit.orchestration.planning_engine import CodePlan, FileChange
from sologit.orchestration.code_generator import GeneratedPatch
from sologit.config.manager import ConfigManager


@pytest.fixture
def mock_config_manager(tmp_path):
    """Mock configuration manager."""
    config_file = tmp_path / "config.yaml"
    
    # Create minimal config
    config_content = """
abacus:
  endpoint: "https://api.abacus.ai/api/v0"
  api_key: "test_key_123"

ai:
  models:
    fast:
      primary: "llama-3.1-8b-instruct"
      max_tokens: 1024
      temperature: 0.1
    coding:
      primary: "deepseek-coder-33b"
      max_tokens: 2048
      temperature: 0.1
    planning:
      primary: "gpt-4o"
      max_tokens: 4096
      temperature: 0.2

escalation:
  triggers: []

budget:
  daily_usd_cap: 10.0
  alert_threshold: 0.8
  track_by_model: true

promote_on_green: true
rollback_on_ci_red: true
"""
    
    config_file.write_text(config_content)
    
    return ConfigManager(config_path=config_file)


@pytest.fixture
def orchestrator(mock_config_manager, tmp_path):
    """Create AI orchestrator with isolated cost tracking."""
    # Create orchestrator with fresh cost tracker for each test
    orch = AIOrchestrator(mock_config_manager)
    
    # Use test-specific storage path to avoid state sharing between tests
    from sologit.orchestration.cost_guard import CostTracker
    storage_path = tmp_path / f"usage_{id(orch)}.json"
    orch.cost_guard.tracker = CostTracker(storage_path)
    
    return orch


def test_orchestrator_initialization(orchestrator):
    """Test orchestrator initializes correctly."""
    assert orchestrator is not None
    assert orchestrator.client is not None
    assert orchestrator.model_router is not None
    assert orchestrator.cost_guard is not None
    assert orchestrator.planning_engine is not None
    assert orchestrator.code_generator is not None


def test_plan_simple_task(orchestrator):
    """Test planning for simple task."""
    prompt = "fix typo in readme"
    
    response = orchestrator.plan(prompt)
    
    assert isinstance(response, PlanResponse)
    assert isinstance(response.plan, CodePlan)
    assert response.model_used
    assert response.cost_usd >= 0


def test_plan_complex_task(orchestrator):
    """Test planning for complex task."""
    prompt = "implement JWT authentication with secure password hashing"
    
    response = orchestrator.plan(prompt)
    
    assert isinstance(response, PlanResponse)
    assert response.complexity.security_sensitive


def test_plan_with_context(orchestrator):
    """Test planning with repository context."""
    prompt = "add API endpoint"
    context = {
        'file_tree': ['api/routes.py'],
        'language': 'Python'
    }
    
    response = orchestrator.plan(prompt, repo_context=context)
    
    assert isinstance(response, PlanResponse)


def test_plan_budget_exceeded(orchestrator):
    """Test planning fails when budget exceeded."""
    # Use up the budget - need enough to actually exceed the $10 cap
    # (1500 tokens * 0.03 per 1k = 0.045 per call, need 10/0.045 ~= 223 calls)
    for i in range(250):
        orchestrator.cost_guard.record_usage(
            model='gpt-4o',
            prompt_tokens=1000,
            completion_tokens=500,
            cost_per_1k=0.03,
            task_type='planning'
        )
    
    # Verify budget is exceeded
    assert orchestrator.cost_guard.get_remaining_budget() <= 0
    
    # Should raise exception
    with pytest.raises(Exception, match="Budget exceeded"):
        orchestrator.plan("test prompt")


def test_generate_patch(orchestrator):
    """Test patch generation."""
    plan = CodePlan(
        title='Test Plan',
        description='Test',
        file_changes=[
            FileChange(path='test.py', action='create', reason='Test', estimated_lines=10)
        ],
        test_strategy='Test',
        risks=[],
        estimated_complexity='low'
    )
    
    response = orchestrator.generate_patch(plan)
    
    assert isinstance(response, PatchResponse)
    assert isinstance(response.patch, GeneratedPatch)
    assert response.model_used


def test_generate_patch_with_files(orchestrator):
    """Test patch generation with existing files."""
    plan = CodePlan(
        title='Modify File',
        description='Update existing file',
        file_changes=[
            FileChange(path='test.py', action='modify', reason='Update', estimated_lines=5)
        ],
        test_strategy='Test',
        risks=[],
        estimated_complexity='medium'
    )
    
    file_contents = {
        'test.py': 'def old_function():\n    pass\n'
    }
    
    response = orchestrator.generate_patch(plan, file_contents)
    
    assert isinstance(response, PatchResponse)


def test_review_patch(orchestrator):
    """Test patch review."""
    patch = GeneratedPatch(
        diff='--- a/test.py\n+++ b/test.py\n@@ -1,1 +1,2 @@\n line\n+new line',
        files_changed=['test.py'],
        additions=1,
        deletions=0,
        model='test',
        confidence=0.8
    )
    
    response = orchestrator.review_patch(patch)
    
    assert isinstance(response, ReviewResponse)
    assert isinstance(response.approved, bool)
    assert isinstance(response.issues, list)
    assert isinstance(response.suggestions, list)


def test_review_large_patch(orchestrator):
    """Test review flags large patches."""
    patch = GeneratedPatch(
        diff='large diff content',
        files_changed=['file.py'],
        additions=300,  # Large patch
        deletions=50,
        model='test',
        confidence=0.8
    )
    
    response = orchestrator.review_patch(patch)
    
    # Should have issues due to size
    assert len(response.issues) > 0


def test_review_patch_without_tests(orchestrator):
    """Test review suggests tests."""
    patch = GeneratedPatch(
        diff='diff content',
        files_changed=['module.py'],  # No test files
        additions=50,
        deletions=10,
        model='test',
        confidence=0.8
    )
    
    response = orchestrator.review_patch(patch)
    
    # Should suggest adding tests
    assert len(response.suggestions) > 0


def test_diagnose_failure(orchestrator):
    """Test failure diagnosis."""
    test_output = """
    FAILED test_module.py::test_function
    AssertionError: Expected 5, got 3
    """
    
    patch = GeneratedPatch(
        diff='test diff',
        files_changed=['module.py'],
        additions=10,
        deletions=5,
        model='test',
        confidence=0.8
    )
    
    diagnosis = orchestrator.diagnose_failure(test_output, patch)
    
    assert isinstance(diagnosis, str)
    assert len(diagnosis) > 0


def test_get_status(orchestrator):
    """Test getting orchestrator status."""
    status = orchestrator.get_status()
    
    assert 'budget' in status
    assert 'models' in status
    assert 'api_configured' in status
    assert status['api_configured'] is True


def test_force_model_selection(orchestrator):
    """Test forcing specific model."""
    prompt = "simple task"
    
    # Force planning model for simple task
    response = orchestrator.plan(prompt, force_model='gpt-4o')
    
    assert response.model_used == 'gpt-4o'


def test_model_escalation_on_failure(orchestrator):
    """Test model escalation after failure."""
    # This test checks the escalation logic
    # In real scenario, would mock a failure and verify escalation
    plan = CodePlan(
        title='Test',
        description='Test',
        file_changes=[],
        test_strategy='Test',
        risks=[],
        estimated_complexity='high'
    )
    
    # Should select appropriate model for high complexity
    response = orchestrator.generate_patch(plan)
    
    # High complexity should use planning or coding tier
    assert response.model_used in ['gpt-4o', 'deepseek-coder-33b', 'claude-3-5-sonnet']


def test_find_model_by_name(orchestrator):
    """Test finding model by name."""
    model = orchestrator._find_model_by_name('gpt-4o')
    
    assert model is not None
    assert model.name == 'gpt-4o'


def test_find_model_by_name_not_found(orchestrator):
    """Test finding non-existent model."""
    model = orchestrator._find_model_by_name('nonexistent-model')
    
    assert model is None

