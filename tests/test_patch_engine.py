
"""
Tests for Patch Engine.
"""

import pytest
import tempfile
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO

from sologit.engines.git_engine import GitEngine
from sologit.engines.patch_engine import PatchEngine, PatchConflictError


@pytest.fixture
def engines():
    """Create GitEngine and PatchEngine with temporary data directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        git_engine = GitEngine(data_dir=Path(tmpdir))
        patch_engine = PatchEngine(git_engine)
        yield git_engine, patch_engine


@pytest.fixture
def sample_zip():
    """Create a sample zip file."""
    buffer = BytesIO()
    with ZipFile(buffer, 'w') as zf:
        zf.writestr('README.md', '# Test Project\n')
        zf.writestr('main.py', 'print("Hello, World!")\n')
    buffer.seek(0)
    return buffer.read()


def test_parse_affected_files(engines):
    """Test parsing affected files from patch."""
    _, patch_engine = engines
    
    patch = """
--- a/file1.py
+++ b/file1.py
@@ -1,3 +1,4 @@
+# New line
 import os
 
--- a/file2.py
+++ b/file2.py
@@ -1,2 +1,2 @@
-old line
+new line
"""
    
    files = patch_engine._parse_affected_files(patch)
    assert set(files) == {'file1.py', 'file2.py'}


def test_patch_validation_no_conflicts(engines, sample_zip):
    """Test patch validation with no conflicts."""
    git_engine, patch_engine = engines
    
    # Setup
    repo_id = git_engine.init_from_zip(sample_zip, "Test Repo")
    pad_id = git_engine.create_workpad(repo_id, "Feature")
    
    # Create a simple patch
    patch = """--- a/new_file.txt
+++ b/new_file.txt
@@ -0,0 +1 @@
+Hello from patch!
"""
    
    # Should validate successfully
    assert patch_engine.validate_patch(pad_id, patch) is True
