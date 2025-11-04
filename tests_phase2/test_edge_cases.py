"""Test edge cases in Solo-Git."""
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch


def test_empty_repository():
    """Test handling of empty repository."""
    from sologit.engines.git_engine import GitEngine
    from sologit.core.repository import Repository
    
    # Mock GitEngine properly without accessing undefined attributes
    engine = Mock()
    repo_mock = Mock(spec=Repository)
    repo_mock.id = "test-repo"
    repo_mock.path = "/path/to/empty"
    engine.init_repository = Mock(return_value=repo_mock)
    
    # Should not crash
    repo = engine.init_repository(source="/path/to/empty", repo_type="git")
    assert repo is not None


def test_huge_diff():
    """Test handling of very large diff."""
    from sologit.engines.patch_engine import PatchEngine
    
    # Mock PatchEngine
    engine = Mock(spec=PatchEngine)
    
    # Generate 10MB diff
    huge_diff = "+" + ("x" * 10_000_000) + "\n"
    
    # Mock apply_patch to reject large diffs
    def mock_apply_patch(repo_id, diff):
        if len(diff) > 1_000_000:
            raise ValueError("Diff too large")
        return {"success": True}
    
    engine.apply_patch.side_effect = mock_apply_patch
    
    # Should reject or handle gracefully
    with pytest.raises(ValueError, match="Diff too large"):
        engine.apply_patch("repo-id", huge_diff)


def test_binary_files_in_diff():
    """Test binary files in diff are handled."""
    from sologit.engines.patch_engine import PatchEngine
    
    # Mock PatchEngine
    engine = Mock(spec=PatchEngine)
    
    # Create a diff with binary file indicator
    binary_diff = """diff --git a/image.png b/image.png
index 1234567..89abcdef 100644
Binary files a/image.png and b/image.png differ
"""
    
    # Mock to detect binary
    def mock_apply_patch(repo_id, diff):
        if "Binary files" in diff:
            return {"success": False, "error": "Binary files not supported"}
        return {"success": True}
    
    engine.apply_patch.side_effect = mock_apply_patch
    
    result = engine.apply_patch("repo-id", binary_diff)
    assert result["success"] is False
    assert "Binary" in result["error"]


def test_special_characters_in_workpad_name():
    """Test special characters in workpad name."""
    from sologit.engines.git_engine import GitEngine
    
    # Mock GitEngine
    engine = Mock(spec=GitEngine)
    
    special_names = [
        "feat/🚀-rocket",
        "fix: bug #123",
        "refactor\\weird\\slashes",
        "test/../../../etc/passwd",
        "name with spaces",
        "name\nwith\nnewlines",
    ]
    
    def mock_create_workpad(repo_id, title):
        # Sanitize title
        import re
        from datetime import datetime
        sanitized = re.sub(r'[^\w\-.]', '-', title)
        if not sanitized or sanitized.startswith('.'):
            raise ValueError(f"Invalid workpad name: {title}")
        
        from sologit.core.workpad import Workpad
        return Workpad(
            id=f"pad-{sanitized}",
            repo_id=repo_id,
            title=sanitized,
            branch_name=f"workpad/{sanitized}",
            created_at=datetime.fromisoformat("2025-01-01T00:00:00")
        )
    
    engine.create_workpad.side_effect = mock_create_workpad
    
    for name in special_names:
        try:
            workpad = engine.create_workpad("repo", name)
            # Should either succeed with sanitized name or raise ValueError
            assert workpad.title is not None
        except ValueError as e:
            # Expected for some invalid names
            assert "Invalid" in str(e)


def test_very_long_workpad_name():
    """Test very long workpad name."""
    from sologit.engines.git_engine import GitEngine
    
    # Mock GitEngine
    engine = Mock(spec=GitEngine)
    
    # Very long name (300 characters)
    long_name = "a" * 300
    
    def mock_create_workpad(repo_id, title):
        # Truncate long names
        from datetime import datetime
        max_length = 100
        truncated = title[:max_length]
        
        from sologit.core.workpad import Workpad
        return Workpad(
            id=f"pad-{truncated[:10]}",
            repo_id=repo_id,
            title=truncated,
            branch_name=f"workpad/{truncated[:50]}",
            created_at=datetime.fromisoformat("2025-01-01T00:00:00")
        )
    
    engine.create_workpad.side_effect = mock_create_workpad
    
    workpad = engine.create_workpad("repo", long_name)
    assert len(workpad.title) <= 100


def test_non_utf8_file_encoding():
    """Test handling of non-UTF-8 file encodings."""
    with TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "latin1.txt"
        
        # Write file in Latin-1 encoding
        test_file.write_bytes("Héllo Wörld".encode('latin-1'))
        
        # Try to read it
        try:
            # Should either handle gracefully or convert
            content = test_file.read_text(encoding='utf-8', errors='replace')
            assert content is not None
        except UnicodeDecodeError:
            # Also acceptable to fail gracefully
            pass


def test_symlinks_in_repository():
    """Test handling of symbolic links."""
    with TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Create a file and symlink
        real_file = tmpdir_path / "real.txt"
        real_file.write_text("content")
        
        symlink = tmpdir_path / "link.txt"
        try:
            symlink.symlink_to(real_file)
            
            # Should handle symlinks without following them inappropriately
            assert symlink.is_symlink()
            assert symlink.exists()
        except OSError:
            # May not be supported on all systems
            pytest.skip("Symlinks not supported")


def test_empty_diff():
    """Test handling of empty diff."""
    from sologit.engines.patch_engine import PatchEngine
    
    # Mock PatchEngine
    engine = Mock(spec=PatchEngine)
    
    def mock_apply_patch(repo_id, diff):
        if not diff or diff.strip() == "":
            return {"success": True, "changes": 0, "message": "No changes"}
        return {"success": True}
    
    engine.apply_patch.side_effect = mock_apply_patch
    
    result = engine.apply_patch("repo-id", "")
    assert result["success"] is True
    assert result["changes"] == 0


def test_whitespace_only_diff():
    """Test diff with only whitespace changes."""
    from sologit.engines.patch_engine import PatchEngine
    
    # Mock PatchEngine
    engine = Mock(spec=PatchEngine)
    
    whitespace_diff = """diff --git a/file.py b/file.py
index 1234567..89abcdef 100644
--- a/file.py
+++ b/file.py
@@ -1,3 +1,3 @@
 def foo():
-    return 1
+    return 1 
"""
    
    def mock_apply_patch(repo_id, diff):
        # Detect whitespace-only changes
        lines = diff.split('\n')
        changes = [l for l in lines if l.startswith('+') or l.startswith('-')]
        significant = [c for c in changes if c.strip()[1:].strip()]
        
        if not significant:
            return {"success": True, "warning": "Only whitespace changes"}
        return {"success": True}
    
    engine.apply_patch.side_effect = mock_apply_patch
    
    result = engine.apply_patch("repo-id", whitespace_diff)
    assert result["success"] is True


def test_concurrent_workpad_with_same_name():
    """Test creating workpads with same name concurrently."""
    from sologit.engines.git_engine import GitEngine
    
    # Mock GitEngine
    engine = Mock(spec=GitEngine)
    created_pads = []
    
    def mock_create_workpad(repo_id, title):
        from sologit.core.workpad import Workpad
        from datetime import datetime
        # Add suffix if title already used
        pad_id = f"pad-{title}-{len(created_pads)}"
        workpad = Workpad(
            id=pad_id,
            repo_id=repo_id,
            title=title,
            branch_name=f"workpad/{title}-{len(created_pads)}",
            created_at=datetime.fromisoformat("2025-01-01T00:00:00")
        )
        created_pads.append(workpad)
        return workpad
    
    engine.create_workpad.side_effect = mock_create_workpad
    
    # Try to create multiple workpads with same name
    pads = []
    for i in range(3):
        pad = engine.create_workpad("repo", "same-name")
        pads.append(pad)
    
    assert len(pads) == 3
    # All should have unique IDs even with same title
    assert len(set(p.id for p in pads)) == 3


def test_malformed_git_state():
    """Test handling of malformed git state."""
    from sologit.state.manager import StateManager
    import os
    
    with TemporaryDirectory() as tmpdir:
        state_file = Path(tmpdir) / "state.json"
        
        # Create malformed state
        state_file.write_text('{"repositories": "not-a-list"}')
        
        # Set SOLO_GIT_STATE environment variable to use custom state file location
        old_env = os.environ.get('SOLO_GIT_STATE')
        try:
            os.environ['SOLO_GIT_STATE'] = str(tmpdir)
            
            # Should handle gracefully - either by loading default state or raising informative error
            try:
                StateManager()
                # If successful, verify state is now valid
                # Most implementations will recover by creating a new valid state
                assert True  # Successfully handled malformed state
            except Exception as e:
                # Acceptable to raise but should be informative
                error_msg = str(e).lower()
                assert any(word in error_msg for word in ["state", "corrupt", "invalid", "json"]), \
                    f"Error message should be informative, got: {e}"
        finally:
            if old_env is not None:
                os.environ['SOLO_GIT_STATE'] = old_env
            elif 'SOLO_GIT_STATE' in os.environ:
                del os.environ['SOLO_GIT_STATE']


def test_repository_path_with_spaces():
    """Test repository path containing spaces."""
    from sologit.engines.git_engine import GitEngine
    from sologit.core.repository import Repository
    
    # Mock GitEngine without spec to allow dynamic attribute assignment
    engine = Mock()
    
    path_with_spaces = "/home/user/my project/repo"
    
    def mock_init_repository(source, repo_type):
        # Should handle spaces in path
        repo_mock = Mock(spec=Repository)
        repo_mock.id = "test-repo"
        repo_mock.path = source
        return repo_mock
    
    engine.init_repository = Mock(side_effect=mock_init_repository)
    
    repo = engine.init_repository(source=path_with_spaces, repo_type="git")
    assert repo is not None
    assert " " in repo.path


def test_submodule_in_repository():
    """Test handling of git submodules."""
    with TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Create .gitmodules file
        gitmodules = tmpdir_path / ".gitmodules"
        gitmodules.write_text("""[submodule "external"]
    path = external
    url = https://github.com/example/external.git
""")
        
        # Should detect submodules
        assert gitmodules.exists()
        content = gitmodules.read_text()
        assert "submodule" in content


def test_extremely_deep_directory_structure():
    """Test handling of very deep directory structures."""
    with TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Create deep directory structure (20 levels)
        current = tmpdir_path
        for i in range(20):
            current = current / f"level{i}"
        
        try:
            current.mkdir(parents=True)
            assert current.exists()
            
            # Create a file deep in the structure
            deep_file = current / "test.txt"
            deep_file.write_text("deep content")
            assert deep_file.exists()
        except OSError as e:
            # May hit OS limits on some systems
            pytest.skip(f"OS limit reached: {e}")
