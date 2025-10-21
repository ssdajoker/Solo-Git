"""
Comprehensive tests to achieve 100% coverage for Git Engine.

Targets all missing coverage lines and error paths.
"""

import pytest
import tempfile
import zipfile
from pathlib import Path
from datetime import datetime, timedelta
from git import Repo
from git.exc import GitCommandError
from sologit.engines.git_engine import (
    GitEngine,
    GitEngineError,
    RepositoryNotFoundError,
    WorkpadNotFoundError,
    CannotPromoteError,
)


@pytest.fixture
def temp_dir():
    """Create temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def simple_repo_zip():
    """Create a simple repository zip file."""
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
        with zipfile.ZipFile(tmp.name, 'w') as zf:
            zf.writestr('README.md', '# Test Repo\n')
            zf.writestr('src/main.py', 'print("Hello, world!")\n')
        
        with open(tmp.name, 'rb') as f:
            return f.read()


class TestGitEngineErrorHandling:
    """Test error handling and edge cases in Git Engine."""

    def test_init_from_zip_invalid_zip(self, temp_dir):
        """Test init_from_zip with invalid zip data."""
        git_engine = GitEngine(temp_dir)
        
        invalid_zip = b"This is not a zip file"
        
        with pytest.raises(GitEngineError) as exc_info:
            git_engine.init_from_zip(invalid_zip, "invalid-repo")
        
        assert "Failed to initialize from zip" in str(exc_info.value)

    def test_init_from_zip_empty_name(self, temp_dir):
        """Test init_from_zip with empty name."""
        git_engine = GitEngine(temp_dir)
        
        # Create valid zip
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
            with zipfile.ZipFile(tmp.name, 'w') as zf:
                zf.writestr('test.txt', 'content')
            
            with open(tmp.name, 'rb') as f:
                repo_data = f.read()
        
        with pytest.raises(GitEngineError) as exc_info:
            git_engine.init_from_zip(repo_data, "")
        
        assert "cannot be empty" in str(exc_info.value)

    def test_init_from_git_invalid_url(self, temp_dir, mocker):
        """Test init_from_git with invalid Git URL."""
        git_engine = GitEngine(temp_dir)

        mocker.patch('git.Repo.clone_from', side_effect=GitCommandError('clone', 'fatal: repository not found'))

        with pytest.raises(GitEngineError, match="Failed to initialize from Git"):
            git_engine.init_from_git("https://invalid-url-that-does-not-exist.com/repo.git")

    def test_init_from_git_empty_url(self, temp_dir):
        """Test init_from_git with empty URL."""
        git_engine = GitEngine(temp_dir)
        
        with pytest.raises(GitEngineError) as exc_info:
            git_engine.init_from_git("")
        
        assert "cannot be empty" in str(exc_info.value)

    def test_create_workpad_long_title(self, temp_dir, simple_repo_zip):
        """Test create_workpad with a very long title."""
        git_engine = GitEngine(temp_dir)
        repo_id = git_engine.init_from_zip(simple_repo_zip, "test-repo")

        long_title = "a" * 150
        with pytest.raises(GitEngineError, match="Workpad title too long"):
            git_engine.create_workpad(repo_id, long_title)

    def test_create_workpad_repository_error(self, temp_dir, simple_repo_zip, mocker):
        """Test create_workpad with repository access error."""
        git_engine = GitEngine(temp_dir)
        repo_id = git_engine.init_from_zip(simple_repo_zip, "test-repo")

        mocker.patch('sologit.engines.git_engine.Repo', side_effect=GitCommandError('rev-parse', 'fatal: not a git repository'))

        with pytest.raises(GitEngineError, match="Failed to create workpad"):
            git_engine.create_workpad(repo_id, "test-pad")

    def test_apply_patch_git_error(self, temp_dir, simple_repo_zip, monkeypatch):
        """Test apply_patch with Git command error."""
        git_engine = GitEngine(temp_dir)
        repo_id = git_engine.init_from_zip(simple_repo_zip, "test-repo")
        pad_id = git_engine.create_workpad(repo_id, "test-pad")
        
        # Create an invalid patch
        invalid_patch = "This is not a valid patch"
        
        with pytest.raises(GitEngineError) as exc_info:
            git_engine.apply_patch(pad_id, invalid_patch)
        
        assert "Failed to apply patch" in str(exc_info.value)

    def test_promote_workpad_error(self, temp_dir, simple_repo_zip, mocker):
        """Test promote_workpad with Git error."""
        git_engine = GitEngine(temp_dir)
        repo_id = git_engine.init_from_zip(simple_repo_zip, "test-repo")
        pad_id = git_engine.create_workpad(repo_id, "test-pad")

        patch = """diff --git a/test.txt b/test.txt
new file mode 100644
index 0000000..ce01362
--- /dev/null
+++ b/test.txt
@@ -0,0 +1 @@
+hello
"""
        git_engine.apply_patch(pad_id, patch)

        mock_repo = mocker.Mock(spec=Repo)
        mock_repo.git.merge.side_effect = GitCommandError('merge', 'fatal: refusing to merge unrelated histories')
        mocker.patch('sologit.engines.git_engine.Repo', return_value=mock_repo)

        with pytest.raises(CannotPromoteError, match="not fast-forward-able"):
            git_engine.promote_workpad(pad_id)

    def test_revert_last_commit_error(self, temp_dir, simple_repo_zip, mocker):
        """Test revert_last_commit with Git error."""
        git_engine = GitEngine(temp_dir)
        repo_id = git_engine.init_from_zip(simple_repo_zip, "test-repo")

        mocker.patch('sologit.engines.git_engine.Repo', side_effect=GitCommandError('reset', 'fatal: Could not reset'))

        with pytest.raises(GitEngineError, match="Failed to revert commit"):
            git_engine.revert_last_commit(repo_id)

    def test_get_diff_error(self, temp_dir, simple_repo_zip, mocker):
        """Test get_diff with Git error."""
        git_engine = GitEngine(temp_dir)
        repo_id = git_engine.init_from_zip(simple_repo_zip, "test-repo")
        pad_id = git_engine.create_workpad(repo_id, "test-pad")

        mock_repo = mocker.Mock(spec=Repo)
        mock_repo.git.diff.side_effect = GitCommandError('diff', 'fatal: Could not diff')
        mocker.patch('sologit.engines.git_engine.Repo', return_value=mock_repo)
        
        with pytest.raises(GitEngineError, match="Failed to get diff"):
            git_engine.get_diff(pad_id)

    def test_get_history_error(self, temp_dir, simple_repo_zip, monkeypatch):
        """Test get_history with Git error."""
        git_engine = GitEngine(temp_dir)
        repo_id = git_engine.init_from_zip(simple_repo_zip, "test-repo")
        
        # Mock iter_commits to raise an exception
        from git import Repo as GitRepo
        original_iter_commits = GitRepo.iter_commits
        
        def mock_iter_commits(self, *args, **kwargs):
            raise Exception("Failed to get commits")
        
        monkeypatch.setattr(GitRepo, "iter_commits", mock_iter_commits)
        
        with pytest.raises(GitEngineError) as exc_info:
            git_engine.get_history(repo_id)
        
        assert "Failed to get history" in str(exc_info.value)

    def test_get_status_error(self, temp_dir, simple_repo_zip, monkeypatch):
        """Test get_status with Git error."""
        git_engine = GitEngine(temp_dir)
        repo_id = git_engine.init_from_zip(simple_repo_zip, "test-repo")
        
        # Mock index.diff to raise an exception
        from git import Repo as GitRepo
        from git.index import IndexFile
        original_diff = IndexFile.diff
        
        def mock_diff(self, *args, **kwargs):
            raise Exception("Diff failed")
        
        monkeypatch.setattr(IndexFile, "diff", mock_diff)
        
        with pytest.raises(GitEngineError) as exc_info:
            git_engine.get_status(repo_id)
        
        assert "Failed to get status" in str(exc_info.value)

    def test_get_file_content_error(self, temp_dir, simple_repo_zip):
        """Test get_file_content with non-existent file."""
        git_engine = GitEngine(temp_dir)
        repo_id = git_engine.init_from_zip(simple_repo_zip, "test-repo")
        
        with pytest.raises(GitEngineError) as exc_info:
            git_engine.get_file_content(repo_id, "nonexistent.txt")
        
        assert "Failed to get file content" in str(exc_info.value)

    def test_rollback_to_checkpoint_error(self, temp_dir, simple_repo_zip, mocker):
        """Test rollback_to_checkpoint with Git error."""
        git_engine = GitEngine(temp_dir)
        repo_id = git_engine.init_from_zip(simple_repo_zip, "test-repo")
        pad_id = git_engine.create_workpad(repo_id, "test-pad")
        
        patch = """diff --git a/test.txt b/test.txt
new file mode 100644
index 0000000..ce01362
--- /dev/null
+++ b/test.txt
@@ -0,0 +1 @@
+hello
"""
        git_engine.apply_patch(pad_id, patch)
        
        mocker.patch('sologit.engines.git_engine.Repo', side_effect=GitCommandError('reset', 'fatal: Could not reset'))
        
        workpad = git_engine.get_workpad(pad_id)
        checkpoint_id = workpad.checkpoints[0]
        
        with pytest.raises(GitEngineError, match="Failed to rollback to checkpoint"):
            git_engine.rollback_to_checkpoint(pad_id, checkpoint_id)

    def test_delete_workpad_error(self, temp_dir, simple_repo_zip, monkeypatch):
        """Test delete_workpad with Git error."""
        git_engine = GitEngine(temp_dir)
        repo_id = git_engine.init_from_zip(simple_repo_zip, "test-repo")
        pad_id = git_engine.create_workpad(repo_id, "test-pad")
        
        # Mock delete_head to raise an exception
        from git import Repo as GitRepo
        original_delete_head = GitRepo.delete_head
        
        def mock_delete_head(self, *args, **kwargs):
            raise Exception("Delete failed")
        
        monkeypatch.setattr(GitRepo, "delete_head", mock_delete_head)
        
        with pytest.raises(GitEngineError) as exc_info:
            git_engine.delete_workpad(pad_id)
        
        assert "Failed to delete workpad" in str(exc_info.value)

    def test_get_workpad_stats_error(self, temp_dir, simple_repo_zip, monkeypatch):
        """Test get_workpad_stats with Git error."""
        git_engine = GitEngine(temp_dir)
        repo_id = git_engine.init_from_zip(simple_repo_zip, "test-repo")
        pad_id = git_engine.create_workpad(repo_id, "test-pad")
        
        # Mock commit.diff to raise an exception
        from git import Repo as GitRepo
        from git.objects import Commit
        original_diff = Commit.diff
        
        def mock_diff(self, *args, **kwargs):
            raise Exception("Diff failed")
        
        monkeypatch.setattr(Commit, "diff", mock_diff)
        
        with pytest.raises(GitEngineError) as exc_info:
            git_engine.get_workpad_stats(pad_id)
        
        assert "Failed to get workpad stats" in str(exc_info.value)

    def test_list_branches_error(self, temp_dir, simple_repo_zip, monkeypatch):
        """Test list_branches with Git error."""
        git_engine = GitEngine(temp_dir)
        repo_id = git_engine.init_from_zip(simple_repo_zip, "test-repo")
        
        # Mock branches property to raise an exception
        from git import Repo as GitRepo
        
        def mock_branches_property(self):
            raise Exception("Failed to list branches")
        
        monkeypatch.setattr(GitRepo, "branches", property(mock_branches_property))
        
        with pytest.raises(GitEngineError) as exc_info:
            git_engine.list_branches(repo_id)
        
        assert "Failed to list branches" in str(exc_info.value)

    def test_list_tags_error(self, temp_dir, simple_repo_zip, monkeypatch):
        """Test list_tags with Git error."""
        git_engine = GitEngine(temp_dir)
        repo_id = git_engine.init_from_zip(simple_repo_zip, "test-repo")
        
        # Mock tags property to raise an exception
        from git import Repo as GitRepo
        
        def mock_tags_property(self):
            raise Exception("Failed to list tags")
        
        monkeypatch.setattr(GitRepo, "tags", property(mock_tags_property))
        
        with pytest.raises(GitEngineError) as exc_info:
            git_engine.list_tags(repo_id)
        
        assert "Failed to list tags" in str(exc_info.value)

    def test_create_commit_error(self, temp_dir, simple_repo_zip, monkeypatch):
        """Test create_commit with Git error."""
        git_engine = GitEngine(temp_dir)
        repo_id = git_engine.init_from_zip(simple_repo_zip, "test-repo")
        pad_id = git_engine.create_workpad(repo_id, "test-pad")
        
        # Mock index.commit to raise an exception
        from git.index import IndexFile
        original_commit = IndexFile.commit
        
        def mock_commit(self, *args, **kwargs):
            raise Exception("Commit failed")
        
        monkeypatch.setattr(IndexFile, "commit", mock_commit)
        
        with pytest.raises(GitEngineError) as exc_info:
            git_engine.create_commit(repo_id, pad_id, "test commit")
        
        assert "Failed to create commit" in str(exc_info.value)

    def test_get_commits_ahead_behind_error(self, temp_dir, simple_repo_zip, monkeypatch):
        """Test get_commits_ahead_behind with Git error."""
        git_engine = GitEngine(temp_dir)
        repo_id = git_engine.init_from_zip(simple_repo_zip, "test-repo")
        pad_id = git_engine.create_workpad(repo_id, "test-pad")
        
        # Mock iter_commits to raise an exception
        from git import Repo as GitRepo
        original_iter_commits = GitRepo.iter_commits
        
        def mock_iter_commits(self, *args, **kwargs):
            raise Exception("Failed to get commits")
        
        monkeypatch.setattr(GitRepo, "iter_commits", mock_iter_commits)
        
        with pytest.raises(GitEngineError) as exc_info:
            git_engine.get_commits_ahead_behind(pad_id)
        
        assert "Failed to get commits ahead/behind" in str(exc_info.value)

    def test_list_files_error(self, temp_dir, simple_repo_zip, monkeypatch):
        """Test list_files with Git error."""
        git_engine = GitEngine(temp_dir)
        repo_id = git_engine.init_from_zip(simple_repo_zip, "test-repo")
        
        # Mock commit.tree.traverse to raise an exception
        from git.objects import Tree
        original_traverse = Tree.traverse
        
        def mock_traverse(self, *args, **kwargs):
            raise Exception("Failed to traverse tree")
        
        monkeypatch.setattr(Tree, "traverse", mock_traverse)
        
        with pytest.raises(GitEngineError) as exc_info:
            git_engine.list_files(repo_id)
        
        assert "Failed to list files" in str(exc_info.value)

    def test_switch_workpad_error(self, temp_dir, simple_repo_zip, monkeypatch):
        """Test switch_workpad with Git error."""
        git_engine = GitEngine(temp_dir)
        repo_id = git_engine.init_from_zip(simple_repo_zip, "test-repo")
        pad_id = git_engine.create_workpad(repo_id, "test-pad")
        
        # Mock checkout to raise an exception
        from git.refs import Head
        original_checkout = Head.checkout
        
        def mock_checkout(self, *args, **kwargs):
            raise Exception("Checkout failed")
        
        monkeypatch.setattr(Head, "checkout", mock_checkout)
        
        with pytest.raises(GitEngineError) as exc_info:
            git_engine.switch_workpad(pad_id)
        
        assert "Failed to switch workpad" in str(exc_info.value)

    def test_compare_workpads_error(self, temp_dir, simple_repo_zip, mocker):
        """Test compare_workpads with Git error."""
        git_engine = GitEngine(temp_dir)
        repo_id = git_engine.init_from_zip(simple_repo_zip, "test-repo")
        pad_id_1 = git_engine.create_workpad(repo_id, "test-pad-1")
        pad_id_2 = git_engine.create_workpad(repo_id, "test-pad-2")

        mock_repo = mocker.Mock(spec=Repo)
        mock_repo.git.diff.side_effect = GitCommandError('diff', 'fatal: Could not diff')
        mocker.patch('sologit.engines.git_engine.Repo', return_value=mock_repo)

        with pytest.raises(GitEngineError, match="Failed to compare workpads"):
            git_engine.compare_workpads(pad_id_1, pad_id_2)

    def test_get_workpad_merge_preview_error(self, temp_dir, simple_repo_zip, monkeypatch):
        """Test get_workpad_merge_preview with Git error."""
        git_engine = GitEngine(temp_dir)
        repo_id = git_engine.init_from_zip(simple_repo_zip, "test-repo")
        pad_id = git_engine.create_workpad(repo_id, "test-pad")
        
        # Mock commit.diff to raise an exception
        from git.objects import Commit
        original_diff = Commit.diff
        
        def mock_diff(self, *args, **kwargs):
            raise Exception("Diff failed")
        
        monkeypatch.setattr(Commit, "diff", mock_diff)
        
        with pytest.raises(GitEngineError) as exc_info:
            git_engine.get_workpad_merge_preview(pad_id)
        
        assert "Failed to generate merge preview" in str(exc_info.value)


class TestGitEngineEdgeCases:
    """Test edge cases and less common code paths."""

    def test_get_active_workpad_on_trunk(self, temp_dir, simple_repo_zip):
        """Test get_active_workpad when on trunk branch."""
        git_engine = GitEngine(temp_dir)
        repo_id = git_engine.init_from_zip(simple_repo_zip, "test-repo")
        
        # Should return None when on trunk
        active = git_engine.get_active_workpad(repo_id)
        assert active is None

    def test_get_active_workpad_error(self, temp_dir, simple_repo_zip, monkeypatch):
        """Test get_active_workpad with Git error."""
        git_engine = GitEngine(temp_dir)
        repo_id = git_engine.init_from_zip(simple_repo_zip, "test-repo")
        
        # Mock active_branch to raise an exception
        from git import Repo as GitRepo
        
        def mock_active_branch_property(self):
            raise Exception("Failed to get active branch")
        
        monkeypatch.setattr(GitRepo, "active_branch", property(mock_active_branch_property))
        
        # Should return None on error
        active = git_engine.get_active_workpad(repo_id)
        assert active is None

    def test_can_promote_false(self, temp_dir, simple_repo_zip):
        """Test can_promote returns False when trunk has diverged."""
        git_engine = GitEngine(temp_dir)
        repo_id = git_engine.init_from_zip(simple_repo_zip, "test-repo")
        pad_id = git_engine.create_workpad(repo_id, "test-pad")
        
        # Apply patch to workpad
        patch = """diff --git a/test.txt b/test.txt
new file mode 100644
index 0000000..ce01362
--- /dev/null
+++ b/test.txt
@@ -0,0 +1 @@
+hello
"""
        git_engine.apply_patch(pad_id, patch)
        
        # Make a change on trunk directly (simulate divergence)
        from git import Repo as GitRepo
        repository = git_engine.get_repo(repo_id)
        repo = GitRepo(repository.path)
        trunk = getattr(repo.heads, repository.trunk_branch)
        trunk.checkout()
        
        test_file = repository.path / "trunk_change.txt"
        test_file.write_text("trunk change")
        repo.index.add(['trunk_change.txt'])
        repo.index.commit("Change on trunk")
        
        # Now can_promote should return False
        can_promote = git_engine.can_promote(pad_id)
        assert can_promote == False

    def test_can_promote_error_returns_false(self, temp_dir, simple_repo_zip, monkeypatch):
        """Test can_promote returns False on error."""
        git_engine = GitEngine(temp_dir)
        repo_id = git_engine.init_from_zip(simple_repo_zip, "test-repo")
        pad_id = git_engine.create_workpad(repo_id, "test-pad")
        
        # Mock merge_base to raise an exception
        from git import Repo as GitRepo
        original_merge_base = GitRepo.merge_base
        
        def mock_merge_base(self, *args, **kwargs):
            raise Exception("merge_base failed")
        
        monkeypatch.setattr(GitRepo, "merge_base", mock_merge_base)
        
        # Should return False on error
        can_promote = git_engine.can_promote(pad_id)
        assert can_promote == False
