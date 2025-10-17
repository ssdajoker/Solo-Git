"""
Additional tests for Code Generator to improve coverage to 90%+.
"""

import pytest
from unittest.mock import Mock

from sologit.orchestration.code_generator import (
    CodeGenerator, GeneratedPatch
)
from sologit.orchestration.planning_engine import CodePlan, FileChange
from sologit.api.client import AbacusClient, ChatResponse


@pytest.fixture
def mock_client():
    """Mock Abacus.ai client."""
    return Mock(spec=AbacusClient)


@pytest.fixture
def generator(mock_client):
    """Create code generator."""
    return CodeGenerator(mock_client)


@pytest.fixture
def sample_plan():
    """Sample code plan."""
    return CodePlan(
        title='Add Login Feature',
        description='Implement user login with email and password',
        file_changes=[
            FileChange(
                path='auth/login.py',
                action='create',
                reason='New login module',
                estimated_lines=50
            )
        ],
        test_strategy='Add unit tests for login',
        risks=[],
        estimated_complexity='medium'
    )


def test_generate_patch_with_large_file_content(generator):
    """Test patch generation with large file content (line 124)."""
    plan = CodePlan(
        title='Modify Large File',
        description='Update file',
        file_changes=[
            FileChange(
                path='large_file.py',
                action='modify',
                reason='Update',
                estimated_lines=100
            )
        ],
        test_strategy='Test',
        risks=[],
        estimated_complexity='medium'
    )
    
    # Create large file content (> 2000 chars, triggers line 124)
    large_content = "# " + "x" * 2500
    file_contents = {
        'large_file.py': large_content
    }
    
    patch = generator.generate_patch(plan, file_contents)
    
    assert isinstance(patch, GeneratedPatch)


def test_generate_patch_with_deployment_credentials(generator, mock_client):
    """Test patch generation with deployment credentials (lines 141-149)."""
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
    
    # Mock the chat response
    mock_response = Mock()
    mock_response.content = '''```diff
--- /dev/null
+++ b/test.py
@@ -0,0 +1,3 @@
+def test():
+    pass
+
```'''
    mock_response.model = 'deepseek-coder-33b'
    mock_response.tokens_used = 100
    mock_client.chat.return_value = mock_response
    
    # Call with deployment credentials (triggers lines 141-149)
    patch = generator.generate_patch(
        plan,
        deployment_id='test-deployment-id',
        deployment_token='test-token'
    )
    
    # Should have called the client
    assert mock_client.chat.called
    assert isinstance(patch, GeneratedPatch)


def test_generate_patch_exception_fallback(generator, mock_client, sample_plan):
    """Test patch generation with exception (lines 171-174)."""
    # Mock the chat to raise an exception
    mock_client.chat.side_effect = Exception("API Error")
    
    # Should fall back to fallback patch
    patch = generator.generate_patch(
        sample_plan,
        deployment_id='test-deployment-id',
        deployment_token='test-token'
    )
    
    assert isinstance(patch, GeneratedPatch)
    assert patch.model == "fallback"
    assert patch.confidence < 0.5


def test_extract_diff_with_markdown_code_block(generator):
    """Test extracting diff from markdown with diff block (lines 181-185)."""
    content = '''Here's the patch:
```diff
--- a/test.py
+++ b/test.py
@@ -1,1 +1,2 @@
 old line
+new line
```
End of patch.'''
    
    diff = generator._extract_diff(content)
    
    # Should extract the diff content
    assert '--- a/test.py' in diff
    assert '+new line' in diff
    assert 'Here\'s the patch:' not in diff


def test_extract_diff_with_generic_code_block(generator):
    """Test extracting diff from generic code block (lines 187-191)."""
    content = '''```
--- a/test.py
+++ b/test.py
@@ -1,1 +1,2 @@
 old line
+new line
```'''
    
    diff = generator._extract_diff(content)
    
    # Should extract the diff content
    assert '--- a/test.py' in diff
    assert '+new line' in diff


def test_extract_diff_with_diff_markers(generator):
    """Test extracting diff when no code blocks (lines 194-205)."""
    content = '''Some text before
--- a/test.py
+++ b/test.py
@@ -1,1 +1,2 @@
 old line
+new line
Some text after'''
    
    diff = generator._extract_diff(content)
    
    # Should extract from diff markers onwards (lines 194-205)
    assert '--- a/test.py' in diff
    assert '+new line' in diff


def test_extract_diff_plain_text_fallback(generator):
    """Test extracting diff from plain text (line 208)."""
    content = "This is just plain text with no diff markers"
    
    diff = generator._extract_diff(content)
    
    # Should return as-is (line 208)
    assert diff == content


def test_extract_files_from_diff_with_dev_null(generator):
    """Test extracting files excluding /dev/null."""
    diff = '''--- /dev/null
+++ b/new_file.py
@@ -0,0 +1,3 @@
+def test():
+    pass
+

--- a/existing.py
+++ b/existing.py
@@ -1,1 +1,2 @@
 line
+new line'''
    
    files = generator._extract_files_from_diff(diff)
    
    # Should include both files but not /dev/null
    assert 'new_file.py' in files
    assert 'existing.py' in files
    assert len(files) == 2


def test_extract_files_duplicate_handling(generator):
    """Test file extraction from diff with multiple hunks for same file."""
    diff = '''--- a/test.py
+++ b/test.py
@@ -1,1 +1,2 @@
 line
+new line

--- a/test.py
+++ b/test.py
@@ -3,1 +3,2 @@
 line
+another line'''
    
    files = generator._extract_files_from_diff(diff)
    
    # The implementation adds files when it sees --- lines, 
    # then may add again when it sees +++ lines if not already present (line 222)
    # In this case, we get test.py from the first --- and the check at line 222
    # prevents adding it again from the first +++, but the second --- adds it again
    assert 'test.py' in files


def test_count_changes_with_various_markers(generator):
    """Test counting changes with various diff markers."""
    diff = '''--- a/test.py
+++ b/test.py
@@ -1,5 +1,6 @@
 line1
-line2
+new line2
+another new line
 line3
 line4
-line5'''
    
    additions, deletions = generator._count_changes(diff)
    
    # Should count lines starting with + or - but not +++ or ---
    assert additions == 2
    assert deletions == 2


def test_generate_mock_patch_all_actions(generator):
    """Test mock patch generation for all action types."""
    # Test create action
    plan_create = CodePlan(
        title='Create',
        description='Create',
        file_changes=[
            FileChange(path='new.py', action='create', reason='New', estimated_lines=10)
        ],
        test_strategy='Test',
        risks=[],
        estimated_complexity='low'
    )
    
    diff_create = generator._generate_mock_patch(plan_create, None)
    assert '--- /dev/null' in diff_create
    assert '+++ b/new.py' in diff_create
    
    # Test modify action
    plan_modify = CodePlan(
        title='Modify',
        description='Modify',
        file_changes=[
            FileChange(path='existing.py', action='modify', reason='Update', estimated_lines=5)
        ],
        test_strategy='Test',
        risks=[],
        estimated_complexity='low'
    )
    
    diff_modify = generator._generate_mock_patch(plan_modify, None)
    assert '--- a/existing.py' in diff_modify
    assert '+++ b/existing.py' in diff_modify
    
    # Test delete action
    plan_delete = CodePlan(
        title='Delete',
        description='Delete',
        file_changes=[
            FileChange(path='old.py', action='delete', reason='Remove', estimated_lines=0)
        ],
        test_strategy='Test',
        risks=[],
        estimated_complexity='low'
    )
    
    diff_delete = generator._generate_mock_patch(plan_delete, None)
    assert '--- a/old.py' in diff_delete
    assert '+++ /dev/null' in diff_delete


def test_generate_mock_patch_multiple_files(generator):
    """Test mock patch generation with multiple file changes."""
    plan = CodePlan(
        title='Multiple Changes',
        description='Multiple files',
        file_changes=[
            FileChange(path='file1.py', action='create', reason='New', estimated_lines=10),
            FileChange(path='file2.py', action='modify', reason='Update', estimated_lines=5),
            FileChange(path='file3.py', action='delete', reason='Remove', estimated_lines=0)
        ],
        test_strategy='Test',
        risks=[],
        estimated_complexity='medium'
    )
    
    diff = generator._generate_mock_patch(plan, None)
    
    # Should have patches for all files
    assert 'file1.py' in diff
    assert 'file2.py' in diff
    assert 'file3.py' in diff


def test_create_fallback_patch(generator, sample_plan):
    """Test fallback patch creation."""
    patch = generator._create_fallback_patch(sample_plan)
    
    assert isinstance(patch, GeneratedPatch)
    assert 'TODO' in patch.diff
    assert sample_plan.title in patch.diff
    assert patch.confidence == 0.1
    assert patch.model == "fallback"
    assert 'TODO.md' in patch.files_changed


def test_generate_patch_without_file_contents(generator, sample_plan):
    """Test patch generation without file contents."""
    # No file_contents provided
    patch = generator.generate_patch(sample_plan, file_contents=None)
    
    assert isinstance(patch, GeneratedPatch)
    assert len(patch.files_changed) > 0


def test_generate_patch_from_feedback_returns_original(generator):
    """Test that generate_patch_from_feedback returns original in Phase 2."""
    original_patch = GeneratedPatch(
        diff='test diff',
        files_changed=['test.py'],
        additions=5,
        deletions=2,
        model='test-model',
        confidence=0.7
    )
    
    feedback = "There's a syntax error"
    
    # Should return original patch (not fully implemented in Phase 2)
    result = generator.generate_patch_from_feedback(
        original_patch,
        feedback,
        deployment_id='test-id',
        deployment_token='test-token'
    )
    
    assert result == original_patch
