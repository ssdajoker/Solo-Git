
"""
Extended tests for Git Engine - testing all new features.
"""

import pytest
import tempfile
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
from datetime import datetime, timedelta

from sologit.engines.git_engine import (
    GitEngine, 
    RepositoryNotFoundError, 
    WorkpadNotFoundError,
    GitEngineError
)


@pytest.fixture
def git_engine():
    """Create GitEngine with temporary data directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = GitEngine(data_dir=Path(tmpdir))
        yield engine


@pytest.fixture
def sample_zip():
    """Create a sample zip file with multiple files."""
    buffer = BytesIO()
    with ZipFile(buffer, 'w') as zf:
        zf.writestr('README.md', '# Test Project\n\nThis is a test.')
        zf.writestr('main.py', 'def main():\n    print("Hello, World!")\n')
        zf.writestr('lib/utils.py', 'def helper():\n    return True\n')
        zf.writestr('tests/test_main.py', 'def test_main():\n    assert True\n')
    buffer.seek(0)
    return buffer.read()


@pytest.fixture
def repo_with_workpad(git_engine, sample_zip):
    """Create a repository with a workpad and some changes."""
    repo_id = git_engine.init_from_zip(sample_zip, "Test Repo")
    pad_id = git_engine.create_workpad(repo_id, "Test Feature")
    return repo_id, pad_id


# ============================================================================
# Git History & Log Tests
# ============================================================================

def test_get_history(git_engine, sample_zip):
    """Test getting commit history."""
    repo_id = git_engine.init_from_zip(sample_zip, "Test Repo")
    
    history = git_engine.get_history(repo_id, limit=10)
    
    assert len(history) == 1  # Initial commit
    assert 'hash' in history[0]
    assert 'short_hash' in history[0]
    assert 'author' in history[0]
    assert 'message' in history[0]
    assert history[0]['message'] == 'Initial commit from zip'


def test_get_history_with_multiple_commits(git_engine, repo_with_workpad):
    """Test history with multiple commits."""
    repo_id, pad_id = repo_with_workpad
    
    # Create a commit via patch
    patch = """diff --git a/newfile.txt b/newfile.txt
new file mode 100644
index 0000000..ce01362
--- /dev/null
+++ b/newfile.txt
@@ -0,0 +1 @@
+hello
"""
    git_engine.apply_patch(pad_id, patch, "Add new file")
    
    # Get workpad to check branch name
    workpad = git_engine.get_workpad(pad_id)
    history = git_engine.get_history(repo_id, branch=workpad.branch_name)
    
    assert len(history) >= 2  # Initial commit + our commit


def test_get_history_invalid_repo(git_engine):
    """Test getting history from invalid repo."""
    with pytest.raises(RepositoryNotFoundError):
        git_engine.get_history("repo_invalid")


# ============================================================================
# Status Tests
# ============================================================================

def test_get_status_clean_repo(git_engine, sample_zip):
    """Test status on clean repository."""
    repo_id = git_engine.init_from_zip(sample_zip, "Test Repo")
    
    status = git_engine.get_status(repo_id)
    
    assert status['is_clean'] is True
    assert status['has_changes'] is False
    assert len(status['changed_files']) == 0
    assert len(status['staged_files']) == 0
    assert len(status['untracked_files']) == 0


def test_get_status_invalid_repo(git_engine):
    """Test status on invalid repository."""
    with pytest.raises(RepositoryNotFoundError):
        git_engine.get_status("repo_invalid")


# ============================================================================
# File Content Tests
# ============================================================================

def test_get_file_content(git_engine, sample_zip):
    """Test reading file content."""
    repo_id = git_engine.init_from_zip(sample_zip, "Test Repo")
    
    content = git_engine.get_file_content(repo_id, "README.md")
    
    assert "Test Project" in content
    assert "This is a test" in content


def test_get_file_content_from_subdirectory(git_engine, sample_zip):
    """Test reading file from subdirectory."""
    repo_id = git_engine.init_from_zip(sample_zip, "Test Repo")
    
    content = git_engine.get_file_content(repo_id, "lib/utils.py")
    
    assert "def helper()" in content


def test_get_file_content_invalid_file(git_engine, sample_zip):
    """Test reading non-existent file."""
    repo_id = git_engine.init_from_zip(sample_zip, "Test Repo")
    
    with pytest.raises(GitEngineError):
        git_engine.get_file_content(repo_id, "nonexistent.txt")


# ============================================================================
# Checkpoint & Rollback Tests
# ============================================================================

def test_rollback_to_checkpoint(git_engine, repo_with_workpad):
    """Test rolling back to a checkpoint."""
    repo_id, pad_id = repo_with_workpad
    
    # Create first checkpoint
    patch1 = """diff --git a/file1.txt b/file1.txt
new file mode 100644
index 0000000..ce01362
--- /dev/null
+++ b/file1.txt
@@ -0,0 +1 @@
+first
"""
    git_engine.apply_patch(pad_id, patch1, "First change")
    
    # Create second checkpoint
    patch2 = """diff --git a/file2.txt b/file2.txt
new file mode 100644
index 0000000..0cfbf08
--- /dev/null
+++ b/file2.txt
@@ -0,0 +1 @@
+second
"""
    git_engine.apply_patch(pad_id, patch2, "Second change")
    
    # Get workpad and verify 2 checkpoints
    workpad = git_engine.get_workpad(pad_id)
    assert len(workpad.checkpoints) == 2
    
    # Rollback to first checkpoint
    git_engine.rollback_to_checkpoint(pad_id, 't1')
    
    # Verify only 1 checkpoint remains
    workpad = git_engine.get_workpad(pad_id)
    assert len(workpad.checkpoints) == 1
    assert workpad.checkpoints[0] == 't1'


def test_rollback_invalid_checkpoint(git_engine, repo_with_workpad):
    """Test rollback to non-existent checkpoint."""
    repo_id, pad_id = repo_with_workpad
    
    with pytest.raises(GitEngineError):
        git_engine.rollback_to_checkpoint(pad_id, 't999')


# ============================================================================
# Workpad Deletion Tests
# ============================================================================

def test_delete_workpad(git_engine, repo_with_workpad):
    """Test deleting a workpad."""
    repo_id, pad_id = repo_with_workpad
    
    # Verify workpad exists
    assert git_engine.get_workpad(pad_id) is not None
    
    # Delete workpad
    git_engine.delete_workpad(pad_id, force=True)
    
    # Verify status changed to deleted
    workpad = git_engine.get_workpad(pad_id)
    assert workpad.status == "deleted"
    
    # Verify repo workpad count decreased
    repo = git_engine.get_repo(repo_id)
    assert repo.workpad_count == 0


def test_delete_workpad_with_checkpoints(git_engine, repo_with_workpad):
    """Test deleting workpad that has checkpoints."""
    repo_id, pad_id = repo_with_workpad
    
    # Create checkpoint
    patch = """diff --git a/test.txt b/test.txt
new file mode 100644
index 0000000..9daeafb
--- /dev/null
+++ b/test.txt
@@ -0,0 +1 @@
+test
"""
    git_engine.apply_patch(pad_id, patch, "Add test file")
    
    # Delete should work
    git_engine.delete_workpad(pad_id, force=True)
    
    workpad = git_engine.get_workpad(pad_id)
    assert workpad.status == "deleted"


# ============================================================================
# Workpad Stats Tests
# ============================================================================

def test_get_workpad_stats(git_engine, repo_with_workpad):
    """Test getting workpad statistics."""
    repo_id, pad_id = repo_with_workpad
    
    # Add some changes using create_commit instead of patch
    # (patches are tricky to format correctly in tests)
    repo = git_engine.get_repo(repo_id)
    feature_file = repo.path / "feature.py"
    feature_file.write_text("""def new_feature():
    print("New feature")
    return True
""")
    
    git_engine.create_commit(repo_id, pad_id, "Add feature")
    
    stats = git_engine.get_workpad_stats(pad_id)
    
    assert stats['pad_id'] == pad_id
    assert 'files_changed' in stats
    assert 'commits_ahead' in stats
    assert 'checkpoints' in stats
    assert stats['checkpoints'] == 1
    assert stats['status'] == 'active'


# ============================================================================
# Cleanup Tests
# ============================================================================

def test_cleanup_stale_workpads(git_engine, sample_zip):
    """Test cleaning up stale workpads."""
    repo_id = git_engine.init_from_zip(sample_zip, "Test Repo")
    
    # Create workpad
    pad_id = git_engine.create_workpad(repo_id, "Old Feature")
    
    # Manually set old last_activity
    workpad = git_engine.get_workpad(pad_id)
    workpad.last_activity = datetime.now() - timedelta(days=10)
    git_engine._save_metadata()
    
    # Cleanup (default 7 days)
    deleted = git_engine.cleanup_stale_workpads(days=7)
    
    assert pad_id in deleted
    assert len(deleted) == 1


def test_cleanup_preserves_recent_workpads(git_engine, repo_with_workpad):
    """Test that cleanup preserves recent workpads."""
    repo_id, pad_id = repo_with_workpad
    
    # Cleanup shouldn't delete recent workpad
    deleted = git_engine.cleanup_stale_workpads(days=7)
    
    assert pad_id not in deleted
    workpad = git_engine.get_workpad(pad_id)
    assert workpad.status == "active"


# ============================================================================
# Branch & Tag Listing Tests
# ============================================================================

def test_list_branches(git_engine, repo_with_workpad):
    """Test listing all branches."""
    repo_id, pad_id = repo_with_workpad
    
    branches = git_engine.list_branches(repo_id)
    
    assert len(branches) >= 2  # main + workpad branch
    
    # Check for trunk
    trunk_branches = [b for b in branches if b['is_trunk']]
    assert len(trunk_branches) == 1
    assert trunk_branches[0]['name'] == 'main'
    
    # Check for workpad
    workpad_branches = [b for b in branches if b['is_workpad']]
    assert len(workpad_branches) >= 1


def test_list_tags(git_engine, repo_with_workpad):
    """Test listing all tags."""
    repo_id, pad_id = repo_with_workpad
    
    # Create checkpoint (which creates tag)
    patch = """diff --git a/test.txt b/test.txt
new file mode 100644
index 0000000..9daeafb
--- /dev/null
+++ b/test.txt
@@ -0,0 +1 @@
+test
"""
    git_engine.apply_patch(pad_id, patch, "Add test")
    
    tags = git_engine.list_tags(repo_id)
    
    assert len(tags) >= 1
    checkpoint_tags = [t for t in tags if t['is_checkpoint']]
    assert len(checkpoint_tags) >= 1


# ============================================================================
# Direct Commit Tests
# ============================================================================

def test_create_commit(git_engine, repo_with_workpad):
    """Test creating direct commit."""
    repo_id, pad_id = repo_with_workpad
    
    # Get repository path and create a file
    repo = git_engine.get_repo(repo_id)
    test_file = repo.path / "direct_test.txt"
    test_file.write_text("Direct commit test")
    
    # Create commit
    commit_hash = git_engine.create_commit(
        repo_id, 
        pad_id, 
        "Direct commit message"
    )
    
    assert commit_hash is not None
    assert len(commit_hash) == 40  # Full SHA-1 hash
    
    # Verify checkpoint was created
    workpad = git_engine.get_workpad(pad_id)
    assert len(workpad.checkpoints) == 1


# ============================================================================
# Commits Ahead/Behind Tests
# ============================================================================

def test_get_commits_ahead_behind(git_engine, repo_with_workpad):
    """Test getting commits ahead/behind trunk."""
    repo_id, pad_id = repo_with_workpad
    
    # Initially no commits ahead
    result = git_engine.get_commits_ahead_behind(pad_id)
    assert result['ahead'] == 0
    assert result['behind'] == 0
    assert result['can_fast_forward'] is True
    
    # Add commit to workpad
    patch = """diff --git a/new.txt b/new.txt
new file mode 100644
index 0000000..ce01362
--- /dev/null
+++ b/new.txt
@@ -0,0 +1 @@
+new
"""
    git_engine.apply_patch(pad_id, patch, "Add new file")
    
    # Now should be ahead
    result = git_engine.get_commits_ahead_behind(pad_id)
    assert result['ahead'] >= 1
    assert result['behind'] == 0
    assert result['can_fast_forward'] is True


# ============================================================================
# List Files Tests
# ============================================================================

def test_list_files(git_engine, sample_zip):
    """Test listing tracked files."""
    repo_id = git_engine.init_from_zip(sample_zip, "Test Repo")
    
    files = git_engine.list_files(repo_id)
    
    assert 'README.md' in files
    assert 'main.py' in files
    assert 'lib/utils.py' in files
    assert 'tests/test_main.py' in files
    assert len(files) == 4


# ============================================================================
# Input Validation Tests
# ============================================================================

def test_init_from_zip_empty_name(git_engine, sample_zip):
    """Test initialization with empty name."""
    with pytest.raises(GitEngineError, match="name cannot be empty"):
        git_engine.init_from_zip(sample_zip, "")


def test_init_from_zip_empty_buffer(git_engine):
    """Test initialization with empty buffer."""
    with pytest.raises(GitEngineError, match="buffer cannot be empty"):
        git_engine.init_from_zip(b"", "Test")


def test_init_from_zip_long_name(git_engine, sample_zip):
    """Test initialization with too long name."""
    long_name = "x" * 300
    with pytest.raises(GitEngineError, match="name too long"):
        git_engine.init_from_zip(sample_zip, long_name)


def test_create_workpad_empty_title(git_engine, sample_zip):
    """Test creating workpad with empty title."""
    repo_id = git_engine.init_from_zip(sample_zip, "Test Repo")
    
    with pytest.raises(GitEngineError, match="title cannot be empty"):
        git_engine.create_workpad(repo_id, "")


def test_create_workpad_long_title(git_engine, sample_zip):
    """Test creating workpad with too long title."""
    repo_id = git_engine.init_from_zip(sample_zip, "Test Repo")
    
    long_title = "x" * 150
    with pytest.raises(GitEngineError, match="title too long"):
        git_engine.create_workpad(repo_id, long_title)


def test_apply_patch_empty_patch(git_engine, repo_with_workpad):
    """Test applying empty patch."""
    repo_id, pad_id = repo_with_workpad
    
    with pytest.raises(GitEngineError, match="Patch cannot be empty"):
        git_engine.apply_patch(pad_id, "")


def test_validate_repo_id(git_engine):
    """Test repository ID validation."""
    with pytest.raises(GitEngineError, match="Invalid repository ID"):
        git_engine._validate_repo_id("invalid")
    
    with pytest.raises(GitEngineError, match="Invalid repository ID"):
        git_engine._validate_repo_id("")


def test_validate_pad_id(git_engine):
    """Test workpad ID validation."""
    with pytest.raises(GitEngineError, match="Invalid workpad ID"):
        git_engine._validate_pad_id("invalid")
    
    with pytest.raises(GitEngineError, match="Invalid workpad ID"):
        git_engine._validate_pad_id("")


# ============================================================================
# Integration Tests
# ============================================================================

def test_full_workflow_with_new_features(git_engine, sample_zip):
    """Test complete workflow using all new features."""
    # Initialize
    repo_id = git_engine.init_from_zip(sample_zip, "Full Test")
    
    # Check initial history
    history = git_engine.get_history(repo_id)
    assert len(history) == 1
    
    # Create workpad
    pad_id = git_engine.create_workpad(repo_id, "Feature A")
    
    # Check status
    status = git_engine.get_status(repo_id, pad_id)
    assert status['is_clean'] is True
    
    # Add changes via patches
    patch1 = """diff --git a/feature_a.py b/feature_a.py
new file mode 100644
index 0000000..ce01362
--- /dev/null
+++ b/feature_a.py
@@ -0,0 +1 @@
+feature a
"""
    git_engine.apply_patch(pad_id, patch1, "Add feature A")
    
    patch2 = """diff --git a/feature_a.py b/feature_a.py
index ce01362..d00491f 100644
--- a/feature_a.py
+++ b/feature_a.py
@@ -1 +1,2 @@
 feature a
+more code
"""
    git_engine.apply_patch(pad_id, patch2, "Enhance feature A")
    
    # Check stats
    stats = git_engine.get_workpad_stats(pad_id)
    assert stats['checkpoints'] == 2
    assert stats['commits_ahead'] >= 2
    
    # Check commits ahead/behind
    result = git_engine.get_commits_ahead_behind(pad_id)
    assert result['ahead'] >= 2
    assert result['can_fast_forward'] is True
    
    # List branches
    branches = git_engine.list_branches(repo_id)
    assert len(branches) >= 2  # At least main + workpad (might have master too)
    
    # List tags (checkpoints)
    tags = git_engine.list_tags(repo_id)
    assert len(tags) == 2
    
    # Rollback to first checkpoint
    git_engine.rollback_to_checkpoint(pad_id, 't1')
    
    workpad = git_engine.get_workpad(pad_id)
    assert len(workpad.checkpoints) == 1
    
    # Promote workpad
    commit_hash = git_engine.promote_workpad(pad_id)
    assert commit_hash is not None
    
    # Verify promotion
    workpad = git_engine.get_workpad(pad_id)
    assert workpad.status == "promoted"
    
    # Check final history
    final_history = git_engine.get_history(repo_id)
    assert len(final_history) >= 2  # Initial + checkpoint


def test_error_recovery_workflow(git_engine, sample_zip):
    """Test error handling and recovery in workflow."""
    repo_id = git_engine.init_from_zip(sample_zip, "Error Test")
    pad_id = git_engine.create_workpad(repo_id, "Test Pad")
    
    # Try to read non-existent file
    with pytest.raises(GitEngineError):
        git_engine.get_file_content(repo_id, "nonexistent.txt")
    
    # Try to rollback to non-existent checkpoint
    with pytest.raises(GitEngineError):
        git_engine.rollback_to_checkpoint(pad_id, 't999')
    
    # Engine should still work after errors
    history = git_engine.get_history(repo_id)
    assert len(history) >= 1
    
    status = git_engine.get_status(repo_id)
    assert 'is_clean' in status
