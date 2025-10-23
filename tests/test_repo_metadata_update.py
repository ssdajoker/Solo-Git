"""
Tests for repository metadata update optimization.

This test verifies the efficiency improvement where repository metadata
is updated through a targeted helper method instead of loading and 
manipulating the entire repository object.
"""

import pytest
import tempfile
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
from datetime import datetime, timedelta

from sologit.engines.git_engine import GitEngine


@pytest.fixture
def git_engine():
    """Create GitEngine with temporary data directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = GitEngine(data_dir=Path(tmpdir))
        yield engine


@pytest.fixture
def sample_zip():
    """Create a sample zip file."""
    buffer = BytesIO()
    with ZipFile(buffer, 'w') as zf:
        zf.writestr('README.md', '# Test Project\n')
        zf.writestr('main.py', 'print("Hello, World!")\n')
    buffer.seek(0)
    return buffer.read()


def test_update_repo_metadata_workpad_count(git_engine, sample_zip):
    """Test that _update_repo_metadata correctly updates workpad_count."""
    repo_id = git_engine.init_from_zip(sample_zip, "Test Repo")
    
    # Initial count should be 0
    repo = git_engine.get_repo(repo_id)
    assert repo.workpad_count == 0
    
    # Increment by 1
    git_engine._update_repo_metadata(repo_id, workpad_count_delta=1)
    repo = git_engine.get_repo(repo_id)
    assert repo.workpad_count == 1
    
    # Increment by 2 more
    git_engine._update_repo_metadata(repo_id, workpad_count_delta=2)
    repo = git_engine.get_repo(repo_id)
    assert repo.workpad_count == 3
    
    # Decrement by 1
    git_engine._update_repo_metadata(repo_id, workpad_count_delta=-1)
    repo = git_engine.get_repo(repo_id)
    assert repo.workpad_count == 2


def test_update_repo_metadata_last_activity(git_engine, sample_zip):
    """Test that _update_repo_metadata correctly updates last_activity."""
    repo_id = git_engine.init_from_zip(sample_zip, "Test Repo")
    
    # Get initial last_activity
    repo = git_engine.get_repo(repo_id)
    initial_activity = repo.last_activity
    
    # Wait a tiny bit to ensure time changes
    import time
    time.sleep(0.01)
    
    # Update metadata
    git_engine._update_repo_metadata(repo_id, workpad_count_delta=0)
    
    # Verify last_activity was updated
    repo = git_engine.get_repo(repo_id)
    assert repo.last_activity > initial_activity


def test_update_repo_metadata_no_last_activity_update(git_engine, sample_zip):
    """Test that _update_repo_metadata can skip last_activity update."""
    repo_id = git_engine.init_from_zip(sample_zip, "Test Repo")
    
    # Get initial last_activity
    repo = git_engine.get_repo(repo_id)
    initial_activity = repo.last_activity
    
    # Wait a tiny bit to ensure time would change if updated
    import time
    time.sleep(0.01)
    
    # Update metadata without updating last_activity
    git_engine._update_repo_metadata(
        repo_id, 
        workpad_count_delta=1, 
        update_last_activity=False
    )
    
    # Verify last_activity was NOT updated
    repo = git_engine.get_repo(repo_id)
    assert repo.last_activity == initial_activity
    # But workpad_count should be updated
    assert repo.workpad_count == 1


def test_create_workpad_uses_optimized_update(git_engine, sample_zip):
    """Test that create_workpad uses the optimized metadata update."""
    repo_id = git_engine.init_from_zip(sample_zip, "Test Repo")
    
    # Get initial state
    repo_before = git_engine.get_repo(repo_id)
    assert repo_before.workpad_count == 0
    initial_activity = repo_before.last_activity
    
    # Wait to ensure timestamp changes
    import time
    time.sleep(0.01)
    
    # Create workpad
    pad_id = git_engine.create_workpad(repo_id, "Test Feature")
    
    # Verify repository metadata was updated
    repo_after = git_engine.get_repo(repo_id)
    assert repo_after.workpad_count == 1
    assert repo_after.last_activity > initial_activity
    
    # Verify workpad was created
    workpad = git_engine.get_workpad(pad_id)
    assert workpad is not None
    assert workpad.title == "Test Feature"


def test_promote_workpad_uses_optimized_update(git_engine, sample_zip):
    """Test that promote_workpad uses the optimized metadata update."""
    repo_id = git_engine.init_from_zip(sample_zip, "Test Repo")
    pad_id = git_engine.create_workpad(repo_id, "Test Feature")
    
    # Create a commit in the workpad
    patch = """diff --git a/test.txt b/test.txt
new file mode 100644
index 0000000..ce01362
--- /dev/null
+++ b/test.txt
@@ -0,0 +1 @@
+hello
"""
    git_engine.apply_patch(pad_id, patch, "Add test file")
    
    # Get state before promotion
    repo_before = git_engine.get_repo(repo_id)
    assert repo_before.workpad_count == 1
    
    # Promote workpad
    commit_hash = git_engine.promote_workpad(pad_id)
    assert commit_hash is not None
    
    # Verify repository metadata was updated
    repo_after = git_engine.get_repo(repo_id)
    assert repo_after.workpad_count == 0
    
    # Verify workpad status
    workpad = git_engine.get_workpad(pad_id)
    assert workpad.status == "promoted"


def test_delete_workpad_uses_optimized_update(git_engine, sample_zip):
    """Test that delete_workpad uses the optimized metadata update."""
    repo_id = git_engine.init_from_zip(sample_zip, "Test Repo")
    pad_id = git_engine.create_workpad(repo_id, "Test Feature")
    
    # Get state before deletion
    repo_before = git_engine.get_repo(repo_id)
    assert repo_before.workpad_count == 1
    
    # Delete workpad
    git_engine.delete_workpad(pad_id, force=True)
    
    # Verify repository metadata was updated
    repo_after = git_engine.get_repo(repo_id)
    assert repo_after.workpad_count == 0
    
    # Verify workpad status
    workpad = git_engine.get_workpad(pad_id)
    assert workpad.status == "deleted"


def test_multiple_workpad_operations(git_engine, sample_zip):
    """Test multiple workpad operations maintain correct counts."""
    repo_id = git_engine.init_from_zip(sample_zip, "Test Repo")
    
    # Create 3 workpads
    pad1 = git_engine.create_workpad(repo_id, "Feature 1")
    pad2 = git_engine.create_workpad(repo_id, "Feature 2")
    pad3 = git_engine.create_workpad(repo_id, "Feature 3")
    
    repo = git_engine.get_repo(repo_id)
    assert repo.workpad_count == 3
    
    # Delete one
    git_engine.delete_workpad(pad1, force=True)
    repo = git_engine.get_repo(repo_id)
    assert repo.workpad_count == 2
    
    # Create another
    pad4 = git_engine.create_workpad(repo_id, "Feature 4")
    repo = git_engine.get_repo(repo_id)
    assert repo.workpad_count == 3
    
    # Delete two more
    git_engine.delete_workpad(pad2, force=True)
    git_engine.delete_workpad(pad3, force=True)
    repo = git_engine.get_repo(repo_id)
    assert repo.workpad_count == 1
