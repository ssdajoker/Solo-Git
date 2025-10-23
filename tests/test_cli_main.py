import importlib
import sys
import types
from pathlib import Path

import click
import pytest


class DummyFormatter:
    def __init__(self):
        self.last_call = None

    def print_error(self, *args, **kwargs):
        self.last_call = (args, kwargs)


class DummyHistory:
    def __init__(self):
        self.commands = []
        self.results = []

    def record_cli_command(self, description, arguments=None, record_text=True):
        self.commands.append(
            {
                "description": description,
                "arguments": arguments,
                "record_text": record_text,
            }
        )
        return "entry-1"

    def update_command_result(self, entry_id, result):
        self.results.append((entry_id, result))


class DummyConfigManager:
    def __init__(self, config_path=None):
        self.config_path = config_path or Path("/tmp/config.yaml")

    def has_abacus_credentials(self):
        return False


@pytest.fixture
def cli_main(monkeypatch):
    stub_commands = types.ModuleType("sologit.cli.commands")
    stub_commands.set_formatter_console = lambda console: None
    stub_commands.pad = click.Group("pad")
    stub_commands.repo = click.Group("repo")
    stub_commands.test = click.Group("test")
    stub_commands.ci = click.Group("ci")

    def execute_pair_loop(**_: object) -> None:
        raise RuntimeError("pair loop not implemented in tests")

    stub_commands.execute_pair_loop = execute_pair_loop

    stub_config = types.ModuleType("sologit.cli.config_commands")
    stub_config.set_formatter_console = lambda console: None
    stub_config.ConfigManager = DummyConfigManager
    stub_config.config_group = click.Group("config")

    stub_integrated = types.ModuleType("sologit.cli.integrated_commands")
    stub_integrated.set_formatter_console = lambda console: None
    stub_integrated.ai = click.Group("ai")
    stub_integrated.edit = click.Group("edit")
    stub_integrated.history = click.Group("history")
    stub_integrated.workpad = click.Group("workpad")

    monkeypatch.setitem(sys.modules, "sologit.cli.commands", stub_commands)
    monkeypatch.setitem(sys.modules, "sologit.cli.config_commands", stub_config)
    monkeypatch.setitem(sys.modules, "sologit.cli.integrated_commands", stub_integrated)

    sys.modules.pop("sologit.cli.main", None)
    module = importlib.import_module("sologit.cli.main")
    return module


def test_find_heaven_gui_dir_prefers_cwd(cli_main, monkeypatch, tmp_path):
    target = tmp_path / "heaven-gui"
    target.mkdir()
    monkeypatch.chdir(tmp_path)

    result = cli_main._find_heaven_gui_dir()

    assert result == target


def test_find_heaven_gui_dir_from_module_parents(cli_main, monkeypatch, tmp_path):
    project_root = tmp_path / "project"
    cli_dir = project_root / "pkg" / "cli"
    cli_dir.mkdir(parents=True)
    fake_main = cli_dir / "main.py"
    fake_main.write_text("# fake")

    target = project_root / "heaven-gui"
    target.mkdir()

    monkeypatch.setattr(cli_main, "__file__", str(fake_main))
    monkeypatch.chdir(tmp_path)

    result = cli_main._find_heaven_gui_dir()

    assert result == target


@pytest.mark.parametrize(
    "platform, path_builder",
    [
        ("win32", lambda gui_dir: gui_dir / "solo-git-gui.exe"),
        (
            "darwin",
            lambda gui_dir: gui_dir
            / "solo-git-gui.app"
            / "Contents"
            / "MacOS"
            / "solo-git-gui",
        ),
        ("linux", lambda gui_dir: gui_dir / "solo-git-gui"),
    ],
)
def test_resolve_gui_executable(cli_main, monkeypatch, tmp_path, platform, path_builder):
    gui_dir = tmp_path / ".sologit" / "gui"
    target = path_builder(gui_dir)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("#!/bin/sh\n")

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(sys, "platform", platform)

    result = cli_main._resolve_gui_executable()

    assert result == target


def test_abort_with_error_raises(cli_main, monkeypatch):
    formatter = DummyFormatter()
    monkeypatch.setattr(cli_main, "formatter", formatter)

    with pytest.raises(click.Abort):
        cli_main.abort_with_error(
            "Something went wrong",
            "stacktrace",
            title="Boom",
            help_text="Fix it",
            tip="Check flags",
            suggestions=["try --help"],
            docs_url="docs/issue",
        )

    args, kwargs = formatter.last_call
    assert args == ("Boom", "Something went wrong")
    assert kwargs["details"] == "stacktrace"
    assert kwargs["help_text"] == "Fix it"
    assert kwargs["tip"] == "Check flags"
    assert kwargs["suggestions"] == ["try --help"]
    assert kwargs["docs_url"] == "docs/issue"


def test_execute_cli_command_records_history(cli_main, monkeypatch):
    history = DummyHistory()

    monkeypatch.setattr(cli_main, "get_command_history", lambda: history)
    monkeypatch.setattr(cli_main, "ConfigManager", DummyConfigManager)

    exit_code = cli_main._execute_cli_command(["hello"])

    assert exit_code == 0
    assert history.commands == [
        {
            "description": "hello",
            "arguments": {"argv": ["hello"]},
            "record_text": True,
        }
    ]
    assert history.results == [("entry-1", {"exit_code": 0})]


def test_main_uses_interactive_shell(cli_main, monkeypatch):
    called = {}

    monkeypatch.setattr(cli_main, "_run_interactive_shell", lambda: called.setdefault("shell", 0))
    monkeypatch.setattr(cli_main, "_execute_cli_command", lambda args: called.__setitem__("cmd", args))

    monkeypatch.setattr(cli_main.sys, "argv", ["evogitctl"])

    class DummyStdin:
        @staticmethod
        def isatty():
            return True

    monkeypatch.setattr(cli_main.sys, "stdin", DummyStdin())

    exit_codes = []
    monkeypatch.setattr(cli_main.sys, "exit", lambda code: exit_codes.append(code))

    cli_main.main()

    assert called["shell"] == 0
    assert "cmd" not in called
    assert exit_codes == [0]
