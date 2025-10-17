
"""
State management for Solo Git Heaven Interface.

This module provides a shared state layer that connects the CLI/TUI
with the GUI companion app.
"""

from sologit.state.schema import (
    WorkpadStatus,
    TestStatus,
    AIOperationStatus,
    CommitNode,
    TestResult,
    TestRun,
    AIOperation,
    WorkpadState,
    RepositoryState,
    GlobalState,
    EventType,
    StateEvent,
)
from sologit.state.manager import StateManager

__all__ = [
    'WorkpadStatus',
    'TestStatus',
    'AIOperationStatus',
    'CommitNode',
    'TestResult',
    'TestRun',
    'AIOperation',
    'WorkpadState',
    'RepositoryState',
    'GlobalState',
    'EventType',
    'StateEvent',
    'StateManager',
]
