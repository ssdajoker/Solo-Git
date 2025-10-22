"""
File Tree Viewer for Heaven Interface.

Displays repository file structure with git status indicators.
"""

from textual.app import ComposeResult
from textual.widgets import Tree, Static
from textual.reactive import reactive
from textual import events
from pathlib import Path
from typing import Dict, Optional, Set, List
from dataclasses import dataclass

from sologit.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FileStatus:
    """File status information."""
    path: str
    status: str  # 'modified', 'added', 'deleted', 'untracked', 'clean'
    is_dir: bool = False


class FileTreeWidget(Static):
    """Widget for displaying file tree with git status."""
    
    CSS = """
    FileTreeWidget {
        width: 100%;
        height: 100%;
        border: solid $primary;
        padding: 1;
    }
    
    FileTreeWidget Tree {
        width: 100%;
        height: 100%;
    }
    
    .file-modified {
        color: $warning;
    }
    
    .file-added {
        color: $success;
    }
    
    .file-deleted {
        color: $error;
    }
    
    .file-untracked {
        color: $accent;
    }
    
    .file-clean {
        color: $text;
    }
    
    .directory {
        color: $primary;
        text-style: bold;
    }
    """
    
    repo_path: reactive[Optional[str]] = reactive(None)
    show_hidden: reactive[bool] = reactive(False)
    
    def __init__(self, repo_path: Optional[str] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._repo_path_value = repo_path
        self.file_statuses: Dict[str, FileStatus] = {}
        self.selected_file: Optional[str] = None

    def compose(self) -> ComposeResult:
        """Compose the file tree."""
        tree = Tree("Repository", id="file-tree")
        tree.show_root = True
        tree.show_guides = True
        yield tree
    
    def on_mount(self) -> None:
        """Handle mount event."""
        if self._repo_path_value:
            self.load_tree(self._repo_path_value)
    
    def load_tree(self, repo_path: str, file_statuses: Optional[Dict[str, str]] = None) -> None:
        """
        Load file tree from repository path.
        
        Args:
            repo_path: Path to repository
            file_statuses: Dict mapping file paths to status ('M', 'A', 'D', '?')
        """
        self._repo_path_value = repo_path
        
        # Parse file statuses
        if file_statuses:
            self.file_statuses = self._parse_statuses(file_statuses)
        
        # Rebuild tree
        tree = self.query_one("#file-tree", Tree)
        tree.clear()
        tree.label = Path(repo_path).name
        
        try:
            repo_path_obj = Path(repo_path)
            if not repo_path_obj.exists():
                logger.warning(f"Repository path does not exist: {repo_path}")
                return
            
            # Build tree recursively
            self._build_tree_node(tree.root, repo_path_obj, repo_path_obj)
            
        except Exception as e:
            logger.error(f"Failed to load file tree: {e}", exc_info=True)
    
    def _parse_statuses(self, git_status: Dict[str, str]) -> Dict[str, FileStatus]:
        """Parse git status output into FileStatus objects."""
        statuses = {}
        
        status_map = {
            'M': 'modified',
            'A': 'added',
            'D': 'deleted',
            '?': 'untracked',
            ' ': 'clean'
        }
        
        for path, status_code in git_status.items():
            status = status_map.get(status_code, 'clean')
            statuses[path] = FileStatus(path, status)
        
        return statuses
    
    def _build_tree_node(self, parent_node, path: Path, root: Path) -> None:
        """Recursively build tree nodes."""
        try:
            # Get all items in directory
            items = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
            
            for item in items:
                # Skip hidden files unless show_hidden is True
                if item.name.startswith('.') and not self.show_hidden:
                    continue
                
                # Get relative path for status lookup
                rel_path = str(item.relative_to(root))
                
                # Get file status
                file_status = self.file_statuses.get(rel_path, FileStatus(rel_path, 'clean'))
                
                # Create label with status indicator
                if item.is_dir():
                    icon = "📁"
                    label = f"{icon} {item.name}"
                    node = parent_node.add(label, data={"path": str(item), "is_dir": True})
                    if hasattr(node, "add_class"):
                        node.add_class("directory")
                    
                    # Recursively add children
                    try:
                        self._build_tree_node(node, item, root)
                    except PermissionError:
                        logger.warning(f"Permission denied: {item}")
                else:
                    # File status icon
                    status_icons = {
                        'modified': '●',
                        'added': '+',
                        'deleted': '-',
                        'untracked': '?',
                        'clean': ' '
                    }
                    status_icon = status_icons.get(file_status.status, ' ')
                    
                    # File type icon
                    file_icons = {
                        '.py': '🐍',
                        '.js': '📜',
                        '.ts': '📘',
                        '.json': '📋',
                        '.md': '📝',
                        '.txt': '📄',
                        '.yml': '⚙️',
                        '.yaml': '⚙️',
                        '.toml': '⚙️',
                        '.html': '🌐',
                        '.css': '🎨',
                        '.sh': '🔧',
                        '.go': '🐹',
                        '.rs': '🦀',
                    }
                    file_icon = file_icons.get(item.suffix, '📄')
                    
                    label = f"{status_icon} {file_icon} {item.name}"
                    node = parent_node.add(label, data={"path": str(item), "is_dir": False, "status": file_status.status})
                    if hasattr(node, "add_class"):
                        node.add_class(f"file-{file_status.status}")
        
        except PermissionError:
            logger.warning(f"Permission denied: {path}")
    
    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle tree node selection."""
        if event.node.data:
            self.selected_file = event.node.data.get("path")
            is_dir = event.node.data.get("is_dir", False)
            
            # Emit custom event
            self.post_message(FileSelected(self.selected_file, is_dir))
    
    def refresh_status(self, file_statuses: Dict[str, str]) -> None:
        """Refresh file statuses without rebuilding entire tree."""
        if self._repo_path_value:
            self.load_tree(self._repo_path_value, file_statuses)
    
    def toggle_hidden(self) -> None:
        """Toggle showing hidden files."""
        self.show_hidden = not self.show_hidden
        if self._repo_path_value:
            self.load_tree(self._repo_path_value, {})
    
    def expand_all(self) -> None:
        """Expand all tree nodes."""
        tree = self.query_one("#file-tree", Tree)
        tree.root.expand_all()
    
    def collapse_all(self) -> None:
        """Collapse all tree nodes."""
        tree = self.query_one("#file-tree", Tree)
        tree.root.collapse_all()
    
    def get_selected_file(self) -> Optional[str]:
        """Get currently selected file path."""
        return self.selected_file


class FileSelected(events.Message):
    """Message emitted when a file is selected."""
    
    def __init__(self, file_path: str, is_dir: bool) -> None:
        super().__init__()
        self.file_path = file_path
        self.is_dir = is_dir


class DiffViewer(Static):
    """Widget for displaying git diffs."""
    
    CSS = """
    DiffViewer {
        width: 100%;
        height: 100%;
        border: solid $primary;
        padding: 1;
        overflow-y: auto;
    }
    
    .diff-header {
        color: $primary;
        text-style: bold;
    }
    
    .diff-add {
        color: $success;
        background: $success 10%;
    }
    
    .diff-remove {
        color: $error;
        background: $error 10%;
    }
    
    .diff-context {
        color: $text-muted;
    }
    
    .diff-hunk {
        color: $accent;
        text-style: bold;
    }
    """
    
    diff_text: reactive[str] = reactive("")
    
    def render(self) -> str:
        """Render the diff."""
        if not self.diff_text:
            return "[i]No changes to display[/i]"
        
        return self._format_diff(self.diff_text)
    
    def _format_diff(self, diff: str) -> str:
        """Format diff text with colors."""
        lines = diff.split('\n')
        formatted = []
        
        for line in lines:
            if line.startswith('+++') or line.startswith('---'):
                formatted.append(f"[bold cyan]{line}[/]")
            elif line.startswith('+'):
                formatted.append(f"[green]{line}[/]")
            elif line.startswith('-'):
                formatted.append(f"[red]{line}[/]")
            elif line.startswith('@@'):
                formatted.append(f"[bold yellow]{line}[/]")
            elif line.startswith('diff --git'):
                formatted.append(f"[bold magenta]{line}[/]")
            else:
                formatted.append(f"[dim]{line}[/]")
        
        return '\n'.join(formatted)
    
    def set_diff(self, diff_text: str) -> None:
        """Set the diff text to display."""
        self.diff_text = diff_text
        self.refresh()
    
    def clear(self) -> None:
        """Clear the diff display."""
        self.diff_text = ""
        self.refresh()
