
"""
Tests for Planning Engine.
"""

import pytest
from unittest.mock import Mock, patch

from sologit.orchestration.planning_engine import (
    PlanningEngine, CodePlan, FileChange
)
from sologit.api.client import AbacusClient, ChatResponse


@pytest.fixture
def mock_client():
    """Mock Abacus.ai client."""
    client = Mock(spec=AbacusClient)
    return client


@pytest.fixture
def engine(mock_client):
    """Create planning engine."""
    return PlanningEngine(mock_client)


def test_engine_initialization(engine):
    """Test engine initializes correctly."""
    assert engine is not None
    assert engine.client is not None


def test_generate_plan_mock(engine):
    """Test plan generation with mock response."""
    prompt = "add user authentication"
    
    plan = engine.generate_plan(prompt)
    
    assert isinstance(plan, CodePlan)
    assert plan.title
    assert plan.description
    assert len(plan.file_changes) > 0


def test_generate_plan_with_context(engine):
    """Test plan generation with repository context."""
    prompt = "add API endpoint"
    context = {
        'file_tree': ['api/routes.py', 'api/models.py'],
        'language': 'Python'
    }
    
    plan = engine.generate_plan(prompt, context)
    
    assert isinstance(plan, CodePlan)


def test_file_change_creation():
    """Test FileChange dataclass."""
    fc = FileChange(
        path='test.py',
        action='create',
        reason='Add new module',
        estimated_lines=50
    )
    
    assert fc.path == 'test.py'
    assert fc.action == 'create'


def test_code_plan_to_dict():
    """Test CodePlan serialization."""
    plan = CodePlan(
        title='Test Plan',
        description='Test description',
        file_changes=[
            FileChange(path='test.py', action='create', reason='Testing', estimated_lines=10)
        ],
        test_strategy='Add unit tests',
        risks=['None'],
        dependencies=[],
        estimated_complexity='low'
    )
    
    data = plan.to_dict()
    
    assert data['title'] == 'Test Plan'
    assert len(data['file_changes']) == 1
    assert data['estimated_complexity'] == 'low'


def test_code_plan_str_representation():
    """Test CodePlan string representation."""
    plan = CodePlan(
        title='Test Plan',
        description='Test description',
        file_changes=[
            FileChange(path='test.py', action='create', reason='Testing', estimated_lines=10)
        ],
        test_strategy='Add unit tests',
        risks=['Risk 1'],
        estimated_complexity='medium'
    )
    
    plan_str = str(plan)
    
    assert 'Test Plan' in plan_str
    assert 'test.py' in plan_str
    assert 'MEDIUM' in plan_str


def test_parse_plan_response(engine):
    """Test parsing AI response."""
    json_response = '''{
        "title": "Add Login",
        "description": "Implement login feature",
        "file_changes": [
            {"path": "auth.py", "action": "create", "reason": "Auth module", "estimated_lines": 50}
        ],
        "test_strategy": "Unit tests",
        "risks": [],
        "estimated_complexity": "medium"
    }'''
    
    plan_data = engine._parse_plan_response(json_response)
    
    assert plan_data['title'] == 'Add Login'
    assert len(plan_data['file_changes']) == 1


def test_parse_plan_response_with_markdown(engine):
    """Test parsing response wrapped in markdown."""
    response = '''```json
    {
        "title": "Test",
        "description": "Test",
        "file_changes": [],
        "test_strategy": "Test",
        "risks": []
    }
    ```'''
    
    plan_data = engine._parse_plan_response(response)
    
    assert plan_data['title'] == 'Test'


def test_generate_mock_plan_add_feature(engine):
    """Test mock plan generation for adding feature."""
    prompt = "add new API endpoint"
    
    plan_data = engine._generate_mock_plan(prompt, None)
    
    assert 'add' in prompt.lower()
    assert len(plan_data['file_changes']) > 0


def test_generate_mock_plan_fix_bug(engine):
    """Test mock plan generation for bug fix."""
    prompt = "fix authentication bug"
    
    plan_data = engine._generate_mock_plan(prompt, None)
    
    assert 'fix' in prompt.lower()
    assert len(plan_data['file_changes']) > 0


def test_fallback_plan_creation(engine):
    """Test creating fallback plan."""
    plan = engine._create_fallback_plan("test prompt")
    
    assert isinstance(plan, CodePlan)
    assert plan.title == "Basic Implementation"
    assert len(plan.file_changes) > 0


def test_format_file_tree(engine):
    """Test file tree formatting."""
    file_tree = ['file1.py', 'file2.py', 'dir/file3.py']
    
    formatted = engine._format_file_tree(file_tree)
    
    assert 'file1.py' in formatted
    assert 'file2.py' in formatted

