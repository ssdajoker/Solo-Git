import os
import shutil
import pytest
from click.testing import CliRunner
from sologit.cli.main import cli
from sologit.core.repository import Repository
from sologit.state.manager import StateManager

@pytest.fixture
def runner(tmp_path_factory):
    state_path = tmp_path_factory.mktemp("sologit_state")
    runner = CliRunner(env={"SOLOGIT_STATE_PATH": str(state_path)})
    return runner

@pytest.fixture
def test_repo_path(tmp_path):
    return tmp_path / "test_repo"

@pytest.fixture
def setup_repo(runner, test_repo_path):
    # Create a directory for the repo
    os.makedirs(test_repo_path, exist_ok=True)

    # Set up sologit
    result = runner.invoke(cli, ["repo", "init", "--path", str(test_repo_path), "--name", "test-repo", "--empty"])
    assert result.exit_code == 0, f"Failed to init repo: {result.output}"

    yield test_repo_path

    # Teardown: clean up the created directory
    shutil.rmtree(test_repo_path)

def test_happy_path_workflow(runner, setup_repo):
    repo_path = setup_repo
    state_manager = StateManager()

    # 1. Find the created repository in the state
    repos = state_manager.list_repositories()
    assert len(repos) == 1, "Expected one repository to be created"
    repo_state = repos[0]
    repo_id = repo_state.repo_id

    # 2. Create a workpad
    result = runner.invoke(cli, ["pad", "create", "My first workpad", "--repo", repo_id])
    assert result.exit_code == 0, f"Failed to create workpad: {result.output}"

    # 3. Verify state
    repo_state_after_create = state_manager.get_repository(repo_id)
    assert repo_state_after_create is not None, "Repository state not found"

    pads = state_manager.list_workpads(repo_id)
    assert len(pads) == 1, "Workpad was not created"

    workpad = pads[0]
    assert workpad.title == "My first workpad", "Workpad title is incorrect"
    assert workpad.status == "draft", "Workpad status should be 'draft'"
