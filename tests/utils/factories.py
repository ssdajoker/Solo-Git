
"""
Factory functions for creating test objects.

Provides convenient functions to create common test objects with sensible
defaults, reducing boilerplate in tests.
"""

import tempfile
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
from typing import Dict, Optional, Any
from datetime import datetime


def create_test_repo(git_engine, name: str = "Test Repo", with_tests: bool = False) -> str:
    """
    Create a test repository.
    
    Args:
        git_engine: GitEngine instance
        name: Repository name
        with_tests: Whether to include test files
    
    Returns:
        Repository ID
    """
    if with_tests:
        zip_content = create_sample_project(with_tests=True)
    else:
        zip_content = create_sample_project(with_tests=False)
    
    return git_engine.init_from_zip(zip_content, name)


def create_test_workpad(git_engine, repo_id: str, title: str = "Test Feature") -> str:
    """
    Create a test workpad.
    
    Args:
        git_engine: GitEngine instance
        repo_id: Repository ID
        title: Workpad title
    
    Returns:
        Workpad ID
    """
    return git_engine.create_workpad(repo_id, title)


def create_test_commit(repo_path: Path, message: str = "Test commit", files: Optional[Dict[str, str]] = None):
    """
    Create a test commit in a repository.
    
    Args:
        repo_path: Path to repository
        message: Commit message
        files: Dictionary of {filename: content} to add
    
    Returns:
        Commit SHA
    """
    import subprocess
    
    # Add files if specified
    if files:
        for filename, content in files.items():
            file_path = repo_path / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
    
    # Stage all changes
    subprocess.run(['git', 'add', '.'], cwd=repo_path, check=True)
    
    # Commit
    result = subprocess.run(
        ['git', 'commit', '-m', message],
        cwd=repo_path,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        raise RuntimeError(f"Failed to create commit: {result.stderr}")
    
    # Get commit SHA
    result = subprocess.run(
        ['git', 'rev-parse', 'HEAD'],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True
    )
    
    return result.stdout.strip()


def create_sample_project(
    with_tests: bool = True,
    with_config: bool = True,
    project_name: str = "test-project"
) -> bytes:
    """
    Create a sample project ZIP file.
    
    Args:
        with_tests: Include test files
        with_config: Include configuration files
        project_name: Name of the project
    
    Returns:
        ZIP file content as bytes
    """
    buffer = BytesIO()
    
    with ZipFile(buffer, 'w') as zf:
        # README
        zf.writestr('README.md', f'''# {project_name}

A test project for Solo-Git testing.

## Features

- Feature 1
- Feature 2
''')
        
        # Source files
        zf.writestr('src/__init__.py', '')
        zf.writestr('src/main.py', '''
"""Main module."""

def add(a, b):
    """Add two numbers."""
    return a + b

def multiply(a, b):
    """Multiply two numbers."""
    return a * b

def greet(name):
    """Greet someone."""
    return f"Hello, {name}!"

if __name__ == "__main__":
    print(greet("World"))
''')
        
        zf.writestr('src/utils.py', '''
"""Utility functions."""

def is_even(n):
    """Check if number is even."""
    return n % 2 == 0

def is_positive(n):
    """Check if number is positive."""
    return n > 0
''')
        
        # Test files
        if with_tests:
            zf.writestr('tests/__init__.py', '')
            zf.writestr('tests/test_main.py', '''
"""Tests for main module."""
import pytest
from src.main import add, multiply, greet

def test_add():
    assert add(1, 2) == 3
    assert add(-1, 1) == 0
    assert add(0, 0) == 0

def test_multiply():
    assert multiply(2, 3) == 6
    assert multiply(-2, 3) == -6
    assert multiply(0, 5) == 0

def test_greet():
    assert greet("Alice") == "Hello, Alice!"
    assert greet("") == "Hello, !"
''')
            
            zf.writestr('tests/test_utils.py', '''
"""Tests for utils module."""
import pytest
from src.utils import is_even, is_positive

def test_is_even():
    assert is_even(2) is True
    assert is_even(3) is False
    assert is_even(0) is True

def test_is_positive():
    assert is_positive(1) is True
    assert is_positive(-1) is False
    assert is_positive(0) is False
''')
        
        # Configuration files
        if with_config:
            zf.writestr('pytest.ini', '''[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
''')
            
            zf.writestr('requirements.txt', '''pytest>=7.0.0
pytest-cov>=4.0.0
''')
            
            zf.writestr('.gitignore', '''__pycache__/
*.pyc
.pytest_cache/
.coverage
htmlcov/
*.egg-info/
''')
    
    buffer.seek(0)
    return buffer.read()


def create_mock_test_results(
    passed: int = 10,
    failed: int = 0,
    skipped: int = 0,
    duration: float = 1.5,
    failures: Optional[list] = None
) -> Dict[str, Any]:
    """
    Create mock test results dictionary.
    
    Args:
        passed: Number of passed tests
        failed: Number of failed tests
        skipped: Number of skipped tests
        duration: Test duration in seconds
        failures: List of failure dictionaries
    
    Returns:
        Test results dictionary
    """
    total = passed + failed + skipped
    
    return {
        'passed': passed,
        'failed': failed,
        'skipped': skipped,
        'total': total,
        'duration': duration,
        'timestamp': datetime.now().isoformat(),
        'failures': failures or [],
        'success_rate': (passed / total * 100) if total > 0 else 0.0
    }


def create_mock_ai_response(
    content: str = "Mock AI response",
    model: str = "test-model",
    tokens: int = 100,
    cost: float = 0.001
) -> Dict[str, Any]:
    """
    Create mock AI API response.
    
    Args:
        content: Response content
        model: Model name
        tokens: Token count
        cost: Cost in USD
    
    Returns:
        AI response dictionary
    """
    return {
        'content': content,
        'model': model,
        'usage': {
            'prompt_tokens': tokens // 2,
            'completion_tokens': tokens // 2,
            'total_tokens': tokens
        },
        'cost_usd': cost,
        'timestamp': datetime.now().isoformat()
    }


def create_temp_git_repo(init: bool = True) -> Path:
    """
    Create a temporary git repository.
    
    Args:
        init: Whether to run git init
    
    Returns:
        Path to temporary repository
    """
    import subprocess
    
    temp_dir = Path(tempfile.mkdtemp(prefix='solo-git-test-'))
    
    if init:
        subprocess.run(['git', 'init'], cwd=temp_dir, check=True)
        subprocess.run(
            ['git', 'config', 'user.email', 'test@example.com'],
            cwd=temp_dir,
            check=True
        )
        subprocess.run(
            ['git', 'config', 'user.name', 'Test User'],
            cwd=temp_dir,
            check=True
        )
    
    return temp_dir
