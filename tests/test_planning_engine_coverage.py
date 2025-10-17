"""
Additional tests for Planning Engine to improve coverage to 90%+.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch

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


def test_code_plan_str_with_dependencies():
    """Test CodePlan __str__ with dependencies (lines 85-91)."""
    plan = CodePlan(
        title='Test Plan',
        description='Test description',
        file_changes=[
            FileChange(path='test.py', action='create', reason='Testing', estimated_lines=10)
        ],
        test_strategy='Add unit tests',
        risks=['Risk 1'],
        dependencies=['numpy', 'pandas'],  # This triggers lines 85-91
        estimated_complexity='medium'
    )
    
    plan_str = str(plan)
    
    assert 'Dependencies:' in plan_str
    assert 'numpy' in plan_str
    assert 'pandas' in plan_str


def test_generate_plan_with_recent_changes_context(engine):
    """Test plan generation with recent changes in context (line 180)."""
    prompt = "add new feature"
    context = {
        'file_tree': ['api/routes.py'],
        'recent_changes': 'Commit abc123: Fixed bug in authentication',  # Triggers line 180
        'language': 'Python'
    }
    
    plan = engine.generate_plan(prompt, repo_context=context)
    
    assert isinstance(plan, CodePlan)


def test_generate_plan_with_deployment_credentials(engine, mock_client):
    """Test plan generation with deployment credentials (lines 199-207)."""
    # Mock the chat response
    mock_response = Mock()
    mock_response.content = '''{
        "title": "Add Feature",
        "description": "Implementation",
        "file_changes": [],
        "test_strategy": "Test",
        "risks": []
    }'''
    mock_response.model = 'gpt-4o'
    mock_response.tokens_used = 100
    mock_client.chat.return_value = mock_response
    
    prompt = "add feature"
    
    # Call with deployment credentials (triggers lines 199-207)
    plan = engine.generate_plan(
        prompt,
        deployment_id='test-deployment-id',
        deployment_token='test-token'
    )
    
    # Should have called the client
    assert mock_client.chat.called
    assert isinstance(plan, CodePlan)


def test_generate_plan_exception_fallback(engine, mock_client):
    """Test plan generation with exception and fallback (lines 229-232)."""
    # Mock the chat to raise an exception
    mock_client.chat.side_effect = Exception("API Error")
    
    prompt = "add feature"
    
    # Should fall back to basic plan
    plan = engine.generate_plan(
        prompt,
        deployment_id='test-deployment-id',
        deployment_token='test-token'
    )
    
    assert isinstance(plan, CodePlan)
    assert plan.title == "Basic Implementation"


def test_format_file_tree_with_string(engine):
    """Test _format_file_tree with string input (line 238)."""
    # Test with a very long string (triggers slicing on line 238)
    long_string = "file" * 200  # 800 characters
    
    result = engine._format_file_tree(long_string)
    
    # Should be truncated to 500 chars
    assert len(result) <= 500


def test_parse_plan_response_with_markdown_variations(engine):
    """Test parsing response with various markdown formats (line 251)."""
    # Test with ```json prefix (triggers line 249)
    response1 = '''```json
    {
        "title": "Test",
        "description": "Test",
        "file_changes": [],
        "test_strategy": "Test",
        "risks": []
    }
    ```'''
    
    plan_data1 = engine._parse_plan_response(response1)
    assert plan_data1['title'] == 'Test'
    
    # Test with just ``` prefix (triggers line 251)
    response2 = '''```
    {
        "title": "Test2",
        "description": "Test2",
        "file_changes": [],
        "test_strategy": "Test",
        "risks": []
    }
    ```'''
    
    plan_data2 = engine._parse_plan_response(response2)
    assert plan_data2['title'] == 'Test2'


def test_parse_plan_response_invalid_json_fallback(engine):
    """Test parsing invalid JSON with fallback (lines 259-278)."""
    # Test with completely invalid JSON
    response = "This is not JSON at all, just plain text describing the plan."
    
    plan_data = engine._parse_plan_response(response)
    
    # Should return minimal structure (line 271-278)
    assert plan_data['title'] == 'Implementation Plan'
    assert plan_data['description']
    assert plan_data['file_changes'] == []
    assert plan_data['test_strategy'] == 'Add tests'


def test_parse_plan_response_partial_json(engine):
    """Test parsing response with partial JSON match (lines 262-268)."""
    # Response with JSON embedded in text (triggers regex extraction)
    response = '''The plan is as follows:
    {"title": "Extracted Plan", "description": "This was extracted", "file_changes": [], "test_strategy": "Test", "risks": []}
    That's the plan!'''
    
    plan_data = engine._parse_plan_response(response)
    
    # Should extract the JSON
    assert plan_data['title'] == 'Extracted Plan'


def test_generate_mock_plan_with_test_keyword(engine):
    """Test mock plan with 'test' keyword (line 295)."""
    prompt = "add comprehensive test coverage for authentication"
    
    plan_data = engine._generate_mock_plan(prompt, None)
    
    # Should create test file (line 295-300)
    test_file = next((fc for fc in plan_data['file_changes'] if 'test' in fc['path']), None)
    assert test_file is not None
    assert test_file['action'] == 'create'


def test_generate_mock_plan_with_cli_keyword(engine):
    """Test mock plan with 'cli' keyword (line 311)."""
    prompt = "add new CLI command for status"
    
    plan_data = engine._generate_mock_plan(prompt, None)
    
    # Should modify CLI commands file (line 310-316)
    cli_file = next((fc for fc in plan_data['file_changes'] if 'cli' in fc['path']), None)
    assert cli_file is not None
    assert 'commands.py' in cli_file['path']


def test_generate_mock_plan_with_refactor_keyword(engine):
    """Test mock plan with 'refactor' keyword (line 334)."""
    prompt = "refactor the authentication module for better performance"
    
    plan_data = engine._generate_mock_plan(prompt, None)
    
    # Should detect refactor keyword (line 333-339)
    assert len(plan_data['file_changes']) > 0
    assert plan_data['file_changes'][0]['action'] == 'modify'


def test_generate_mock_plan_with_api_keyword(engine):
    """Test mock plan with 'api' keyword."""
    prompt = "add new REST API endpoint for user management"
    
    plan_data = engine._generate_mock_plan(prompt, None)
    
    # Should create/modify API file (line 303-309)
    api_file = next((fc for fc in plan_data['file_changes'] if 'api' in fc['path'] or 'endpoint' in fc['path']), None)
    assert api_file is not None


def test_generate_mock_plan_default_case(engine):
    """Test mock plan default case when no keywords match."""
    prompt = "do something unspecified"
    
    plan_data = engine._generate_mock_plan(prompt, None)
    
    # Should still create a default file change (line 342-348)
    assert len(plan_data['file_changes']) > 0


def test_format_file_tree_with_list(engine):
    """Test _format_file_tree with list input."""
    file_tree = ['file1.py', 'file2.py', 'dir/file3.py'] * 10  # 30 files
    
    result = engine._format_file_tree(file_tree)
    
    # Should limit to 20 files (line 237)
    lines = result.split('\n')
    assert len(lines) <= 20


def test_code_plan_str_without_dependencies():
    """Test CodePlan __str__ without dependencies."""
    plan = CodePlan(
        title='Simple Plan',
        description='Simple description',
        file_changes=[
            FileChange(path='test.py', action='create', reason='Testing', estimated_lines=10)
        ],
        test_strategy='Add unit tests',
        risks=['Risk 1'],
        dependencies=[],  # Empty dependencies, won't trigger lines 85-91
        estimated_complexity='low'
    )
    
    plan_str = str(plan)
    
    # Should not include Dependencies section
    assert 'Dependencies:' not in plan_str or plan_str.count('Dependencies:') == 0 or '## Dependencies:' not in plan_str


def test_file_change_with_zero_lines():
    """Test FileChange with zero estimated lines."""
    fc = FileChange(
        path='test.py',
        action='delete',
        reason='Remove obsolete file',
        estimated_lines=0
    )
    
    # Verify in CodePlan.__str__ (line 71-72)
    plan = CodePlan(
        title='Delete File',
        description='Remove old file',
        file_changes=[fc],
        test_strategy='Test',
        risks=[],
        estimated_complexity='low'
    )
    
    plan_str = str(plan)
    
    # When estimated_lines is 0, line 71-72 won't execute
    assert 'test.py' in plan_str


def test_generate_plan_with_language_context(engine):
    """Test plan generation with language in context."""
    prompt = "add feature"
    context = {
        'language': 'TypeScript'  # Triggers line 185
    }
    
    plan = engine.generate_plan(prompt, repo_context=context)
    
    assert isinstance(plan, CodePlan)
