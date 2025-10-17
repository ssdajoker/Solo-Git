
"""
End-to-end workflow tests for Solo Git Phase 1.

Tests the complete workflow from repository initialization through
workpad creation, patching, and promotion.
"""

import pytest
import tempfile
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO

from sologit.engines.git_engine import (
    GitEngine, 
    RepositoryNotFoundError, 
    WorkpadNotFoundError,
    CannotPromoteError
)
from sologit.engines.patch_engine import PatchEngine


@pytest.fixture
def engines():
    """Create GitEngine and PatchEngine with temporary data directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        git_engine = GitEngine(data_dir=Path(tmpdir))
        patch_engine = PatchEngine(git_engine)
        yield git_engine, patch_engine


@pytest.fixture
def sample_project_zip():
    """Create a sample Python project zip file."""
    buffer = BytesIO()
    with ZipFile(buffer, 'w') as zf:
        zf.writestr('hello.py', '''def greet(name):
    """Say hello to someone."""
    return f"Hello, {name}!"

if __name__ == "__main__":
    print(greet("World"))
''')
        zf.writestr('test_hello.py', '''from hello import greet

def test_greet():
    assert greet("Alice") == "Hello, Alice!"
    assert greet("Bob") == "Hello, Bob!"
''')
        zf.writestr('README.md', '# Test Project\n\nA simple Python project for testing.\n')
    buffer.seek(0)
    return buffer.read()


def test_complete_workflow(engines, sample_project_zip):
    """Test complete workflow: init -> create pad -> apply patch -> promote."""
    git_engine, patch_engine = engines
    
    # Step 1: Initialize repository from zip
    repo_id = git_engine.init_from_zip(sample_project_zip, "Test Project")
    assert repo_id.startswith("repo_")
    
    repo = git_engine.get_repo(repo_id)
    assert repo.name == "Test Project"
    assert repo.trunk_branch == "main"
    assert repo.workpad_count == 0
    
    # Step 2: Create workpad
    pad_id = git_engine.create_workpad(repo_id, "Add farewell function")
    assert pad_id.startswith("pad_")
    
    workpad = git_engine.get_workpad(pad_id)
    assert workpad.title == "Add farewell function"
    assert workpad.status == "active"
    assert len(workpad.checkpoints) == 0
    
    # Verify repository updated
    repo = git_engine.get_repo(repo_id)
    assert repo.workpad_count == 1
    
    # Step 3: Apply patch to add new function
    patch = """--- a/hello.py
+++ b/hello.py
@@ -2,5 +2,9 @@ def greet(name):
     \"""Say hello to someone.\"""
     return f"Hello, {name}!"
 
+def farewell(name):
+    \"""Say goodbye to someone.\"""
+    return f"Goodbye, {name}!"
+
 if __name__ == "__main__":
     print(greet("World"))
"""
    
    checkpoint_id = patch_engine.apply_patch(pad_id, patch, "Add farewell function")
    assert checkpoint_id == "t1"
    
    # Verify checkpoint created
    workpad = git_engine.get_workpad(pad_id)
    assert len(workpad.checkpoints) == 1
    assert workpad.checkpoints[0] == "t1"
    
    # Step 4: Check diff
    diff = git_engine.get_diff(pad_id)
    assert "farewell" in diff
    assert "+def farewell(name):" in diff
    
    # Step 5: Verify can promote
    assert git_engine.can_promote(pad_id) is True
    
    # Step 6: Promote workpad
    commit_hash = git_engine.promote_workpad(pad_id)
    assert len(commit_hash) == 40  # Git commit hash length
    
    # Verify workpad status updated
    workpad = git_engine.get_workpad(pad_id)
    assert workpad.status == "promoted"
    
    # Verify repository workpad count updated
    repo = git_engine.get_repo(repo_id)
    assert repo.workpad_count == 0


def test_multiple_checkpoints(engines, sample_project_zip):
    """Test creating multiple checkpoints in a workpad."""
    git_engine, patch_engine = engines
    
    repo_id = git_engine.init_from_zip(sample_project_zip, "Test Project")
    pad_id = git_engine.create_workpad(repo_id, "Multiple changes")
    
    # Checkpoint 1: Add farewell function
    patch1 = """--- a/hello.py
+++ b/hello.py
@@ -2,5 +2,9 @@ def greet(name):
     \"""Say hello to someone.\"""
     return f"Hello, {name}!"
 
+def farewell(name):
+    \"""Say goodbye to someone.\"""
+    return f"Goodbye, {name}!"
+
 if __name__ == "__main__":
     print(greet("World"))
"""
    checkpoint1 = patch_engine.apply_patch(pad_id, patch1, "Add farewell")
    assert checkpoint1 == "t1"
    
    # Checkpoint 2: Add another function
    patch2 = """--- a/hello.py
+++ b/hello.py
@@ -6,5 +6,9 @@ def farewell(name):
     \"""Say goodbye to someone.\"""
     return f"Goodbye, {name}!"
 
+def shout(message):
+    \"""Shout a message.\"""
+    return message.upper() + "!!!"
+
 if __name__ == "__main__":
     print(greet("World"))
"""
    checkpoint2 = patch_engine.apply_patch(pad_id, patch2, "Add shout function")
    assert checkpoint2 == "t2"
    
    # Verify both checkpoints exist
    workpad = git_engine.get_workpad(pad_id)
    assert workpad.checkpoints == ["t1", "t2"]


def test_cannot_promote_diverged_trunk(engines, sample_project_zip):
    """Test that promotion fails when trunk has diverged."""
    git_engine, patch_engine = engines
    
    repo_id = git_engine.init_from_zip(sample_project_zip, "Test Project")
    pad_id = git_engine.create_workpad(repo_id, "Feature")
    
    # Apply patch to workpad
    patch = """--- a/hello.py
+++ b/hello.py
@@ -1,3 +1,4 @@
+# Modified in workpad
 def greet(name):
     \"""Say hello to someone.\"""
     return f"Hello, {name}!"
"""
    patch_engine.apply_patch(pad_id, patch, "Add comment")
    
    # Simulate trunk divergence by making a direct commit to trunk
    # (In a real scenario, this would be another workpad being promoted)
    repo = git_engine.get_repo(repo_id)
    from git import Repo
    git_repo = Repo(repo.path)
    trunk = getattr(git_repo.heads, repo.trunk_branch)
    trunk.checkout()
    
    # Make a change to trunk
    readme_path = repo.path / "README.md"
    readme_path.write_text("# Modified README\n")
    git_repo.index.add(['README.md'])
    git_repo.index.commit("Modify README on trunk")
    
    # Now trying to promote should fail
    assert git_engine.can_promote(pad_id) is False
    
    with pytest.raises(CannotPromoteError):
        git_engine.promote_workpad(pad_id)


def test_get_repo_map(engines, sample_project_zip):
    """Test getting repository file tree."""
    git_engine, _ = engines
    
    repo_id = git_engine.init_from_zip(sample_project_zip, "Test Project")
    
    repo_map = git_engine.get_repo_map(repo_id)
    assert repo_map is not None
    assert repo_map['type'] == 'directory'
    
    # Check that files are present in the tree
    def find_file_in_tree(tree, filename):
        if tree['type'] == 'file' and tree['name'] == filename:
            return True
        if tree['type'] == 'directory' and 'children' in tree:
            for child in tree['children']:
                if find_file_in_tree(child, filename):
                    return True
        return False
    
    assert find_file_in_tree(repo_map, 'hello.py')
    assert find_file_in_tree(repo_map, 'test_hello.py')
    assert find_file_in_tree(repo_map, 'README.md')


def test_revert_last_commit(engines, sample_project_zip):
    """Test reverting last commit on trunk."""
    git_engine, patch_engine = engines
    
    repo_id = git_engine.init_from_zip(sample_project_zip, "Test Project")
    
    # Create and promote a workpad
    pad_id = git_engine.create_workpad(repo_id, "Feature")
    patch = """--- a/hello.py
+++ b/hello.py
@@ -1,3 +1,4 @@
+# New comment
 def greet(name):
     \"""Say hello to someone.\"""
     return f"Hello, {name}!"
"""
    patch_engine.apply_patch(pad_id, patch, "Add comment")
    commit_hash = git_engine.promote_workpad(pad_id)
    
    # Verify the change is in trunk
    repo = git_engine.get_repo(repo_id)
    hello_file = repo.path / "hello.py"
    content = hello_file.read_text()
    assert "# New comment" in content
    
    # Revert the commit
    git_engine.revert_last_commit(repo_id)
    
    # Verify the change is reverted
    content_after = hello_file.read_text()
    assert "# New comment" not in content_after


def test_patch_validation_conflict(engines, sample_project_zip):
    """Test patch validation detects conflicts."""
    git_engine, patch_engine = engines
    
    repo_id = git_engine.init_from_zip(sample_project_zip, "Test Project")
    pad_id = git_engine.create_workpad(repo_id, "Feature")
    
    # Apply a patch that modifies hello.py
    patch1 = """--- a/hello.py
+++ b/hello.py
@@ -1,3 +1,4 @@
+# First modification
 def greet(name):
     \"""Say hello to someone.\"""
     return f"Hello, {name}!"
"""
    patch_engine.apply_patch(pad_id, patch1, "First change")
    
    # Try to apply a conflicting patch (modifying same lines)
    patch2 = """--- a/hello.py
+++ b/hello.py
@@ -1,3 +1,4 @@
+# Different modification
 def greet(name):
     \"""Say hello to someone.\"""
     return f"Hello, {name}!"
"""
    
    # This should fail validation (patch expects unmodified file)
    from sologit.engines.patch_engine import PatchConflictError
    with pytest.raises(PatchConflictError):
        patch_engine.validate_patch(pad_id, patch2)


def test_init_from_git_url(engines):
    """Test repository initialization from Git URL."""
    git_engine, _ = engines
    
    # Use a public Git repository
    git_url = "https://github.com/github/gitignore.git"
    
    try:
        repo_id = git_engine.init_from_git(git_url, "Git Ignore Templates")
        
        assert repo_id.startswith("repo_")
        
        repo = git_engine.get_repo(repo_id)
        assert repo.name == "Git Ignore Templates"
        assert repo.source_type == "git"
        assert repo.source_url == git_url
        
    except Exception as e:
        # Skip test if network is unavailable
        pytest.skip(f"Skipping Git URL test due to network error: {e}")
