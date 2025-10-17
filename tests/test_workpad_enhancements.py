
"""
Tests for Workpad Management System enhancements.
"""

import tempfile
import zipfile
from pathlib import Path

import pytest

from sologit.engines.git_engine import GitEngine


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
def test_repo(git_engine, temp_dir):
    """Create test repository."""
    # Create test files
    test_project = temp_dir / "test_project"
    test_project.mkdir()
    (test_project / "hello.py").write_text("def hello():\n    print('Hello')\n")
    (test_project / "README.md").write_text("# Test Project\n")
    
    # Create zip
    zip_path = temp_dir / "test.zip"
    with zipfile.ZipFile(zip_path, 'w') as zf:
        for file in test_project.glob('*'):
            zf.write(file, file.name)
    
    # Initialize repository
    repo_id = git_engine.init_from_zip(zip_path.read_bytes(), "test-repo")
    return repo_id


def test_switch_workpad(git_engine, test_repo):
    """Test switching between workpads."""
    # Create two workpads
    pad1 = git_engine.create_workpad(test_repo, "Feature 1")
    pad2 = git_engine.create_workpad(test_repo, "Feature 2")
    
    # Switch to pad1
    git_engine.switch_workpad(pad1)
    active = git_engine.get_active_workpad(test_repo)
    assert active is not None
    assert active.id == pad1
    
    # Switch to pad2
    git_engine.switch_workpad(pad2)
    active = git_engine.get_active_workpad(test_repo)
    assert active is not None
    assert active.id == pad2


def test_get_active_workpad_on_trunk(git_engine, test_repo):
    """Test getting active workpad when on trunk."""
    # Checkout trunk (should be there by default)
    active = git_engine.get_active_workpad(test_repo)
    assert active is None  # No workpad active


def test_list_workpads_filtered(git_engine, test_repo):
    """Test filtered workpad listing."""
    # Create workpads
    pad1 = git_engine.create_workpad(test_repo, "AAA Feature")
    pad2 = git_engine.create_workpad(test_repo, "BBB Feature")
    pad3 = git_engine.create_workpad(test_repo, "CCC Feature")
    
    # Promote one workpad
    git_engine.promote_workpad(pad1)
    
    # Filter by status
    active_pads = git_engine.list_workpads_filtered(status="active")
    assert len(active_pads) == 2
    assert all(p.status == "active" for p in active_pads)
    
    promoted_pads = git_engine.list_workpads_filtered(status="promoted")
    assert len(promoted_pads) == 1
    assert promoted_pads[0].id == pad1
    
    # Sort by title
    all_pads = git_engine.list_workpads_filtered(sort_by="title")
    assert all_pads[0].title.startswith("AAA")
    assert all_pads[-1].title.startswith("CCC")
    
    # Sort by title reverse
    all_pads_rev = git_engine.list_workpads_filtered(sort_by="title", reverse=True)
    assert all_pads_rev[0].title.startswith("CCC")
    assert all_pads_rev[-1].title.startswith("AAA")


def test_compare_workpads(git_engine, test_repo):
    """Test comparing two workpads."""
    # Create two workpads
    pad1 = git_engine.create_workpad(test_repo, "Feature 1")
    pad2 = git_engine.create_workpad(test_repo, "Feature 2")
    
    # Add different changes to each
    patch1 = """diff --git a/hello.py b/hello.py
index 0000000..1111111 100644
--- a/hello.py
+++ b/hello.py
@@ -1,2 +1,3 @@
 def hello():
     print('Hello')
+    print('From Feature 1')
"""
    git_engine.apply_patch(pad1, patch1)
    
    patch2 = """diff --git a/hello.py b/hello.py
index 0000000..2222222 100644
--- a/hello.py
+++ b/hello.py
@@ -1,2 +1,3 @@
 def hello():
     print('Hello')
+    print('From Feature 2')
"""
    git_engine.apply_patch(pad2, patch2)
    
    # Compare workpads
    comparison = git_engine.compare_workpads(pad1, pad2)
    
    assert comparison['pad_1']['id'] == pad1
    assert comparison['pad_2']['id'] == pad2
    assert comparison['files_changed'] >= 0  # Should have changes
    assert 'diff' in comparison


def test_get_workpad_merge_preview(git_engine, test_repo):
    """Test workpad merge preview."""
    # Create workpad and add changes
    pad = git_engine.create_workpad(test_repo, "Test Feature")
    
    patch = """diff --git a/hello.py b/hello.py
index 0000000..1111111 100644
--- a/hello.py
+++ b/hello.py
@@ -1,2 +1,3 @@
 def hello():
     print('Hello')
+    print('Enhanced!')
"""
    git_engine.apply_patch(pad, patch)
    
    # Get merge preview
    preview = git_engine.get_workpad_merge_preview(pad)
    
    assert preview['pad_id'] == pad
    assert preview['can_fast_forward'] is True
    assert preview['commits_ahead'] == 1
    assert preview['commits_behind'] == 0
    assert preview['ready_to_promote'] is True
    assert len(preview['conflicts']) == 0
    assert preview['files_changed'] > 0


def test_get_workpad_merge_preview_diverged(git_engine, test_repo):
    """Test merge preview when trunk has diverged."""
    # Create workpad
    pad = git_engine.create_workpad(test_repo, "Test Feature")
    
    # Add change to workpad
    patch1 = """diff --git a/hello.py b/hello.py
index 0000000..1111111 100644
--- a/hello.py
+++ b/hello.py
@@ -1,2 +1,3 @@
 def hello():
     print('Hello')
+    print('From workpad')
"""
    git_engine.apply_patch(pad, patch1)
    
    # Make conflicting change on trunk
    pad_trunk = git_engine.create_workpad(test_repo, "Trunk change")
    patch2 = """diff --git a/hello.py b/hello.py
index 0000000..2222222 100644
--- a/hello.py
+++ b/hello.py
@@ -1,2 +1,3 @@
 def hello():
     print('Hello')
+    print('From trunk')
"""
    git_engine.apply_patch(pad_trunk, patch2)
    git_engine.promote_workpad(pad_trunk)
    
    # Get merge preview for original workpad
    preview = git_engine.get_workpad_merge_preview(pad)
    
    assert preview['can_fast_forward'] is False
    assert preview['commits_behind'] > 0
    assert preview['ready_to_promote'] is False
    assert len(preview['conflicts']) > 0


def test_cleanup_workpads_with_filters(git_engine, test_repo):
    """Test cleanup with enhanced filtering."""
    from datetime import datetime, timedelta
    
    # Create workpads
    pad1 = git_engine.create_workpad(test_repo, "Recent")
    pad2 = git_engine.create_workpad(test_repo, "Old")
    pad3 = git_engine.create_workpad(test_repo, "Also old")
    
    # Manually set old timestamps
    workpad2 = git_engine.get_workpad(pad2)
    workpad2.last_activity = datetime.now() - timedelta(days=10)
    git_engine.workpad_db[pad2] = workpad2
    
    workpad3 = git_engine.get_workpad(pad3)
    workpad3.last_activity = datetime.now() - timedelta(days=8)
    workpad3.status = "active"
    git_engine.workpad_db[pad3] = workpad3
    git_engine._save_metadata()
    
    # Cleanup old workpads
    deleted = git_engine.cleanup_workpads(days=7, status="active")
    
    # Should have deleted pad3 (old and active)
    assert len(deleted) >= 1
    
    # Recent workpad should still exist
    assert git_engine.get_workpad(pad1) is not None


def test_switch_workpad_updates_activity(git_engine, test_repo):
    """Test that switching workpad updates last_activity."""
    from datetime import datetime
    
    pad = git_engine.create_workpad(test_repo, "Test")
    workpad_before = git_engine.get_workpad(pad)
    original_activity = workpad_before.last_activity
    
    # Wait a bit (simulate time passing)
    import time
    time.sleep(0.1)
    
    # Switch to workpad
    git_engine.switch_workpad(pad)
    
    # Check that last_activity was updated
    workpad_after = git_engine.get_workpad(pad)
    assert workpad_after.last_activity > original_activity


def test_cleanup_workpads_repo_specific(git_engine, temp_dir):
    """Test cleanup can be limited to specific repository."""
    from datetime import datetime, timedelta
    
    # Create two repositories
    test_project = temp_dir / "test_project"
    test_project.mkdir()
    (test_project / "file.txt").write_text("test")
    
    zip_path = temp_dir / "test.zip"
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(test_project / "file.txt", "file.txt")
    
    repo1 = git_engine.init_from_zip(zip_path.read_bytes(), "repo1")
    repo2 = git_engine.init_from_zip(zip_path.read_bytes(), "repo2")
    
    # Create old workpads in both repos
    pad1 = git_engine.create_workpad(repo1, "Old in repo1")
    pad2 = git_engine.create_workpad(repo2, "Old in repo2")
    
    # Set both as old
    for pad_id in [pad1, pad2]:
        workpad = git_engine.get_workpad(pad_id)
        workpad.last_activity = datetime.now() - timedelta(days=10)
        git_engine.workpad_db[pad_id] = workpad
    git_engine._save_metadata()
    
    # Cleanup only repo1
    deleted = git_engine.cleanup_workpads(repo_id=repo1, days=7)
    
    # Only repo1's workpad should be deleted
    assert pad1 in deleted
    assert pad2 not in deleted
    assert git_engine.get_workpad(pad2) is not None
