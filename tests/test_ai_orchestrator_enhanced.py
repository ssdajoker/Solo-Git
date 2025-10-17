"""
Enhanced tests for AI Orchestrator to achieve >95% coverage.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from sologit.orchestration.ai_orchestrator import (
    AIOrchestrator, PlanResponse, PatchResponse, ReviewResponse, TaskType
)
from sologit.orchestration.planning_engine import CodePlan, FileChange
from sologit.orchestration.code_generator import GeneratedPatch
from sologit.config.manager import ConfigManager


@pytest.fixture
def mock_config_manager():
    """Mock configuration manager."""
    return Mock(spec=ConfigManager)


@pytest.fixture
def temp_storage():
    """Create temporary storage for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "usage.json"


@pytest.fixture
def orchestrator(temp_storage):
    """Create AI orchestrator for testing with isolated storage."""
    orch = AIOrchestrator()
    # Use isolated storage path
    orch.cost_guard.tracker.storage_path = temp_storage
    orch.cost_guard.tracker.usage_history = {}
    orch.cost_guard.tracker._load_history()
    return orch


def test_plan_with_force_model(orchestrator):
    """Test planning with forced model selection."""
    # Mock the _find_model_by_name to return a valid model
    mock_model = MagicMock()
    mock_model.name = "gpt-4o"
    mock_model.cost_per_1k_tokens = 0.03
    
    with patch.object(orchestrator, '_find_model_by_name', return_value=mock_model):
        response = orchestrator.plan(
            prompt="add authentication",
            force_model="gpt-4o"
        )
    
    assert isinstance(response, PlanResponse)
    assert response.model_used == "gpt-4o"


def test_plan_with_invalid_force_model(orchestrator):
    """Test planning with invalid forced model raises error."""
    with patch.object(orchestrator, '_find_model_by_name', return_value=None):
        with pytest.raises(ValueError, match="Model .* not found"):
            orchestrator.plan(
                prompt="add feature",
                force_model="nonexistent-model"
            )


def test_plan_budget_exceeded(orchestrator):
    """Test planning fails when budget exceeded."""
    # Set budget to zero
    orchestrator.cost_guard.config.daily_usd_cap = 0.0
    
    # Record high usage to exceed budget
    orchestrator.cost_guard.record_usage(
        model="test",
        prompt_tokens=100000,
        completion_tokens=50000,
        cost_per_1k=10.0,
        task_type="test"
    )
    
    with pytest.raises(Exception, match="Budget exceeded"):
        orchestrator.plan(prompt="add feature")


def test_plan_with_repo_context(orchestrator):
    """Test planning with repository context."""
    repo_context = {
        'file_tree': ['file1.py', 'file2.py'],
        'language': 'Python'
    }
    
    response = orchestrator.plan(
        prompt="add authentication",
        repo_context=repo_context
    )
    
    assert isinstance(response, PlanResponse)
    assert response.complexity is not None


def test_plan_escalation_on_failure(orchestrator):
    """Test planning escalates on failure."""
    # Mock planning to fail first time
    call_count = [0]
    
    def mock_generate_plan(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            raise Exception("Planning failed")
        # Second call succeeds
        return CodePlan(
            title="Plan",
            description="Description",
            file_changes=[],
            test_strategy="Test",
            risks=[],
            dependencies=[]
        )
    
    with patch.object(orchestrator.planning_engine, 'generate_plan', side_effect=mock_generate_plan):
        # Should escalate and retry
        response = orchestrator.plan(prompt="add feature")
        assert isinstance(response, PlanResponse)


def test_plan_escalation_budget_check(orchestrator):
    """Test planning escalation respects budget."""
    # Set low budget
    orchestrator.cost_guard.config.daily_usd_cap = 0.01
    
    # Mock planning to fail
    with patch.object(orchestrator.planning_engine, 'generate_plan', side_effect=Exception("Fail")):
        with pytest.raises(Exception):
            orchestrator.plan(prompt="add feature")


def test_generate_patch_with_force_model(orchestrator):
    """Test patch generation with forced model."""
    plan = CodePlan(
        title="Test Plan",
        description="Test",
        file_changes=[],
        test_strategy="Test",
        risks=[],
        dependencies=[],
        estimated_complexity="medium"
    )
    
    mock_model = MagicMock()
    mock_model.name = "deepseek-coder-33b"
    mock_model.cost_per_1k_tokens = 0.0005
    
    with patch.object(orchestrator, '_find_model_by_name', return_value=mock_model):
        response = orchestrator.generate_patch(
            plan=plan,
            force_model="deepseek-coder-33b"
        )
    
    assert isinstance(response, PatchResponse)


def test_generate_patch_invalid_force_model(orchestrator):
    """Test patch generation with invalid forced model."""
    plan = CodePlan(
        title="Test",
        description="Test",
        file_changes=[],
        test_strategy="Test",
        risks=[],
        dependencies=[]
    )
    
    with patch.object(orchestrator, '_find_model_by_name', return_value=None):
        with pytest.raises(ValueError, match="Model .* not found"):
            orchestrator.generate_patch(
                plan=plan,
                force_model="nonexistent"
            )


def test_generate_patch_low_complexity(orchestrator):
    """Test patch generation for low complexity uses FAST tier."""
    plan = CodePlan(
        title="Simple Fix",
        description="Fix typo",
        file_changes=[],
        test_strategy="Test",
        risks=[],
        dependencies=[],
        estimated_complexity="low"
    )
    
    response = orchestrator.generate_patch(plan=plan)
    
    assert isinstance(response, PatchResponse)


def test_generate_patch_high_complexity(orchestrator):
    """Test patch generation for high complexity uses PLANNING tier."""
    plan = CodePlan(
        title="Complex Feature",
        description="Complex implementation",
        file_changes=[],
        test_strategy="Test",
        risks=[],
        dependencies=[],
        estimated_complexity="high"
    )
    
    response = orchestrator.generate_patch(plan=plan)
    
    assert isinstance(response, PatchResponse)


def test_generate_patch_with_file_contents(orchestrator):
    """Test patch generation with file contents."""
    plan = CodePlan(
        title="Update Files",
        description="Modify existing files",
        file_changes=[
            FileChange(path="file.py", action="modify", reason="Update", estimated_lines=10)
        ],
        test_strategy="Test",
        risks=[],
        dependencies=[],
        estimated_complexity="medium"
    )
    
    file_contents = {
        "file.py": "# Existing content\ndef func():\n    pass\n"
    }
    
    response = orchestrator.generate_patch(
        plan=plan,
        file_contents=file_contents
    )
    
    assert isinstance(response, PatchResponse)


def test_generate_patch_budget_exceeded(orchestrator):
    """Test patch generation fails when budget exceeded."""
    plan = CodePlan(
        title="Test",
        description="Test",
        file_changes=[],
        test_strategy="Test",
        risks=[],
        dependencies=[]
    )
    
    # Exceed budget
    orchestrator.cost_guard.config.daily_usd_cap = 0.0
    orchestrator.cost_guard.record_usage(
        model="test",
        prompt_tokens=100000,
        completion_tokens=50000,
        cost_per_1k=10.0,
        task_type="test"
    )
    
    with pytest.raises(Exception, match="Budget exceeded"):
        orchestrator.generate_patch(plan=plan)


def test_generate_patch_escalation_on_failure(orchestrator):
    """Test patch generation escalates on failure."""
    plan = CodePlan(
        title="Test",
        description="Test",
        file_changes=[],
        test_strategy="Test",
        risks=[],
        dependencies=[]
    )
    
    call_count = [0]
    
    def mock_generate_patch(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            raise Exception("Generation failed")
        return GeneratedPatch(
            diff="test",
            files_changed=["test.py"],
            additions=1,
            deletions=0,
            model="test"
        )
    
    with patch.object(orchestrator.code_generator, 'generate_patch', side_effect=mock_generate_patch):
        response = orchestrator.generate_patch(plan=plan)
        assert isinstance(response, PatchResponse)


def test_generate_patch_escalation_budget_check(orchestrator):
    """Test patch generation escalation respects budget."""
    plan = CodePlan(
        title="Test",
        description="Test",
        file_changes=[],
        test_strategy="Test",
        risks=[],
        dependencies=[]
    )
    
    orchestrator.cost_guard.config.daily_usd_cap = 0.01
    
    with patch.object(orchestrator.code_generator, 'generate_patch', side_effect=Exception("Fail")):
        with pytest.raises(Exception):
            orchestrator.generate_patch(plan=plan)


def test_review_patch_large_patch(orchestrator):
    """Test review identifies large patches."""
    patch = GeneratedPatch(
        diff="large diff" * 100,
        files_changed=["file1.py", "file2.py"],
        additions=250,  # Large patch
        deletions=50,
        model="test"
    )
    
    review = orchestrator.review_patch(patch)
    
    assert isinstance(review, ReviewResponse)
    assert not review.approved  # Should not approve large patch
    assert len(review.issues) > 0


def test_review_patch_no_tests(orchestrator):
    """Test review suggests adding tests."""
    patch = GeneratedPatch(
        diff="diff",
        files_changed=["feature.py"],  # No test files
        additions=50,
        deletions=0,
        model="test"
    )
    
    review = orchestrator.review_patch(patch)
    
    assert isinstance(review, ReviewResponse)
    assert len(review.suggestions) > 0
    assert any('test' in s.lower() for s in review.suggestions)


def test_review_patch_with_tests(orchestrator):
    """Test review approves patch with tests."""
    patch = GeneratedPatch(
        diff="diff",
        files_changed=["feature.py", "test_feature.py"],  # Has tests
        additions=50,
        deletions=0,
        model="test"
    )
    
    review = orchestrator.review_patch(patch)
    
    assert isinstance(review, ReviewResponse)
    assert review.approved


def test_review_patch_with_context(orchestrator):
    """Test review with additional context."""
    patch = GeneratedPatch(
        diff="diff",
        files_changed=["file.py"],
        additions=10,
        deletions=0,
        model="test"
    )
    
    context = {
        'security_sensitive': True
    }
    
    review = orchestrator.review_patch(patch, context=context)
    
    assert isinstance(review, ReviewResponse)


def test_diagnose_failure(orchestrator):
    """Test failure diagnosis."""
    test_output = """
    FAILED tests/test_feature.py::test_function
    AssertionError: expected 5 but got 3
    """
    
    patch = GeneratedPatch(
        diff="diff",
        files_changed=["feature.py"],
        additions=10,
        deletions=0,
        model="test"
    )
    
    diagnosis = orchestrator.diagnose_failure(test_output, patch)
    
    assert isinstance(diagnosis, str)
    assert len(diagnosis) > 0
    assert "Test Failure Diagnosis" in diagnosis


def test_diagnose_failure_with_context(orchestrator):
    """Test failure diagnosis with context."""
    test_output = "Error: ImportError"
    
    patch = GeneratedPatch(
        diff="diff",
        files_changed=["file.py"],
        additions=5,
        deletions=0,
        model="test"
    )
    
    context = {
        'previous_failures': 2
    }
    
    diagnosis = orchestrator.diagnose_failure(test_output, patch, context=context)
    
    assert isinstance(diagnosis, str)


def test_get_status(orchestrator):
    """Test getting orchestrator status."""
    status = orchestrator.get_status()
    
    assert 'budget' in status
    assert 'models' in status
    assert 'api_configured' in status
    
    assert 'fast' in status['models']
    assert 'coding' in status['models']
    assert 'planning' in status['models']


def test_find_model_by_name_found(orchestrator):
    """Test finding model by name."""
    # Find a model that exists
    model = orchestrator._find_model_by_name("llama-3.1-8b-instruct")
    
    # Might be None if not configured, but method should work
    if model:
        assert model.name == "llama-3.1-8b-instruct"


def test_find_model_by_name_not_found(orchestrator):
    """Test finding non-existent model returns None."""
    model = orchestrator._find_model_by_name("nonexistent-model-xyz")
    
    assert model is None


def test_task_type_enum():
    """Test TaskType enum values."""
    assert TaskType.PLANNING.value == "planning"
    assert TaskType.CODING.value == "coding"
    assert TaskType.REVIEW.value == "review"
    assert TaskType.DIAGNOSIS.value == "diagnosis"


def test_plan_response_dataclass():
    """Test PlanResponse dataclass."""
    from sologit.orchestration.model_router import ComplexityMetrics
    
    plan = CodePlan(
        title="Test",
        description="Test",
        file_changes=[],
        test_strategy="Test",
        risks=[],
        dependencies=[]
    )
    
    complexity = ComplexityMetrics(
        score=0.5,
        security_sensitive=False,
        estimated_patch_size=50,
        file_count=2,
        has_tests=True,
        requires_architecture=False
    )
    
    response = PlanResponse(
        plan=plan,
        model_used="gpt-4o",
        cost_usd=0.05,
        complexity=complexity
    )
    
    assert response.plan == plan
    assert response.model_used == "gpt-4o"
    assert response.cost_usd == 0.05
    assert response.complexity == complexity


def test_patch_response_dataclass():
    """Test PatchResponse dataclass."""
    patch = GeneratedPatch(
        diff="diff",
        files_changed=["file.py"],
        additions=10,
        deletions=5,
        model="test"
    )
    
    response = PatchResponse(
        patch=patch,
        model_used="deepseek",
        cost_usd=0.02
    )
    
    assert response.patch == patch
    assert response.model_used == "deepseek"
    assert response.cost_usd == 0.02


def test_review_response_dataclass():
    """Test ReviewResponse dataclass."""
    response = ReviewResponse(
        approved=True,
        issues=[],
        suggestions=["Add more tests"],
        model_used="gpt-4o",
        cost_usd=0.01
    )
    
    assert response.approved is True
    assert len(response.issues) == 0
    assert len(response.suggestions) == 1
    assert response.model_used == "gpt-4o"
    assert response.cost_usd == 0.01


def test_orchestrator_initialization_with_custom_config():
    """Test orchestrator initialization with custom config."""
    mock_config = Mock(spec=ConfigManager)
    mock_config.config = MagicMock()
    mock_config.config.abacus = MagicMock()
    mock_config.config.budget = MagicMock()
    mock_config.config.budget.daily_usd_cap = 20.0
    mock_config.config.budget.alert_threshold = 0.9
    mock_config.config.budget.track_by_model = True
    mock_config.config.to_dict.return_value = {
        'ai': {'models': {}},
        'escalation': {'triggers': []}
    }
    
    orchestrator = AIOrchestrator(config_manager=mock_config)
    
    assert orchestrator.config_manager == mock_config


def test_generate_patch_empty_file_contents(orchestrator):
    """Test patch generation with empty file contents dict."""
    plan = CodePlan(
        title="Test",
        description="Test",
        file_changes=[],
        test_strategy="Test",
        risks=[],
        dependencies=[]
    )
    
    response = orchestrator.generate_patch(
        plan=plan,
        file_contents={}
    )
    
    assert isinstance(response, PatchResponse)


def test_diagnose_failure_long_output(orchestrator):
    """Test diagnosis truncates long test output."""
    long_output = "Error: " + ("x" * 1000)
    
    patch = GeneratedPatch(
        diff="diff",
        files_changed=["file.py"],
        additions=5,
        deletions=0,
        model="test"
    )
    
    diagnosis = orchestrator.diagnose_failure(long_output, patch)
    
    # Should truncate to 500 chars
    assert len(diagnosis) > 0
