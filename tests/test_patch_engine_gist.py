
import pytest
from unittest.mock import patch, MagicMock
from sologit.engines.patch_engine import PatchEngine, GistError
from sologit.engines.git_engine import GitEngine
import tempfile
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO

@pytest.fixture
def git_engine():
    """Create GitEngine with temporary data directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = GitEngine(data_dir=Path(tmpdir))
        yield engine

@pytest.fixture
def patch_engine(git_engine):
    """Fixture for a PatchEngine with a mocked GitEngine."""
    return PatchEngine(git_engine)

@pytest.fixture
def sample_zip():
    """Create a sample zip file."""
    buffer = BytesIO()
    with ZipFile(buffer, 'w') as zf:
        zf.writestr('file.txt', 'hello\\n')
    buffer.seek(0)
    return buffer.read()

@patch('requests.get')
def test_apply_patch_from_gist_success(mock_get, patch_engine, git_engine, sample_zip):
    """Test successfully applying a patch from a Gist."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "--- a/file.txt\n+++ b/file.txt\n@@ -1 +1 @@\n-hello\n+world\n"
    mock_get.return_value = mock_response

    repo_id = git_engine.init_from_zip(sample_zip, "Test Repo")
    pad_id = git_engine.create_workpad(repo_id, "test-pad")

    gist_url = "https://gist.github.com/user/12345"
    checkpoint_id = patch_engine.apply_patch_from_gist(pad_id, gist_url, "test message")

    mock_get.assert_called_once_with(gist_url + "/raw", timeout=10)
    assert checkpoint_id is not None

@patch('sologit.engines.patch_engine.requests.get')
def test_apply_patch_from_gist_fetch_error(mock_get, patch_engine, git_engine, sample_zip):
    """Test that a GistError is raised when the Gist fetch fails."""
    mock_get.side_effect = Exception("Network error")

    repo_id = git_engine.init_from_zip(sample_zip, "Test Repo")
    pad_id = git_engine.create_workpad(repo_id, "test-pad")

    with pytest.raises(GistError):
        patch_engine.apply_patch_from_gist(pad_id, "https://gist.github.com/user/12345")

def test_apply_patch_from_invalid_url(patch_engine, git_engine, sample_zip):
    """Test that a GistError is raised for an invalid Gist URL."""
    repo_id = git_engine.init_from_zip(sample_zip, "Test Repo")
    pad_id = git_engine.create_workpad(repo_id, "test-pad")
    with pytest.raises(GistError):
        patch_engine.apply_patch_from_gist(pad_id, "https://example.com")
