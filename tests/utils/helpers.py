
"""
Helper functions for tests.

Provides utility functions that make tests easier to write and maintain.
"""

import time
import subprocess
from pathlib import Path
from typing import Callable, Any, Optional, List, Dict
from contextlib import contextmanager


def wait_for_condition(
    condition: Callable[[], bool],
    timeout: float = 5.0,
    interval: float = 0.1,
    error_message: str = "Condition not met within timeout"
) -> bool:
    """
    Wait for a condition to become true.
    
    Args:
        condition: Callable that returns bool
        timeout: Maximum time to wait in seconds
        interval: Time between checks in seconds
        error_message: Error message if timeout
    
    Returns:
        True if condition met
    
    Raises:
        TimeoutError: If condition not met within timeout
    """
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if condition():
            return True
        time.sleep(interval)
    
    raise TimeoutError(error_message)


def capture_cli_output(cli_runner, cli_command, args: List[str]) -> Dict[str, Any]:
    """
    Capture CLI command output.
    
    Args:
        cli_runner: Click CLI runner
        cli_command: CLI command function
        args: List of command arguments
    
    Returns:
        Dictionary with exit_code, output, and error
    """
    result = cli_runner.invoke(cli_command, args)
    
    return {
        'exit_code': result.exit_code,
        'output': result.output,
        'exception': result.exception,
        'success': result.exit_code == 0
    }


def mock_ai_response(prompt: str, style: str = "plan") -> str:
    """
    Generate a mock AI response based on prompt.
    
    Args:
        prompt: Input prompt
        style: Response style ('plan', 'code', 'review')
    
    Returns:
        Mock response string
    """
    if style == "plan":
        return """
1. Analyze the requirements
2. Design the solution
3. Implement the code
4. Write tests
5. Run tests and verify
"""
    elif style == "code":
        return """```python
def new_function():
    \"\"\"New function implementation.\"\"\"
    return True
```"""
    elif style == "review":
        return """
Code Review:
✓ Implementation looks good
✓ Tests are comprehensive
⚠ Consider adding error handling
⚠ Add docstrings for public functions
"""
    else:
        return "Mock AI response"


@contextmanager
def temporary_file(content: str = "", suffix: str = ".txt"):
    """
    Context manager for temporary file.
    
    Args:
        content: Initial file content
        suffix: File suffix
    
    Yields:
        Path to temporary file
    """
    import tempfile
    import os
    
    fd, path = tempfile.mkstemp(suffix=suffix)
    temp_path = Path(path)
    
    try:
        if content:
            temp_path.write_text(content)
        yield temp_path
    finally:
        os.close(fd)
        if temp_path.exists():
            temp_path.unlink()


@contextmanager
def change_directory(path: Path):
    """
    Context manager to temporarily change directory.
    
    Args:
        path: Directory to change to
    
    Yields:
        Path object
    """
    import os
    
    original = Path.cwd()
    try:
        os.chdir(path)
        yield path
    finally:
        os.chdir(original)


def run_git_command(repo_path: Path, *args: str) -> str:
    """
    Run a git command and return output.
    
    Args:
        repo_path: Path to git repository
        *args: Git command arguments
    
    Returns:
        Command output
    
    Raises:
        RuntimeError: If command fails
    """
    result = subprocess.run(
        ['git'] + list(args),
        cwd=repo_path,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        raise RuntimeError(f"Git command failed: {result.stderr}")
    
    return result.stdout.strip()


def get_git_commits(repo_path: Path, count: int = 10) -> List[Dict[str, str]]:
    """
    Get recent git commits.
    
    Args:
        repo_path: Path to git repository
        count: Number of commits to retrieve
    
    Returns:
        List of commit dictionaries
    """
    output = run_git_command(
        repo_path,
        'log',
        f'-{count}',
        '--format=%H|%an|%ae|%at|%s'
    )
    
    commits = []
    for line in output.split('\n'):
        if not line:
            continue
        
        parts = line.split('|')
        if len(parts) == 5:
            commits.append({
                'sha': parts[0],
                'author': parts[1],
                'email': parts[2],
                'timestamp': parts[3],
                'message': parts[4]
            })
    
    return commits


def get_git_diff(repo_path: Path, ref1: str = 'HEAD~1', ref2: str = 'HEAD') -> str:
    """
    Get git diff between two refs.
    
    Args:
        repo_path: Path to git repository
        ref1: First reference
        ref2: Second reference
    
    Returns:
        Diff output
    """
    return run_git_command(repo_path, 'diff', ref1, ref2)


def count_lines_of_code(directory: Path, extensions: List[str] = None) -> int:
    """
    Count lines of code in directory.
    
    Args:
        directory: Directory to scan
        extensions: List of file extensions to include (e.g., ['.py', '.js'])
    
    Returns:
        Total line count
    """
    if extensions is None:
        extensions = ['.py']
    
    total_lines = 0
    
    for ext in extensions:
        for file_path in directory.rglob(f'*{ext}'):
            if '__pycache__' in str(file_path) or '.git' in str(file_path):
                continue
            
            try:
                with open(file_path, 'r') as f:
                    total_lines += sum(1 for _ in f)
            except:
                pass
    
    return total_lines


def assert_eventually(
    assertion: Callable[[], None],
    timeout: float = 5.0,
    interval: float = 0.1
) -> None:
    """
    Assert that a condition becomes true eventually.
    
    Args:
        assertion: Assertion function (raises AssertionError if fails)
        timeout: Maximum time to wait
        interval: Time between checks
    
    Raises:
        AssertionError: If assertion never passes
    """
    start_time = time.time()
    last_error = None
    
    while time.time() - start_time < timeout:
        try:
            assertion()
            return
        except AssertionError as e:
            last_error = e
            time.sleep(interval)
    
    raise AssertionError(f"Assertion failed after {timeout}s: {last_error}")


def create_file_tree(base_path: Path, structure: Dict[str, Any]) -> None:
    """
    Create a file tree from a dictionary structure.
    
    Args:
        base_path: Base directory path
        structure: Dictionary where keys are paths and values are:
                  - str: file content
                  - dict: subdirectory structure
                  - None: empty directory
    
    Example:
        create_file_tree(Path('/tmp/test'), {
            'src': {
                'main.py': 'print("hello")',
                'utils': {
                    'helpers.py': 'def help(): pass'
                }
            },
            'tests': None,
            'README.md': '# Project'
        })
    """
    base_path.mkdir(parents=True, exist_ok=True)
    
    for name, content in structure.items():
        path = base_path / name
        
        if isinstance(content, dict):
            # It's a directory with contents
            create_file_tree(path, content)
        elif isinstance(content, str):
            # It's a file with content
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        elif content is None:
            # It's an empty directory
            path.mkdir(parents=True, exist_ok=True)


def sanitize_output(output: str) -> str:
    """
    Sanitize CLI output for testing (remove ANSI codes, normalize whitespace).
    
    Args:
        output: Raw CLI output
    
    Returns:
        Sanitized output
    """
    import re
    
    # Remove ANSI escape codes
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    output = ansi_escape.sub('', output)
    
    # Normalize whitespace
    output = '\n'.join(line.rstrip() for line in output.split('\n'))
    
    return output.strip()
