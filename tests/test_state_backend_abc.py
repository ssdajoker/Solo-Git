"""Tests for the StateBackend abstract base class implementation."""

import inspect
from pathlib import Path

import pytest

from sologit.state.manager import JSONStateBackend, StateBackend


def test_state_backend_is_abstract() -> None:
    """StateBackend should behave as an abstract base class."""
    assert inspect.isabstract(StateBackend)
    with pytest.raises(TypeError):
        StateBackend()  # type: ignore[abstract]


def test_json_state_backend_implements_contract(tmp_path: Path) -> None:
    """Concrete JSON backend should be instantiable and non-abstract."""
    assert not inspect.isabstract(JSONStateBackend)
    backend = JSONStateBackend(tmp_path)

    # Basic smoke test for implemented methods to ensure no NotImplementedError stubs remain
    backend.write_global_state(backend.read_global_state())
    assert backend.list_repositories() == []
    assert backend.list_workpads() == []
