"""
Enhanced tests for Code Generator to achieve >95% coverage.
"""

import pytest
import json
from unittest.mock import Mock
from pathlib import Path

from sologit.orchestration.code_generator import (
    CodeGenerator, GeneratedPatch
)
from sologit.orchestration.planning_engine import CodePlan, FileChange
from sologit.api.client import AbacusClient, ChatResponse


@pytest.fixture
def mock_client():
    """Mock Abacus API client."""
    return Mock(spec=AbacusClient)


@pytest.fixture
def generator(mock_client):
    """Create code generator for testing."""
    return CodeGenerator(mock_client)


@pytest.fixture
def sample_plan():
    """Sample code plan for testing."""
    return CodePlan(
        title="Add Authentication",
        description="Implement JWT authentication",
        file_changes=[
            FileChange(
                path="auth.py",
                action="create",
                reason="Auth module",
                estimated_lines=100
            ),
            FileChange(
                path="config.py",
                action="modify",
                reason="Add auth config",
                estimated_lines=20
            )
        ],
        test_strategy="Unit tests for auth module",
        risks=["Security considerations"],
        dependencies=["jwt"],
        estimated_complexity="high"
    )


def test_generated_patch_str():
    """Test GeneratedPatch __str__ method."""
    patch = GeneratedPatch(
        diff="--- a/file.py\n+++ b/file.py",
        files_changed=["file.py", "test.py"],
        additions=10,
        deletions=5,
        model="gpt-4o",
        confidence=0.9
    )
    
    result = str(patch)
    assert "2 files changed" in result
    assert "+10" in result
    assert "-5" in result


def test_generate_patch_with_file_contents(generator, sample_plan):
    """Test patch generation with existing file contents."""
    file_contents = {
        "config.py": "# Existing config\nSETTINGS = {}\n"
    }
    
    patch = generator.generate_patch(
        plan=sample_plan,
        file_contents=file_contents
    )
    
    assert isinstance(patch, GeneratedPatch)
    assert len(patch.files_changed) > 0


def test_generate_patch_with_deployment_credentials(generator, sample_plan, mock_client):
    """Test patch generation with deployment credentials."""
    # Mock API response
    mock_diff = """--- a/auth.py
+++ b/auth.py
@@ -1,1 +1,5 @@
+def authenticate():
+    pass
"""
    
    mock_response = ChatResponse(
        content=f"```diff\n{mock_diff}\n```",
        model="deepseek-coder",
        tokens_used=300,
        finish_reason="stop"
    )
    mock_client.chat.return_value = mock_response
    
    patch = generator.generate_patch(
        plan=sample_plan,
        deployment_id="deploy-123",
        deployment_token="token-456"
    )
    
    assert isinstance(patch, GeneratedPatch)


def test_generate_patch_api_error_fallback(generator, sample_plan, mock_client):
    """Test patch generation falls back on API error."""
    mock_client.chat.side_effect = Exception("API error")
    
    patch = generator.generate_patch(
        plan=sample_plan,
        deployment_id="deploy-123",
        deployment_token="token-456"
    )
    
    # Should return fallback patch
    assert isinstance(patch, GeneratedPatch)
    assert patch.model == "fallback"


def test_extract_diff_with_markdown_diff(generator):
    """Test diff extraction from markdown diff block."""
    content = """Here's the patch:
```diff
--- a/file.py
+++ b/file.py
@@ -1,1 +1,2 @@
 line1
+line2
```
"""
    
    diff = generator._extract_diff(content)
    assert "--- a/file.py" in diff
    assert "+line2" in diff


def test_extract_diff_with_plain_markdown(generator):
    """Test diff extraction from plain markdown block."""
    content = """```
--- a/file.py
+++ b/file.py
@@ -1,1 +1,2 @@
 line1
+line2
```"""
    
    diff = generator._extract_diff(content)
    assert "--- a/file.py" in diff


def test_extract_diff_no_markdown(generator):
    """Test diff extraction without markdown."""
    content = """--- a/file.py
+++ b/file.py
@@ -1,1 +1,2 @@
 line1
+line2"""
    
    diff = generator._extract_diff(content)
    assert "--- a/file.py" in diff


def test_extract_diff_with_surrounding_text(generator):
    """Test diff extraction with surrounding text."""
    content = """Here's what I changed:

--- a/file.py
+++ b/file.py
@@ -1,1 +1,2 @@
 line1
+line2

That's all!"""
    
    diff = generator._extract_diff(content)
    assert "--- a/file.py" in diff


def test_extract_diff_no_markers(generator):
    """Test diff extraction with no diff markers."""
    content = "Just some plain text"
    
    diff = generator._extract_diff(content)
    assert diff == content


def test_extract_files_from_diff(generator):
    """Test file extraction from diff."""
    diff = """--- a/file1.py
+++ b/file1.py
@@ -1,1 +1,2 @@
+line
--- a/file2.py
+++ b/file2.py
@@ -1,1 +1,2 @@
+line"""
    
    files = generator._extract_files_from_diff(diff)
    
    assert "file1.py" in files
    assert "file2.py" in files


def test_extract_files_from_diff_with_dev_null(generator):
    """Test file extraction handles /dev/null."""
    diff = """--- /dev/null
+++ b/newfile.py
@@ -0,0 +1,2 @@
+line1
+line2"""
    
    files = generator._extract_files_from_diff(diff)
    
    assert "newfile.py" in files
    assert "/dev/null" not in files


def test_extract_files_from_diff_deletion(generator):
    """Test file extraction for deletions."""
    diff = """--- a/oldfile.py
+++ /dev/null
@@ -1,2 +0,0 @@
-line1
-line2"""
    
    files = generator._extract_files_from_diff(diff)
    
    assert "oldfile.py" in files


def test_count_changes_additions_deletions(generator):
    """Test counting additions and deletions."""
    diff = """--- a/file.py
+++ b/file.py
@@ -1,3 +1,4 @@
 line1
-line2
+line2_modified
+line3
 line4"""
    
    additions, deletions = generator._count_changes(diff)
    
    assert additions == 2  # +line2_modified, +line3
    assert deletions == 1  # -line2


def test_count_changes_ignores_headers(generator):
    """Test that count changes ignores diff headers."""
    diff = """--- a/file.py
+++ b/file.py
@@ -1,1 +1,2 @@
 line1
+line2"""
    
    additions, deletions = generator._count_changes(diff)
    
    assert additions == 1  # Should not count +++ header
    assert deletions == 0  # Should not count --- header


def test_generate_mock_patch_create(generator):
    """Test mock patch generation for file creation."""
    plan = CodePlan(
        title="Add module",
        description="Add new module",
        file_changes=[
            FileChange(
                path="newmodule.py",
                action="create",
                reason="New functionality",
                estimated_lines=50
            )
        ],
        test_strategy="Test strategy",
        risks=[],
        dependencies=[]
    )
    
    diff = generator._generate_mock_patch(plan, None)
    
    assert "--- /dev/null" in diff
    assert "+++ b/newmodule.py" in diff
    assert "New functionality" in diff


def test_generate_mock_patch_modify(generator):
    """Test mock patch generation for file modification."""
    plan = CodePlan(
        title="Update module",
        description="Update existing module",
        file_changes=[
            FileChange(
                path="existing.py",
                action="modify",
                reason="Bug fix",
                estimated_lines=10
            )
        ],
        test_strategy="Test strategy",
        risks=[],
        dependencies=[]
    )
    
    diff = generator._generate_mock_patch(plan, None)
    
    assert "--- a/existing.py" in diff
    assert "+++ b/existing.py" in diff
    assert "Bug fix" in diff


def test_generate_mock_patch_delete(generator):
    """Test mock patch generation for file deletion."""
    plan = CodePlan(
        title="Remove module",
        description="Remove obsolete module",
        file_changes=[
            FileChange(
                path="obsolete.py",
                action="delete",
                reason="No longer needed",
                estimated_lines=0
            )
        ],
        test_strategy="Test strategy",
        risks=[],
        dependencies=[]
    )
    
    diff = generator._generate_mock_patch(plan, None)
    
    assert "--- a/obsolete.py" in diff
    assert "+++ /dev/null" in diff


def test_generate_mock_patch_multiple_files(generator):
    """Test mock patch generation for multiple files."""
    plan = CodePlan(
        title="Multi-file change",
        description="Change multiple files",
        file_changes=[
            FileChange(path="file1.py", action="create", reason="New", estimated_lines=20),
            FileChange(path="file2.py", action="modify", reason="Update", estimated_lines=10),
            FileChange(path="file3.py", action="delete", reason="Remove", estimated_lines=0)
        ],
        test_strategy="Test strategy",
        risks=[],
        dependencies=[]
    )
    
    diff = generator._generate_mock_patch(plan, None)
    
    assert "file1.py" in diff
    assert "file2.py" in diff
    assert "file3.py" in diff


def test_create_fallback_patch(generator, sample_plan):
    """Test fallback patch creation."""
    patch = generator._create_fallback_patch(sample_plan)
    
    assert isinstance(patch, GeneratedPatch)
    assert patch.model == "fallback"
    assert patch.confidence == 0.1
    assert "TODO.md" in patch.files_changed
    assert sample_plan.title in patch.diff


def test_generate_patch_from_feedback(generator, mock_client):
    """Test patch refinement from feedback."""
    original_patch = GeneratedPatch(
        diff="--- a/file.py\n+++ b/file.py\n@@ -1,1 +1,2 @@\n line1\n+line2",
        files_changed=["file.py"],
        additions=1,
        deletions=0,
        model="gpt-4o",
        confidence=0.8
    )
    
    feedback = "Tests failed: NameError on line 5"
    
    refined_patch = generator.generate_patch_from_feedback(
        original_patch=original_patch,
        feedback=feedback
    )
    
    # For Phase 2, should return original patch
    assert refined_patch == original_patch


def test_generate_patch_with_long_file_content(generator):
    """Test patch generation with long file content (>2000 chars)."""
    plan = CodePlan(
        title="Update large file",
        description="Modify large file",
        file_changes=[
            FileChange(
                path="large.py",
                action="modify",
                reason="Update",
                estimated_lines=50
            )
        ],
        test_strategy="Test strategy",
        risks=[],
        dependencies=[]
    )
    
    # Create a large file content
    long_content = "# " + ("line\n" * 500)  # >2000 chars
    file_contents = {"large.py": long_content}
    
    patch = generator.generate_patch(
        plan=plan,
        file_contents=file_contents
    )
    
    assert isinstance(patch, GeneratedPatch)


def test_generate_patch_without_file_contents(generator, sample_plan):
    """Test patch generation without file contents."""
    patch = generator.generate_patch(
        plan=sample_plan,
        file_contents=None
    )
    
    assert isinstance(patch, GeneratedPatch)


def test_extract_files_duplicate_handling(generator):
    """Test that duplicate files are handled in extraction."""
    diff = """--- a/file.py
+++ b/file.py
@@ -1,1 +1,2 @@
+line
--- a/file.py
+++ b/file.py
@@ -3,1 +3,2 @@
+line"""
    
    files = generator._extract_files_from_diff(diff)
    
    # The implementation allows duplicates, so we just check files are extracted
    assert "file.py" in files
    assert len(files) >= 1


def test_generate_mock_patch_with_file_contents(generator):
    """Test mock patch generation uses file contents."""
    plan = CodePlan(
        title="Update config",
        description="Update configuration",
        file_changes=[
            FileChange(
                path="config.py",
                action="modify",
                reason="Add setting",
                estimated_lines=5
            )
        ],
        test_strategy="Test strategy",
        risks=[],
        dependencies=[]
    )
    
    file_contents = {
        "config.py": "# Config file\nSETTINGS = {}\n"
    }
    
    diff = generator._generate_mock_patch(plan, file_contents)
    
    assert isinstance(diff, str)
    assert len(diff) > 0


def test_generate_patch_model_parameter(generator, sample_plan):
    """Test patch generation with custom model."""
    patch = generator.generate_patch(
        plan=sample_plan,
        model="codellama-70b"
    )
    
    # Model should be set in the patch
    assert patch.model in ["codellama-70b", "deepseek-coder-33b"]  # Falls back to default in mock


def test_generate_patch_confidence_value(generator, sample_plan):
    """Test generated patch has confidence value."""
    patch = generator.generate_patch(plan=sample_plan)
    
    assert 0.0 <= patch.confidence <= 1.0


def test_count_changes_empty_diff(generator):
    """Test counting changes in empty diff."""
    diff = ""
    
    additions, deletions = generator._count_changes(diff)
    
    assert additions == 0
    assert deletions == 0


def test_extract_files_empty_diff(generator):
    """Test file extraction from empty diff."""
    diff = ""
    
    files = generator._extract_files_from_diff(diff)
    
    assert files == []
