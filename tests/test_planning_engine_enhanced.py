"""
Enhanced tests for Planning Engine to achieve >95% coverage.
"""

import pytest
import json
from unittest.mock import Mock, patch

from sologit.orchestration.planning_engine import (
    PlanningEngine, CodePlan, FileChange
)
from sologit.api.client import AbacusClient, ChatResponse


@pytest.fixture
def mock_client():
    """Mock Abacus API client."""
    return Mock(spec=AbacusClient)


@pytest.fixture
def engine(mock_client):
    """Create planning engine for testing."""
    return PlanningEngine(mock_client)


def test_code_plan_with_dependencies():
    """Test CodePlan with dependencies."""
    plan = CodePlan(
        title="Test Plan",
        description="Description",
        file_changes=[],
        test_strategy="Test strategy",
        risks=["Risk 1"],
        dependencies=["dep1", "dep2"],
        estimated_complexity="high"
    )
    
    str_repr = str(plan)
    assert "## Dependencies:" in str_repr
    assert "dep1" in str_repr
    assert "dep2" in str_repr


def test_code_plan_without_dependencies():
    """Test CodePlan without dependencies."""
    plan = CodePlan(
        title="Test Plan",
        description="Description",
        file_changes=[],
        test_strategy="Test strategy",
        risks=["Risk 1"],
        dependencies=[],
        estimated_complexity="low"
    )
    
    str_repr = str(plan)
    assert "## Dependencies:" not in str_repr


def test_code_plan_with_estimated_lines():
    """Test CodePlan with file changes having estimated lines."""
    plan = CodePlan(
        title="Test Plan",
        description="Description",
        file_changes=[
            FileChange(
                path="test.py",
                action="create",
                reason="Test file",
                estimated_lines=100
            )
        ],
        test_strategy="Test strategy",
        risks=[],
        dependencies=[],
        estimated_complexity="medium"
    )
    
    str_repr = str(plan)
    assert "Est. lines: 100" in str_repr


def test_generate_plan_with_file_tree_context(engine):
    """Test plan generation with file tree context."""
    repo_context = {
        'file_tree': ['file1.py', 'file2.py', 'dir/file3.py'],
        'language': 'Python'
    }
    
    plan = engine.generate_plan(
        prompt="add authentication",
        repo_context=repo_context
    )
    
    assert plan is not None
    assert isinstance(plan, CodePlan)


def test_generate_plan_with_recent_changes_context(engine):
    """Test plan generation with recent changes context."""
    repo_context = {
        'recent_changes': "Modified auth.py\nAdded user model"
    }
    
    plan = engine.generate_plan(
        prompt="improve authentication",
        repo_context=repo_context
    )
    
    assert plan is not None
    assert isinstance(plan, CodePlan)


def test_generate_plan_with_language_context(engine):
    """Test plan generation with language context."""
    repo_context = {
        'language': 'Python'
    }
    
    plan = engine.generate_plan(
        prompt="add feature",
        repo_context=repo_context
    )
    
    assert plan is not None


def test_generate_plan_with_deployment_credentials(engine, mock_client):
    """Test plan generation with deployment credentials."""
    # Mock the API response
    mock_response = ChatResponse(
        content=json.dumps({
            'title': 'Add Authentication',
            'description': 'Implement JWT auth',
            'file_changes': [
                {
                    'path': 'auth.py',
                    'action': 'create',
                    'reason': 'Auth module',
                    'estimated_lines': 100
                }
            ],
            'test_strategy': 'Unit tests',
            'risks': ['Security risk'],
            'dependencies': ['jwt'],
            'estimated_complexity': 'high'
        }),
        model="gpt-4o",
        tokens_used=300,
        finish_reason="stop"
    )
    mock_client.chat.return_value = mock_response
    
    plan = engine.generate_plan(
        prompt="add authentication",
        deployment_id="deploy-123",
        deployment_token="token-456"
    )
    
    assert plan.title == "Add Authentication"
    assert len(plan.file_changes) == 1
    assert plan.dependencies == ['jwt']


def test_generate_plan_api_error_fallback(engine, mock_client):
    """Test plan generation falls back on API error."""
    mock_client.chat.side_effect = Exception("API error")
    
    plan = engine.generate_plan(
        prompt="add feature",
        deployment_id="deploy-123",
        deployment_token="token-456"
    )
    
    # Should return fallback plan
    assert plan is not None
    assert isinstance(plan, CodePlan)
    assert "Basic Implementation" in plan.title


def test_format_file_tree_with_list(engine):
    """Test file tree formatting with list input."""
    file_tree = ['file1.py', 'file2.py', 'file3.py']
    
    result = engine._format_file_tree(file_tree)
    
    assert 'file1.py' in result
    assert 'file2.py' in result


def test_format_file_tree_with_large_list(engine):
    """Test file tree formatting limits to 20 files."""
    file_tree = [f'file{i}.py' for i in range(50)]
    
    result = engine._format_file_tree(file_tree)
    
    # Should only include first 20
    lines = result.split('\n')
    assert len(lines) <= 20


def test_format_file_tree_with_string(engine):
    """Test file tree formatting with string input."""
    file_tree = "Complex tree structure" * 100  # Long string
    
    result = engine._format_file_tree(file_tree)
    
    # Should be truncated to 500 chars
    assert len(result) <= 500


def test_parse_plan_response_clean_json(engine):
    """Test parsing clean JSON response."""
    content = json.dumps({
        'title': 'Test Plan',
        'description': 'Test description',
        'file_changes': [],
        'test_strategy': 'Test strategy',
        'risks': [],
        'estimated_complexity': 'low'
    })
    
    result = engine._parse_plan_response(content)
    
    assert result['title'] == 'Test Plan'
    assert result['estimated_complexity'] == 'low'


def test_parse_plan_response_with_markdown_json(engine):
    """Test parsing JSON wrapped in markdown code block."""
    content = "```json\n" + json.dumps({
        'title': 'Test Plan',
        'description': 'Test description',
        'file_changes': [],
        'test_strategy': 'Test strategy',
        'risks': [],
        'estimated_complexity': 'medium'
    }) + "\n```"
    
    result = engine._parse_plan_response(content)
    
    assert result['title'] == 'Test Plan'


def test_parse_plan_response_with_markdown(engine):
    """Test parsing JSON wrapped in plain markdown block."""
    content = "```\n" + json.dumps({
        'title': 'Test Plan',
        'description': 'Test description',
        'file_changes': [],
        'test_strategy': 'Test strategy',
        'risks': [],
        'estimated_complexity': 'high'
    }) + "\n```"
    
    result = engine._parse_plan_response(content)
    
    assert result['title'] == 'Test Plan'


def test_parse_plan_response_invalid_json(engine):
    """Test parsing invalid JSON returns minimal structure."""
    content = "This is not JSON at all"
    
    result = engine._parse_plan_response(content)
    
    assert 'title' in result
    assert 'description' in result
    assert 'file_changes' in result
    assert isinstance(result['file_changes'], list)


def test_parse_plan_response_json_with_text(engine):
    """Test parsing JSON embedded in text."""
    content = "Here's the plan: " + json.dumps({
        'title': 'Extracted Plan',
        'description': 'Description',
        'file_changes': [],
        'test_strategy': 'Test',
        'risks': [],
        'estimated_complexity': 'low'
    }) + " - end of plan"
    
    result = engine._parse_plan_response(content)
    
    # Should extract the JSON part
    assert 'title' in result


def test_parse_plan_response_malformed_json_fallback(engine):
    """Test parsing malformed JSON falls back gracefully."""
    content = "{ invalid json structure ["
    
    result = engine._parse_plan_response(content)
    
    # Should return minimal structure
    assert result['title'] == 'Implementation Plan'
    assert result['file_changes'] == []


def test_generate_mock_plan_add_feature(engine):
    """Test mock plan generation for adding feature."""
    plan = engine._generate_mock_plan(
        prompt="add user authentication",
        repo_context=None
    )
    
    assert 'title' in plan
    assert len(plan['file_changes']) > 0
    assert plan['estimated_complexity'] == 'medium'


def test_generate_mock_plan_add_test(engine):
    """Test mock plan generation for adding tests."""
    plan = engine._generate_mock_plan(
        prompt="add tests for authentication",
        repo_context=None
    )
    
    # Should include test file
    file_changes = plan['file_changes']
    assert any('test' in fc['path'] for fc in file_changes)


def test_generate_mock_plan_add_api(engine):
    """Test mock plan generation for API endpoint."""
    plan = engine._generate_mock_plan(
        prompt="add API endpoint for users",
        repo_context=None
    )
    
    file_changes = plan['file_changes']
    assert any('api' in fc['path'] for fc in file_changes)


def test_generate_mock_plan_add_cli(engine):
    """Test mock plan generation for CLI command."""
    plan = engine._generate_mock_plan(
        prompt="add CLI command for status",
        repo_context=None
    )
    
    file_changes = plan['file_changes']
    assert any('cli' in fc['path'] for fc in file_changes)


def test_generate_mock_plan_fix_bug(engine):
    """Test mock plan generation for bug fix."""
    plan = engine._generate_mock_plan(
        prompt="fix memory leak bug",
        repo_context=None
    )
    
    file_changes = plan['file_changes']
    assert any(fc['action'] == 'modify' for fc in file_changes)


def test_generate_mock_plan_refactor(engine):
    """Test mock plan generation for refactoring."""
    plan = engine._generate_mock_plan(
        prompt="refactor authentication module",
        repo_context=None
    )
    
    file_changes = plan['file_changes']
    assert len(file_changes) > 0
    assert 'refactor' in file_changes[0]['reason'].lower()


def test_generate_mock_plan_improve(engine):
    """Test mock plan generation for improvement."""
    plan = engine._generate_mock_plan(
        prompt="improve performance of search",
        repo_context=None
    )
    
    file_changes = plan['file_changes']
    assert len(file_changes) > 0


def test_generate_mock_plan_generic(engine):
    """Test mock plan generation for generic request."""
    plan = engine._generate_mock_plan(
        prompt="update the system",
        repo_context=None
    )
    
    # Should have default file change
    file_changes = plan['file_changes']
    assert len(file_changes) > 0
    assert file_changes[0]['action'] == 'modify'


def test_create_fallback_plan(engine):
    """Test fallback plan creation."""
    plan = engine._create_fallback_plan("add feature X")
    
    assert isinstance(plan, CodePlan)
    assert plan.title == "Basic Implementation"
    assert len(plan.file_changes) == 1
    assert plan.estimated_complexity == "unknown"
    assert "Planning failed" in plan.risks[0]


def test_generate_plan_with_all_context_types(engine):
    """Test plan generation with all context types."""
    repo_context = {
        'file_tree': ['file1.py', 'file2.py'],
        'recent_changes': 'Modified auth.py',
        'language': 'Python'
    }
    
    plan = engine.generate_plan(
        prompt="add caching layer",
        repo_context=repo_context
    )
    
    assert plan is not None
    assert isinstance(plan, CodePlan)


def test_generate_plan_empty_context(engine):
    """Test plan generation with empty context."""
    plan = engine.generate_plan(
        prompt="add feature",
        repo_context={}
    )
    
    assert plan is not None


def test_code_plan_to_dict_complete(engine):
    """Test CodePlan to_dict with all fields."""
    plan = CodePlan(
        title="Complete Plan",
        description="Full description",
        file_changes=[
            FileChange(
                path="test.py",
                action="create",
                reason="Test file",
                estimated_lines=50
            )
        ],
        test_strategy="Complete testing",
        risks=["Risk 1", "Risk 2"],
        dependencies=["dep1", "dep2"],
        estimated_complexity="high"
    )
    
    data = plan.to_dict()
    
    assert data['title'] == "Complete Plan"
    assert data['description'] == "Full description"
    assert len(data['file_changes']) == 1
    assert data['file_changes'][0]['path'] == "test.py"
    assert data['test_strategy'] == "Complete testing"
    assert len(data['risks']) == 2
    assert len(data['dependencies']) == 2
    assert data['estimated_complexity'] == "high"


def test_generate_mock_plan_create_keyword(engine):
    """Test mock plan with 'create' keyword."""
    plan = engine._generate_mock_plan(
        prompt="create new module for caching",
        repo_context=None
    )
    
    assert len(plan['file_changes']) > 0


def test_generate_mock_plan_implement_keyword(engine):
    """Test mock plan with 'implement' keyword."""
    plan = engine._generate_mock_plan(
        prompt="implement rate limiting",
        repo_context=None
    )
    
    assert len(plan['file_changes']) > 0
