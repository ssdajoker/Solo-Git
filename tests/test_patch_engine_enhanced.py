
"""
Tests for Patch Engine enhancements.
"""

import tempfile
import zipfile
from pathlib import Path

import pytest

from sologit.engines.git_engine import GitEngine
from sologit.engines.patch_engine import PatchEngine, PatchConflictError


@pytest.fixture
def temp_dir():
    """Create temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def git_engine(temp_dir):
    """Create GitEngine instance."""
    return GitEngine(data_dir=temp_dir)


@pytest.fixture
def patch_engine(git_engine):
    """Create PatchEngine instance."""
    return PatchEngine(git_engine)


@pytest.fixture
def test_repo(git_engine, temp_dir):
    """Create test repository."""
    # Create test files
    test_project = temp_dir / "test_project"
    test_project.mkdir()
    (test_project / "hello.py").write_text(
        "def hello():\n    print('Hello')\n"
    )
    (test_project / "world.py").write_text(
        "def world():\n    print('World')\n"
    )
    (test_project / "README.md").write_text("# Test Project\n")
    
    # Create zip
    zip_path = temp_dir / "test.zip"
    with zipfile.ZipFile(zip_path, 'w') as zf:
        for file in test_project.glob('*'):
            zf.write(file, file.name)
    
    # Initialize repository
    repo_id = git_engine.init_from_zip(zip_path.read_bytes(), "test-repo")
    return repo_id


@pytest.fixture
def test_workpad(git_engine, test_repo):
    """Create test workpad."""
    return git_engine.create_workpad(test_repo, "Test Feature")


def test_get_patch_stats_simple(patch_engine):
    """Test patch statistics for simple patch."""
    patch = """diff --git a/hello.py b/hello.py
index 0000000..1111111 100644
--- a/hello.py
+++ b/hello.py
@@ -1,2 +1,3 @@
 def hello():
     print('Hello')
+    print('Added line')
"""
    
    stats = patch_engine.get_patch_stats(patch)
    
    assert stats['files_affected'] == 1
    assert 'hello.py' in stats['files_list']
    assert stats['additions'] == 1
    assert stats['deletions'] == 0
    assert stats['total_changes'] == 1
    assert stats['hunks'] == 1
    assert stats['complexity'] == 'trivial'


def test_get_patch_stats_complex(patch_engine):
    """Test patch statistics for complex patch."""
    # Multi-file patch with many changes
    patch = """diff --git a/file1.py b/file1.py
index 0000000..1111111 100644
--- a/file1.py
+++ b/file1.py
@@ -1,5 +1,10 @@
 line1
-line2
+line2 modified
 line3
+new line 4
+new line 5
+new line 6
diff --git a/file2.py b/file2.py
index 2222222..3333333 100644
--- a/file2.py
+++ b/file2.py
@@ -1,3 +1,5 @@
 content
+more content
+even more
"""
    
    stats = patch_engine.get_patch_stats(patch)
    
    assert stats['files_affected'] == 2
    assert stats['additions'] > 0
    assert stats['deletions'] > 0
    assert stats['hunks'] == 2


def test_patch_complexity_calculation(patch_engine):
    """Test patch complexity levels."""
    # Trivial
    stats = patch_engine.get_patch_stats(
        "diff --git a/a b/a\n--- a/a\n+++ b/a\n@@ -1 +1,2 @@\n line\n+added\n"
    )
    assert stats['complexity'] == 'trivial'
    
    # Very complex (simulate large patch)
    large_patch = "diff --git a/file.py b/file.py\n--- a/file.py\n+++ b/file.py\n"
    large_patch += "@@ -1,1 +1,600 @@\n"
    large_patch += "\n".join(["+line" for _ in range(600)])
    
    stats = patch_engine.get_patch_stats(large_patch)
    assert stats['complexity'] == 'very_complex'


def test_preview_patch_success(patch_engine, test_workpad):
    """Test patch preview for clean patch."""
    patch = """diff --git a/hello.py b/hello.py
index 0000000..1111111 100644
--- a/hello.py
+++ b/hello.py
@@ -1,2 +1,3 @@
 def hello():
     print('Hello')
+    print('Added')
"""
    
    preview = patch_engine.preview_patch(test_workpad, patch)
    
    assert preview['can_apply'] is True
    assert preview['has_conflicts'] is False
    assert len(preview['conflict_files']) == 0
    assert preview['stats']['files_affected'] == 1
    assert 'SAFE_TO_APPLY' in preview['recommendation']


def test_preview_patch_with_conflicts(patch_engine, git_engine, test_workpad):
    """Test patch preview with conflicts."""
    # Apply initial patch
    patch1 = """diff --git a/hello.py b/hello.py
index 0000000..1111111 100644
--- a/hello.py
+++ b/hello.py
@@ -1,2 +1,3 @@
 def hello():
     print('Hello')
+    print('First change')
"""
    git_engine.apply_patch(test_workpad, patch1)
    
    # Try to preview conflicting patch
    patch2 = """diff --git a/hello.py b/hello.py
index 0000000..2222222 100644
--- a/hello.py
+++ b/hello.py
@@ -1,2 +1,3 @@
 def hello():
     print('Hello')
+    print('Conflicting change')
"""
    
    preview = patch_engine.preview_patch(test_workpad, patch2)
    
    assert preview['can_apply'] is False
    assert preview['has_conflicts'] is True
    assert len(preview['conflict_files']) > 0
    assert 'MANUAL_RESOLUTION_REQUIRED' in preview['recommendation']


def test_detect_conflicts_detailed_no_conflicts(patch_engine, test_workpad):
    """Test detailed conflict detection with no conflicts."""
    patch = """diff --git a/hello.py b/hello.py
index 0000000..1111111 100644
--- a/hello.py
+++ b/hello.py
@@ -1,2 +1,3 @@
 def hello():
     print('Hello')
+    print('Safe change')
"""
    
    result = patch_engine.detect_conflicts_detailed(test_workpad, patch)
    
    assert result['has_conflicts'] is False
    assert len(result['conflicting_files']) == 0
    assert result['can_apply'] is True


def test_detect_conflicts_detailed_with_conflicts(patch_engine, git_engine, test_workpad):
    """Test detailed conflict detection with conflicts."""
    # Apply initial patch
    patch1 = """diff --git a/hello.py b/hello.py
index 0000000..1111111 100644
--- a/hello.py
+++ b/hello.py
@@ -1,2 +1,3 @@
 def hello():
     print('Hello')
+    print('First')
"""
    git_engine.apply_patch(test_workpad, patch1)
    
    # Try conflicting patch
    patch2 = """diff --git a/hello.py b/hello.py
index 0000000..2222222 100644
--- a/hello.py
+++ b/hello.py
@@ -1,2 +1,3 @@
 def hello():
     print('Hello')
+    print('Second')
"""
    
    result = patch_engine.detect_conflicts_detailed(test_workpad, patch2)
    
    assert result['has_conflicts'] is True
    assert len(result['conflicting_files']) > 0
    assert result['can_apply'] is False
    assert 'error_message' in result


def test_split_patch_by_file(patch_engine):
    """Test splitting multi-file patch."""
    multi_patch = """diff --git a/hello.py b/hello.py
index 0000000..1111111 100644
--- a/hello.py
+++ b/hello.py
@@ -1,2 +1,3 @@
 def hello():
     print('Hello')
+    print('Change 1')
diff --git a/world.py b/world.py
index 2222222..3333333 100644
--- a/world.py
+++ b/world.py
@@ -1,2 +1,3 @@
 def world():
     print('World')
+    print('Change 2')
"""
    
    split_patches = patch_engine.split_patch_by_file(multi_patch)
    
    assert len(split_patches) == 2
    assert 'hello.py' in split_patches
    assert 'world.py' in split_patches
    assert 'Change 1' in split_patches['hello.py']
    assert 'Change 2' in split_patches['world.py']


def test_combine_patches(patch_engine):
    """Test combining multiple patches."""
    patch1 = """diff --git a/hello.py b/hello.py
--- a/hello.py
+++ b/hello.py
@@ -1 +1,2 @@
 line
+added
"""
    
    patch2 = """diff --git a/world.py b/world.py
--- a/world.py
+++ b/world.py
@@ -1 +1,2 @@
 line
+added
"""
    
    combined = patch_engine.combine_patches([patch1, patch2])
    
    assert 'hello.py' in combined
    assert 'world.py' in combined
    assert len(combined) > 0


def test_combine_patches_empty(patch_engine):
    """Test combining empty patch list."""
    result = patch_engine.combine_patches([])
    assert result == ""


def test_validate_patch_syntax_valid(patch_engine):
    """Test syntax validation for valid patch."""
    patch = """diff --git a/hello.py b/hello.py
index 0000000..1111111 100644
--- a/hello.py
+++ b/hello.py
@@ -1,2 +1,3 @@
 def hello():
     print('Hello')
+    print('Added')
"""
    
    result = patch_engine.validate_patch_syntax(patch)
    
    assert result['valid'] is True
    assert len(result['errors']) == 0


def test_validate_patch_syntax_empty(patch_engine):
    """Test syntax validation for empty patch."""
    result = patch_engine.validate_patch_syntax("")
    
    assert result['valid'] is False
    assert 'empty' in result['errors'][0].lower()


def test_validate_patch_syntax_missing_headers(patch_engine):
    """Test syntax validation for patch missing headers."""
    patch = "@@ -1,2 +1,3 @@\n line\n+added\n"
    
    result = patch_engine.validate_patch_syntax(patch)
    
    assert result['valid'] is True  # Still valid, just has warnings
    assert len(result['warnings']) > 0


def test_apply_patch_interactive_dry_run(patch_engine, test_workpad):
    """Test interactive patch application in dry run mode."""
    patch = """diff --git a/hello.py b/hello.py
index 0000000..1111111 100644
--- a/hello.py
+++ b/hello.py
@@ -1,2 +1,3 @@
 def hello():
     print('Hello')
+    print('Dry run test')
"""
    
    result = patch_engine.apply_patch_interactive(
        test_workpad, 
        patch, 
        "Test message",
        dry_run=True
    )
    
    assert result['applied'] is False
    assert result['reason'] == 'dry_run'
    assert result['would_succeed'] is True
    assert 'preview' in result


def test_apply_patch_interactive_success(patch_engine, test_workpad):
    """Test successful interactive patch application."""
    patch = """diff --git a/hello.py b/hello.py
index 0000000..1111111 100644
--- a/hello.py
+++ b/hello.py
@@ -1,2 +1,3 @@
 def hello():
     print('Hello')
+    print('Interactive test')
"""
    
    result = patch_engine.apply_patch_interactive(
        test_workpad, 
        patch, 
        "Interactive commit"
    )
    
    assert result['applied'] is True
    assert 'checkpoint_id' in result
    assert 'preview' in result


def test_apply_patch_interactive_invalid_syntax(patch_engine, test_workpad):
    """Test interactive application with invalid syntax."""
    result = patch_engine.apply_patch_interactive(
        test_workpad,
        "",  # Empty patch
        "Test"
    )
    
    assert result['applied'] is False
    assert result['reason'] == 'invalid_syntax'
    assert len(result['errors']) > 0


def test_apply_patch_interactive_with_conflicts(patch_engine, git_engine, test_workpad):
    """Test interactive application with conflicts."""
    # Apply initial patch
    patch1 = """diff --git a/hello.py b/hello.py
index 0000000..1111111 100644
--- a/hello.py
+++ b/hello.py
@@ -1,2 +1,3 @@
 def hello():
     print('Hello')
+    print('First')
"""
    git_engine.apply_patch(test_workpad, patch1)
    
    # Try conflicting patch
    patch2 = """diff --git a/hello.py b/hello.py
index 0000000..2222222 100644
--- a/hello.py
+++ b/hello.py
@@ -1,2 +1,3 @@
 def hello():
     print('Hello')
+    print('Conflicts with first')
"""
    
    result = patch_engine.apply_patch_interactive(test_workpad, patch2, "Test")
    
    assert result['applied'] is False
    assert result['reason'] == 'has_conflicts'
    assert 'preview' in result


def test_patch_stats_with_file_creation(patch_engine):
    """Test patch stats for file creation."""
    patch = """diff --git a/new_file.py b/new_file.py
new file mode 100644
index 0000000..1111111
--- /dev/null
+++ b/new_file.py
@@ -0,0 +1,5 @@
+def new_function():
+    pass
+
+if __name__ == '__main__':
+    new_function()
"""
    
    stats = patch_engine.get_patch_stats(patch)
    
    assert stats['files_affected'] == 1
    assert 'new_file.py' in stats['files_list']
    assert stats['additions'] == 5
    assert stats['deletions'] == 0


def test_patch_stats_with_file_deletion(patch_engine):
    """Test patch stats for file deletion."""
    patch = """diff --git a/old_file.py b/old_file.py
deleted file mode 100644
index 1111111..0000000
--- a/old_file.py
+++ /dev/null
@@ -1,5 +0,0 @@
-def old_function():
-    pass
-
-if __name__ == '__main__':
-    old_function()
"""
    
    stats = patch_engine.get_patch_stats(patch)
    
    assert stats['files_affected'] == 1
    assert 'old_file.py' in stats['files_list']
    assert stats['additions'] == 0
    assert stats['deletions'] == 5
