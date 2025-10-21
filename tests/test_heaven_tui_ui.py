import asyncio
import io
import time
import zipfile
from pathlib import Path

import pytest
from git import Repo
from textual.widgets import Input

from sologit.state.git_sync import GitStateSync
from sologit.ui.heaven_tui import HeavenTUI
from sologit.orchestration.ai_orchestrator import AIOrchestrator
from sologit.ui.test_runner import TestRunner, TestResult, TestStatus


def _build_repo_zip(tmp_path: Path) -> bytes:
    repo_src = tmp_path / "repo_src"
    repo_src.mkdir()
    (repo_src / "README.md").write_text("Sample repository\n")
    tests_dir = repo_src / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_sample.py").write_text("def test_sample():\n    assert True\n")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for path in repo_src.rglob("*"):
            if path.is_file():
                zf.write(path, arcname=str(path.relative_to(repo_src)))
    return buffer.getvalue()


async def _wait_until(predicate, timeout: float = 3.0) -> None:
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        if predicate():
            return
        await asyncio.sleep(0.05)
    raise AssertionError("condition not met in time")


@pytest.mark.asyncio
async def test_heaven_tui_workpad_flow(tmp_path, monkeypatch):
    state_dir = tmp_path / "state"
    data_dir = tmp_path / "data"
    git_sync = GitStateSync(state_dir=state_dir, data_dir=data_dir)

    repo_bytes = _build_repo_zip(tmp_path)
    repo_info = git_sync.init_repo_from_zip(repo_bytes, "demo")
    repo_path = Path(repo_info["path"])
    repo_id = git_sync.get_active_context()["repo_id"]

    async def fake_run_tests(self, target="fast", output_callback=None, result_callback=None):
        result = TestResult(status=TestStatus.RUNNING)
        if result_callback:
            result_callback(result)
        await asyncio.sleep(0)
        result.status = TestStatus.PASSED
        result.passed = 1
        result.total = 1
        result.duration = 0.01
        result.output = "ok"
        if result_callback:
            result_callback(result)
        return result

    monkeypatch.setattr(TestRunner, "run_tests", fake_run_tests, raising=False)

    app = HeavenTUI(
        repo_path=str(repo_path),
        git_sync=git_sync,
        ai_orchestrator=AIOrchestrator(),
    )

    async with app.run_test() as pilot:
        await pilot.press("ctrl+n")
        await _wait_until(
            lambda: len(app.screen_stack) > 1
            and bool(app.screen_stack[-1].query("#prompt-input"))
        )
        input_widget = app.screen_stack[-1].query_one("#prompt-input", Input)
        input_widget.value = "New Feature Workpad"
        await pilot.press("enter")
        await pilot.pause(0.1)

        await _wait_until(lambda: len(git_sync.list_workpads(repo_id)) > 0)
        workpad = git_sync.list_workpads(repo_id)[0]
        workpad_id = workpad["id"]
        assert workpad_id

        await pilot.press("ctrl+t")
        await _wait_until(
            lambda: git_sync.get_test_runs(workpad_id)
            and git_sync.get_test_runs(workpad_id)[0]["status"] != "pending"
        )
        test_runs = git_sync.get_test_runs(workpad_id)
        assert test_runs[0]["status"] == "passed"

        workpad_meta = git_sync.git_engine.get_workpad(workpad_id)
        repo_meta = git_sync.git_engine.get_repo(workpad_meta.repo_id)
        repo = Repo(repo_meta.path)
        repo.git.checkout(workpad_meta.branch_name)
        readme = repo_path / "README.md"
        readme.write_text(readme.read_text() + "\nNew line\n")
        repo.index.add([str(readme.relative_to(repo_path))])
        repo.index.commit("Update README")
        repo.git.checkout(repo_meta.trunk_branch)

        await pilot.press("ctrl+shift+p")
        await _wait_until(
            lambda: git_sync.state_manager.get_workpad(workpad_id).status == "promoted"
        )

        final_state = git_sync.state_manager.get_workpad(workpad_id)
        assert final_state.status == "promoted"
