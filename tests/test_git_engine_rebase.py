
import pytest
from pathlib import Path
import tempfile
from zipfile import ZipFile
from io import BytesIO
from git import Repo

from sologit.engines.git_engine import GitEngine, RebaseConflictError, WorkpadNotFoundError

@pytest.fixture
def git_engine():
    """Create GitEngine with temporary data directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = GitEngine(data_dir=Path(tmpdir))
        yield engine

def create_test_repo_with_divergence(engine: GitEngine):
    """Creates a test repo with a workpad that has diverged from the trunk."""
    zip_buffer = BytesIO()
    with ZipFile(zip_buffer, 'w') as zf:
        zf.writestr('file.txt', 'initial content')
    zip_buffer.seek(0)

    repo_id = engine.init_from_zip(zip_buffer.read(), name='Test Repo')
    repo = engine.get_repo(repo_id)

    pad_id = engine.create_workpad(repo_id, 'feature-branch')

    repo_path = Path(repo.path)
    git_repo = Repo(repo_path)

    # Switch to trunk to make a commit
    git_repo.heads.main.checkout()
    (repo_path / 'file.txt').write_text('commit on trunk')
    git_repo.index.add(['file.txt'])
    git_repo.index.commit('Commit on trunk')

    # Make a commit on the workpad
    workpad = engine.get_workpad(pad_id)
    git_repo.heads[workpad.branch_name].checkout()
    (repo_path / 'another_file.txt').write_text('new file on workpad')
    git_repo.index.add(['another_file.txt'])
    git_repo.index.commit('Commit on workpad')

    return repo_id, pad_id

def test_rebase_workpad_success(git_engine: GitEngine):
    """Test successful rebase of a workpad."""
    repo_id, pad_id = create_test_repo_with_divergence(git_engine)

    git_engine.rebase_workpad(pad_id)

    repo = Repo(git_engine.get_repo(repo_id).path)
    workpad = git_engine.get_workpad(pad_id)

    trunk_commit = repo.heads['main'].commit
    workpad_commit = repo.heads[workpad.branch_name].commit

    assert trunk_commit in workpad_commit.parents

def test_rebase_workpad_with_conflict(git_engine: GitEngine):
    """Test that a rebase with conflicts raises a RebaseConflictError."""
    zip_buffer = BytesIO()
    with ZipFile(zip_buffer, 'w') as zf:
        zf.writestr('file.txt', 'initial content')
    zip_buffer.seek(0)

    repo_id = git_engine.init_from_zip(zip_buffer.read(), name='Test Repo')
    repo = git_engine.get_repo(repo_id)

    pad_id = git_engine.create_workpad(repo_id, 'feature-branch')

    repo_path = Path(repo.path)
    git_repo = Repo(repo_path)

    # Make conflicting commits
    git_repo.heads.main.checkout()
    (repo_path / 'file.txt').write_text('change on trunk')
    git_repo.index.add(['file.txt'])
    git_repo.index.commit('Change on trunk')

    workpad = git_engine.get_workpad(pad_id)
    git_repo.heads[workpad.branch_name].checkout()
    (repo_path / 'file.txt').write_text('change on workpad')
    git_repo.index.add(['file.txt'])
    git_repo.index.commit('Change on workpad')

    with pytest.raises(RebaseConflictError):
        git_engine.rebase_workpad(pad_id)
