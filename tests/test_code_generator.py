
"""
Tests for Code Generator.
"""

import pytest
from unittest.mock import Mock

from sologit.orchestration.code_generator import (
    CodeGenerator, GeneratedPatch
)
from sologit.orchestration.planning_engine import CodePlan, FileChange
from sologit.api.client import AbacusClient


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


def test_generator_initialization(generator):
    """Test generator initializes correctly."""
    assert generator is not None
    assert generator.client is not None


def test_generate_patch_mock(generator, sample_plan):
    """Test patch generation with mock."""
    patch = generator.generate_patch(sample_plan)
    
    assert isinstance(patch, GeneratedPatch)
    assert patch.diff
    assert len(patch.files_changed) > 0


def test_generated_patch_str(generator, sample_plan):
    """Test GeneratedPatch string representation."""
    patch = generator.generate_patch(sample_plan)
    
    patch_str = str(patch)
    
    assert 'files changed' in patch_str.lower()
    assert str(patch.additions) in patch_str


def test_extract_diff_from_markdown(generator):
    """Test extracting diff from markdown code block."""
    content = '''```diff
--- a/test.py
+++ b/test.py
@@ -1,1 +1,2 @@
 old line
+new line
```'''
    
    diff = generator._extract_diff(content)
    
    assert '--- a/test.py' in diff
    assert '+new line' in diff


def test_extract_files_from_diff(generator):
    """Test extracting file list from diff."""
    diff = '''--- a/file1.py
+++ b/file1.py
@@ -1,1 +1,2 @@
 line
+new line

--- a/file2.py
+++ b/file2.py
@@ -1,1 +1,1 @@
-old
+new'''
    
    files = generator._extract_files_from_diff(diff)
    
    assert 'file1.py' in files
    assert 'file2.py' in files


def test_count_changes(generator):
    """Test counting additions and deletions."""
    diff = '''--- a/test.py
+++ b/test.py
@@ -1,3 +1,4 @@
 line1
-line2
+new line2
+new line3
 line4'''
    
    additions, deletions = generator._count_changes(diff)
    
    assert additions == 2
    assert deletions == 1


def test_generate_mock_patch_create(generator):
    """Test mock patch for file creation."""
    plan = CodePlan(
        title='Create Module',
        description='New module',
        file_changes=[
            FileChange(path='new.py', action='create', reason='New', estimated_lines=10)
        ],
        test_strategy='Test',
        risks=[],
        estimated_complexity='low'
    )
    
    diff = generator._generate_mock_patch(plan, None)
    
    assert '--- /dev/null' in diff
    assert '+++ b/new.py' in diff


def test_generate_mock_patch_modify(generator):
    """Test mock patch for file modification."""
    plan = CodePlan(
        title='Modify Module',
        description='Update module',
        file_changes=[
            FileChange(path='existing.py', action='modify', reason='Update', estimated_lines=5)
        ],
        test_strategy='Test',
        risks=[],
        estimated_complexity='low'
    )
    
    diff = generator._generate_mock_patch(plan, None)
    
    assert '--- a/existing.py' in diff
    assert '+++ b/existing.py' in diff


def test_generate_mock_patch_delete(generator):
    """Test mock patch for file deletion."""
    plan = CodePlan(
        title='Delete Module',
        description='Remove module',
        file_changes=[
            FileChange(path='old.py', action='delete', reason='Obsolete', estimated_lines=0)
        ],
        test_strategy='Test',
        risks=[],
        estimated_complexity='low'
    )
    
    diff = generator._generate_mock_patch(plan, None)
    
    assert '--- a/old.py' in diff
    assert '+++ /dev/null' in diff


def test_create_fallback_patch(generator, sample_plan):
    """Test creating fallback patch."""
    patch = generator._create_fallback_patch(sample_plan)
    
    assert isinstance(patch, GeneratedPatch)
    assert 'TODO' in patch.diff
    assert patch.confidence < 0.5


def test_generate_patch_with_file_contents(generator, sample_plan):
    """Test patch generation with existing file contents."""
    file_contents = {
        'auth/login.py': 'def old_function():\n    pass\n'
    }
    
    patch = generator.generate_patch(sample_plan, file_contents)
    
    assert isinstance(patch, GeneratedPatch)


def test_generate_patch_from_feedback(generator):
    """Test generating refined patch from feedback."""
    original_patch = GeneratedPatch(
        diff='--- a/test.py\n+++ b/test.py\n@@ -1,1 +1,1 @@\n-old\n+new',
        files_changed=['test.py'],
        additions=1,
        deletions=1,
        model='test',
        confidence=0.8
    )
    
    feedback = "Syntax error on line 5"
    
    refined_patch = generator.generate_patch_from_feedback(
        original_patch,
        feedback
    )
    
    # For Phase 2, returns original (refinement not implemented yet)
    assert refined_patch == original_patch

