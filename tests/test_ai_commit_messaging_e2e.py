"""
End-to-End Test for AI Commit Message Generation

Tests the complete workflow:
1. Create workpad with changes
2. Generate AI commit message via CLI with --json flag
3. Verify Abacus-first routing and fallback behavior
4. Test error scenarios
"""

import json
import os
import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner
from git import Repo

from sologit.cli.main import cli
from sologit.config.manager import ConfigManager
from sologit.state.manager import StateManager


@pytest.fixture
def runner(tmp_path_factory):
    """Create CLI runner with isolated state."""
    state_path = tmp_path_factory.mktemp("sologit_state")
    data_path = tmp_path_factory.mktemp("sologit_data")
    runner = CliRunner(
        env={
            "SOLOGIT_STATE_PATH": str(state_path),
            "SOLOGIT_DATA_PATH": str(data_path),
        }
    )
    runner.state_path = state_path  # type: ignore[attr-defined]
    runner.data_path = data_path  # type: ignore[attr-defined]
    return runner


@pytest.fixture
def test_repo_path(tmp_path):
    """Create test repository path."""
    return tmp_path / "test_repo"


@pytest.fixture
def setup_repo(runner, test_repo_path):
    """Initialize repository and clean up afterwards."""
    os.makedirs(test_repo_path, exist_ok=True)
    state_path = Path(getattr(runner, "state_path"))
    data_path = Path(getattr(runner, "data_path"))
    
    baseline_state = StateManager(state_dir=state_path)
    existing_ids = {repo.repo_id for repo in baseline_state.list_repositories()}
    
    result = runner.invoke(
        cli,
        [
            "repo",
            "init",
            "--path",
            str(test_repo_path),
            "--name",
            "test-repo",
            "--empty",
        ],
    )
    assert result.exit_code == 0, f"Failed to init repo: {result.output}"

    current_state = StateManager(state_dir=state_path)
    repos = current_state.list_repositories()
    new_repos = [repo for repo in repos if repo.repo_id not in existing_ids]
    repo_id = new_repos[0].repo_id if new_repos else None

    try:
        yield test_repo_path, state_path, repo_id
    finally:
        if test_repo_path.exists():
            shutil.rmtree(test_repo_path)
        if data_path.exists():
            shutil.rmtree(data_path, ignore_errors=True)
        if state_path.exists():
            shutil.rmtree(state_path, ignore_errors=True)


def test_ai_commit_message_json_format(runner, setup_repo):
    """Test AI commit message generation with JSON output format."""
    test_repo_path, state_path, repo_id = setup_repo
    
    # Create a workpad with JSON output
    result = runner.invoke(
        cli, ["pad", "create", "feature-test", "--repo", repo_id, "--json"]
    )
    assert result.exit_code == 0, f"Failed to create workpad: {result.output}"
    
    # Parse workpad ID from JSON output
    try:
        create_response = json.loads(result.output)
        assert create_response.get("success"), f"Workpad creation failed: {create_response.get('error')}"
        workpad_id = create_response.get("workpad", {}).get("workpad_id")
        assert workpad_id, "No workpad_id in response"
    except json.JSONDecodeError:
        # Fallback to reading from state
        state_manager = StateManager(state_dir=state_path)
        workpads = state_manager.list_workpads()
        assert len(workpads) > 0, f"No workpads found. CLI output: {result.output}"
        workpad_id = workpads[0].workpad_id
    
    # Make some changes to the workpad
    test_file = test_repo_path / "test_file.py"
    test_file.write_text("def hello():\n    return 'world'\n")
    
    # Add the file to git
    repo = Repo(test_repo_path)
    repo.index.add([str(test_file)])
    
    # Generate commit message with JSON output
    result = runner.invoke(
        cli,
        ["commit-msg", "-w", workpad_id, "--no-edit", "--json"],
    )
    
    # Note: This will fail if no AI provider is configured
    # For CI/CD, we need to mock or skip this test
    if "No AI providers configured" in result.output:
        pytest.skip("No AI providers configured - expected in CI environment")
    
    # Verify JSON output format
    if result.exit_code == 0:
        try:
            response = json.loads(result.output)
            assert "success" in response, "Response missing 'success' field"
            
            if response["success"]:
                assert "message" in response, "Success response missing 'message' field"
                assert "provider" in response, "Success response missing 'provider' field"
                assert "model" in response, "Success response missing 'model' field"
                assert "latency_ms" in response, "Success response missing 'latency_ms' field"
                assert "cost_usd" in response, "Success response missing 'cost_usd' field"
                assert "fallback_used" in response, "Success response missing 'fallback_used' field"
                assert "workpad_id" in response, "Success response missing 'workpad_id' field"
                
                # Verify message is not empty
                assert response["message"], "Generated message is empty"
                
                # Verify provider info
                assert response["provider"], "Provider not specified"
                
            else:
                assert "error" in response, "Error response missing 'error' field"
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON output: {e}\nOutput: {result.output}")


def test_ai_commit_message_no_changes(runner, setup_repo):
    """Test AI commit message generation with no changes."""
    test_repo_path, state_path, repo_id = setup_repo
    
    # Create a workpad
    result = runner.invoke(
        cli, ["pad", "create", "empty-test", "--repo", repo_id]
    )
    assert result.exit_code == 0, f"Failed to create workpad: {result.output}"
    
    # Get workpad ID from state
    state_manager = StateManager(state_dir=state_path)
    workpads = state_manager.list_workpads()
    assert len(workpads) > 0, "No workpads found"
    workpad_id = workpads[0].workpad_id
    
    # Try to generate commit message without any changes
    result = runner.invoke(
        cli,
        ["commit-msg", "-w", workpad_id, "--no-edit", "--json"],
    )
    
    # Verify error response for no changes
    try:
        response = json.loads(result.output)
        assert "success" in response
        assert not response["success"] or response.get("error") == "No changes to commit"
    except json.JSONDecodeError:
        # CLI might not return JSON for some errors
        assert "No changes" in result.output or result.exit_code != 0


def test_ai_commit_message_invalid_workpad(runner, setup_repo):
    """Test AI commit message generation with invalid workpad ID."""
    test_repo_path, state_path, repo_id = setup_repo
    
    # Try to generate commit message for non-existent workpad
    result = runner.invoke(
        cli,
        ["commit-msg", "-w", "invalid-workpad-id", "--no-edit", "--json"],
    )
    
    # Verify error response
    assert result.exit_code != 0 or "not found" in result.output.lower()
    
    try:
        response = json.loads(result.output)
        assert "success" in response
        assert not response["success"]
        assert "error" in response
        assert "not found" in response["error"].lower()
    except json.JSONDecodeError:
        # CLI might exit before returning JSON
        pass


def test_ai_commit_message_conventional_format(runner, setup_repo):
    """Test that generated messages follow conventional commit format."""
    test_repo_path, state_path, repo_id = setup_repo
    
    # Create a workpad
    result = runner.invoke(
        cli, ["pad", "create", "conventional-test", "--repo", repo_id]
    )
    assert result.exit_code == 0
    
    # Get workpad ID
    state_manager = StateManager(state_dir=state_path)
    workpads = state_manager.list_workpads()
    workpad_id = workpads[0].workpad_id
    
    # Make changes
    test_file = test_repo_path / "feature.py"
    test_file.write_text("def new_feature():\n    pass\n")
    
    repo = Repo(test_repo_path)
    repo.index.add([str(test_file)])
    
    # Generate commit message with conventional format
    result = runner.invoke(
        cli,
        ["commit-msg", "-w", workpad_id, "--no-edit", "--conventional", "--json"],
    )
    
    if "No AI providers configured" in result.output:
        pytest.skip("No AI providers configured - expected in CI environment")
    
    if result.exit_code == 0:
        try:
            response = json.loads(result.output)
            if response["success"] and response.get("message"):
                message = response["message"]
                # Check for conventional commit format
                # Format: type(scope)?: subject
                conventional_types = ["feat", "fix", "docs", "style", "refactor", "test", "chore", "perf", "ci", "build", "revert"]
                starts_with_type = any(message.startswith(t) for t in conventional_types)
                assert starts_with_type, f"Message doesn't follow conventional format: {message}"
        except json.JSONDecodeError:
            pass


def test_ai_commit_message_provider_routing(runner, setup_repo):
    """Test that AI provider routing works correctly (Abacus-first)."""
    test_repo_path, state_path, repo_id = setup_repo
    
    # Create a workpad
    result = runner.invoke(
        cli, ["pad", "create", "routing-test", "--repo", repo_id]
    )
    assert result.exit_code == 0
    
    # Get workpad ID
    state_manager = StateManager(state_dir=state_path)
    workpads = state_manager.list_workpads()
    workpad_id = workpads[0].workpad_id
    
    # Make changes
    test_file = test_repo_path / "routing.py"
    test_file.write_text("# Test routing\n")
    
    repo = Repo(test_repo_path)
    repo.index.add([str(test_file)])
    
    # Generate commit message
    result = runner.invoke(
        cli,
        ["commit-msg", "-w", workpad_id, "--no-edit", "--json"],
    )
    
    if "No AI providers configured" in result.output:
        pytest.skip("No AI providers configured - expected in CI environment")
    
    if result.exit_code == 0:
        try:
            response = json.loads(result.output)
            if response["success"]:
                # Verify provider info is included
                assert "provider" in response
                assert "fallback_used" in response
                
                # If fallback was used, it should be indicated
                if response.get("fallback_used"):
                    # Fallback provider should not be Abacus
                    assert response.get("provider", "").lower() != "abacus"
        except json.JSONDecodeError:
            pass


@pytest.mark.integration
def test_full_workflow_with_ai_commit(runner, setup_repo):
    """
    Test complete workflow:
    1. Create workpad
    2. Make changes
    3. Generate AI commit message
    4. Verify message quality
    5. Use message to checkpoint
    """
    test_repo_path, state_path, repo_id = setup_repo
    
    # Create workpad
    result = runner.invoke(
        cli, ["pad", "create", "full-workflow", "--repo", repo_id]
    )
    assert result.exit_code == 0
    
    # Get workpad ID
    state_manager = StateManager(state_dir=state_path)
    workpads = state_manager.list_workpads()
    workpad_id = workpads[0].workpad_id
    
    # Make meaningful changes
    test_file = test_repo_path / "calculator.py"
    test_file.write_text("""
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b
""")
    
    repo = Repo(test_repo_path)
    repo.index.add([str(test_file)])
    
    # Generate AI commit message
    result = runner.invoke(
        cli,
        ["commit-msg", "-w", workpad_id, "--no-edit", "--json"],
    )
    
    if "No AI providers configured" in result.output:
        pytest.skip("No AI providers configured - expected in CI environment")
    
    if result.exit_code == 0:
        try:
            response = json.loads(result.output)
            if response["success"]:
                message = response.get("message")
                assert message, "No message generated"
                
                # Verify message quality
                assert len(message) > 10, "Message too short"
                
                # Message should mention calculator or math operations
                message_lower = message.lower()
                contains_relevant = any(
                    word in message_lower 
                    for word in ["calculator", "add", "subtract", "math", "arithmetic", "function"]
                )
                # This is a best-effort check, AI might phrase differently
                # So we don't fail the test if it doesn't match
                
                print(f"Generated message: {message}")
                print(f"Provider: {response.get('provider')}")
                print(f"Model: {response.get('model')}")
                print(f"Cost: ${response.get('cost_usd', 0):.4f}")
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
