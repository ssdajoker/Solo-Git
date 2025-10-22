"""Keyboard shortcut definitions for the Heaven Interface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence


@dataclass(frozen=True)
class Shortcut:
    """Representation of a single keyboard shortcut."""

    key: str
    action: str
    context: str


@dataclass(frozen=True)
class ShortcutCategory:
    """Group of related keyboard shortcuts."""

    name: str
    shortcuts: Sequence[Shortcut]


SHORTCUT_CATEGORIES: Sequence[ShortcutCategory] = (
    ShortcutCategory(
        name="Navigation",
        shortcuts=(
            Shortcut("Ctrl+P", "Open command palette", "Global"),
            Shortcut("Tab / Shift+Tab", "Switch between panels", "Global"),
            Shortcut("Arrow Keys", "Navigate within focused panel", "Global"),
        ),
    ),
    ShortcutCategory(
        name="Workpads",
        shortcuts=(
            Shortcut("Ctrl+N", "Create new workpad", "Workpads"),
            Shortcut("Ctrl+W", "Close active workpad", "Workpads"),
            Shortcut("Ctrl+D", "Show workpad diff", "Workpads"),
            Shortcut("Ctrl+S", "Commit workpad changes", "Workpads"),
        ),
    ),
    ShortcutCategory(
        name="Testing",
        shortcuts=(
            Shortcut("Ctrl+T", "Run focused tests", "Testing"),
            Shortcut("Ctrl+Shift+T", "Run full test suite", "Testing"),
            Shortcut("Ctrl+L", "Clear test output", "Testing"),
        ),
    ),
    ShortcutCategory(
        name="AI Assistance",
        shortcuts=(
            Shortcut("Ctrl+G", "Generate code with AI", "AI"),
            Shortcut("Ctrl+R", "Review code with AI", "AI"),
            Shortcut("Ctrl+M", "Generate commit message", "AI"),
        ),
    ),
    ShortcutCategory(
        name="History",
        shortcuts=(
            Shortcut("Ctrl+Z", "Undo last command", "History"),
            Shortcut("Ctrl+Shift+Z", "Redo command", "History"),
            Shortcut("Ctrl+H", "Show command history", "History"),
        ),
    ),
    ShortcutCategory(
        name="View",
        shortcuts=(
            Shortcut("Ctrl+B", "Toggle file browser", "View"),
            Shortcut("Ctrl+1", "Focus commit graph", "View"),
            Shortcut("Ctrl+2", "Focus workpad panel", "View"),
            Shortcut("Ctrl+3", "Focus test output", "View"),
            Shortcut("Ctrl+F", "Search files", "View"),
        ),
    ),
    ShortcutCategory(
        name="General",
        shortcuts=(
            Shortcut("R", "Refresh interface", "Global"),
            Shortcut("?", "Show help overlay", "Global"),
            Shortcut("Ctrl+Q", "Quit application", "Global"),
            Shortcut("Ctrl+C", "Cancel current operation", "Global"),
        ),
    ),
)


def iter_shortcuts() -> Iterable[Shortcut]:
    """Iterate through all registered shortcuts."""

    for category in SHORTCUT_CATEGORIES:
        yield from category.shortcuts
def format_help_markup() -> str:
    """Return Rich markup for the help modal."""

    lines: List[str] = ["[bold cyan]Heaven Interface - Keyboard Shortcuts[/]", ""]
    for category in SHORTCUT_CATEGORIES:
        lines.append(f"[bold yellow]{category.name}[/]")
        for shortcut in category.shortcuts:
            lines.append(f"  {shortcut.key:<15} {shortcut.action}")
        lines.append("")
    lines.append("[bold green]Press Escape or Q to close this help[/]")
    return "\n".join(lines)


def get_status_bar_summary() -> str:
    """Return a concise summary string for the status bar."""

    summary_shortcuts = (
        ("Ctrl+P", "Palette"),
        ("Ctrl+T", "Tests"),
        ("Ctrl+Z", "Undo"),
        ("Ctrl+Shift+Z", "Redo"),
        ("?", "Help"),
        ("Ctrl+Q", "Quit"),
    )
    return "  •  ".join(f"{key}: {label}" for key, label in summary_shortcuts)
