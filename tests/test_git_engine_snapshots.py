
import pytest
from pathlib import Path
import tempfile
from zipfile import ZipFile
from io import BytesIO
from git import Repo

from sologit.engines.git_engine import GitEngine, WorkpadNotFoundError, SnapshotNotFoundError

@pytest.fixture
def git_engine():
    """Create GitEngine with temporary data directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = GitEngine(data_dir=Path(tmpdir))
        yield engine

def create_test_repo(engine: GitEngine):
    """Creates a test repo."""
    zip_buffer = BytesIO()
    with ZipFile(zip_buffer, 'w') as zf:
        zf.writestr('file.txt', 'initial content')
    zip_buffer.seek(0)

    repo_id = engine.init_from_zip(zip_buffer.read(), name='Test Repo')
    return repo_id

def test_create_and_list_snapshots(git_engine: GitEngine):
    """Test creating and listing snapshots."""
    repo_id = create_test_repo(git_engine)
    pad_id = git_engine.create_workpad(repo_id, 'feature-branch')

    # Create a snapshot
    snapshot_id = git_engine.create_snapshot(pad_id, "first snapshot")
    assert snapshot_id.startswith("snap_")

    # List snapshots
    snapshots = git_engine.list_snapshots(pad_id)
    assert len(snapshots) == 1
    assert snapshots[0].id == snapshot_id
    assert snapshots[0].message == "first snapshot"

def test_restore_snapshot(git_engine: GitEngine):
    """Test restoring a snapshot."""
    repo_id = create_test_repo(git_engine)
    pad_id = git_engine.create_workpad(repo_id, 'feature-branch')

    repo_path = Path(git_engine.get_repo(repo_id).path)
    file_path = repo_path / 'file.txt'

    # Make a change and create a snapshot
    file_path.write_text('state before snapshot')
    snapshot_id = git_engine.create_snapshot(pad_id, "snapshot to restore")

    # Make another change
    file_path.write_text('state after snapshot')

    # Restore the snapshot
    git_engine.restore_snapshot(pad_id, snapshot_id)

    # Check that the file content is restored
    assert file_path.read_text() == 'state before snapshot'

def test_delete_snapshot(git_engine: GitEngine):
    """Test deleting a snapshot."""
    repo_id = create_test_repo(git_engine)
    pad_id = git_engine.create_workpad(repo_id, 'feature-branch')

    snapshot_id = git_engine.create_snapshot(pad_id, "snapshot to delete")

    # Delete the snapshot
    git_engine.delete_snapshot(pad_id, snapshot_id)

    # Check that the snapshot is gone
    snapshots = git_engine.list_snapshots(pad_id)
    assert len(snapshots) == 0

    # Verify that trying to delete it again raises an error
    with pytest.raises(SnapshotNotFoundError):
        git_engine.delete_snapshot(pad_id, snapshot_id)
