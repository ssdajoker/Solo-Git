
"""
Custom assertion helpers for Solo-Git tests.

Provides domain-specific assertions that make tests more readable and provide
better error messages.
"""

import subprocess
from pathlib import Path
from typing import Any, Dict, Optional


def assert_repo_exists(git_engine, repo_id: str, message: Optional[str] = None):
    """
    Assert that a repository exists.
    
    Args:
        git_engine: GitEngine instance
        repo_id: Repository ID to check
        message: Optional custom error message
    
    Raises:
        AssertionError: If repository doesn't exist
    """
    try:
        repo = git_engine.get_repo(repo_id)
        assert repo is not None, message or f"Repository {repo_id} should exist"
    except Exception as e:
        raise AssertionError(message or f"Repository {repo_id} not found: {e}")


def assert_workpad_exists(git_engine, workpad_id: str, message: Optional[str] = None):
    """
    Assert that a workpad exists.
    
    Args:
        git_engine: GitEngine instance
        workpad_id: Workpad ID to check
        message: Optional custom error message
    
    Raises:
        AssertionError: If workpad doesn't exist
    """
    try:
        workpad = git_engine.get_workpad(workpad_id)
        assert workpad is not None, message or f"Workpad {workpad_id} should exist"
    except Exception as e:
        raise AssertionError(message or f"Workpad {workpad_id} not found: {e}")


def assert_git_clean(repo_path: Path, message: Optional[str] = None):
    """
    Assert that git working directory is clean (no uncommitted changes).
    
    Args:
        repo_path: Path to git repository
        message: Optional custom error message
    
    Raises:
        AssertionError: If working directory is not clean
    """
    result = subprocess.run(
        ['git', 'status', '--porcelain'],
        cwd=repo_path,
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"Git status command failed: {result.stderr}"
    assert not result.stdout.strip(), message or f"Git working directory should be clean, but has changes:\n{result.stdout}"


def assert_git_has_changes(repo_path: Path, message: Optional[str] = None):
    """
    Assert that git working directory has uncommitted changes.
    
    Args:
        repo_path: Path to git repository
        message: Optional custom error message
    
    Raises:
        AssertionError: If working directory is clean
    """
    result = subprocess.run(
        ['git', 'status', '--porcelain'],
        cwd=repo_path,
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"Git status command failed: {result.stderr}"
    assert result.stdout.strip(), message or "Git working directory should have changes, but is clean"


def assert_branch_exists(repo_path: Path, branch_name: str, message: Optional[str] = None):
    """
    Assert that a git branch exists.
    
    Args:
        repo_path: Path to git repository
        branch_name: Name of branch to check
        message: Optional custom error message
    
    Raises:
        AssertionError: If branch doesn't exist
    """
    result = subprocess.run(
        ['git', 'rev-parse', '--verify', branch_name],
        cwd=repo_path,
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, message or f"Branch '{branch_name}' should exist"


def assert_test_results_valid(test_results: Dict[str, Any], message: Optional[str] = None):
    """
    Assert that test results dictionary has required fields and valid values.
    
    Args:
        test_results: Test results dictionary
        message: Optional custom error message
    
    Raises:
        AssertionError: If test results are invalid
    """
    required_fields = ['passed', 'failed', 'total', 'duration']
    
    for field in required_fields:
        assert field in test_results, message or f"Test results missing required field: {field}"
    
    assert test_results['passed'] >= 0, "Passed tests count must be non-negative"
    assert test_results['failed'] >= 0, "Failed tests count must be non-negative"
    assert test_results['total'] >= 0, "Total tests count must be non-negative"
    assert test_results['duration'] >= 0, "Duration must be non-negative"
    
    # Logical consistency
    assert test_results['passed'] + test_results['failed'] <= test_results['total'], \
        "Passed + Failed should not exceed Total"


def assert_file_contains(file_path: Path, content: str, message: Optional[str] = None):
    """
    Assert that a file contains specific content.
    
    Args:
        file_path: Path to file
        content: Content that should be present
        message: Optional custom error message
    
    Raises:
        AssertionError: If file doesn't contain content
    """
    assert file_path.exists(), f"File {file_path} should exist"
    
    file_content = file_path.read_text()
    assert content in file_content, message or f"File {file_path} should contain '{content}'"


def assert_file_not_contains(file_path: Path, content: str, message: Optional[str] = None):
    """
    Assert that a file does not contain specific content.
    
    Args:
        file_path: Path to file
        content: Content that should not be present
        message: Optional custom error message
    
    Raises:
        AssertionError: If file contains content
    """
    assert file_path.exists(), f"File {file_path} should exist"
    
    file_content = file_path.read_text()
    assert content not in file_content, message or f"File {file_path} should not contain '{content}'"


def assert_json_structure(data: Dict, expected_keys: list, message: Optional[str] = None):
    """
    Assert that a JSON/dict has expected structure.
    
    Args:
        data: Dictionary to check
        expected_keys: List of keys that should be present
        message: Optional custom error message
    
    Raises:
        AssertionError: If structure doesn't match
    """
    missing_keys = [key for key in expected_keys if key not in data]
    assert not missing_keys, message or f"JSON missing expected keys: {missing_keys}"
