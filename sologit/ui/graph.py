
"""
ASCII commit graph renderer for Heaven Interface CLI/TUI.

Renders commit history as an ASCII art graph with test indicators.
"""

from typing import List, Optional, Dict, Any
from rich.console import Console
from rich.text import Text
from sologit.ui.theme import theme
from sologit.state.schema import CommitNode


class CommitGraphRenderer:
    """Renders commit graphs in ASCII art format."""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.theme = theme
    
    def render_commit_line(self, commit: CommitNode, is_latest: bool = False) -> Text:
        """Render a single commit line."""
        text = Text()
        
        # Commit node
        if commit.is_trunk:
            node_char = "●"
            node_color = self.theme.colors.trunk
        elif commit.workpad_id:
            node_char = "○"
            node_color = self.theme.colors.workpad
        else:
            node_char = "●"
            node_color = self.theme.colors.commit
        
        text.append(node_char, style=node_color)
        text.append(" ")
        
        # Test status indicator
        if commit.test_status:
            test_icon = self.theme.get_status_icon(commit.test_status)
            test_color = self.theme.get_status_color(commit.test_status)
            text.append(test_icon, style=test_color)
        else:
            text.append(" ")
        text.append(" ")
        
        # CI status indicator
        if commit.ci_status:
            if commit.ci_status == 'passed':
                text.append("✓", style=self.theme.colors.success)
            elif commit.ci_status == 'failed':
                text.append("✗", style=self.theme.colors.error)
            elif commit.ci_status == 'running':
                text.append("◉", style=self.theme.colors.running)
        else:
            text.append(" ")
        text.append(" ")
        
        # Short SHA
        text.append(commit.short_sha, style=self.theme.colors.text_secondary)
        text.append(" ")
        
        # Commit message (truncated)
        message = commit.message.split('\n')[0]
        if len(message) > 60:
            message = message[:57] + "..."
        text.append(message, style=self.theme.colors.text_primary)
        
        # Author and time
        text.append(f" ({commit.author})", style=self.theme.colors.text_muted)
        
        return text
    
    def render_connection(self, has_child: bool = True) -> Text:
        """Render connection line between commits."""
        text = Text()
        if has_child:
            text.append("│", style=self.theme.colors.text_secondary)
        else:
            text.append(" ", style=self.theme.colors.text_secondary)
        return text
    
    def render_graph(self, commits: List[CommitNode], max_lines: int = 20) -> None:
        """Render a commit graph."""
        if not commits:
            self.console.print(f"[{self.theme.colors.text_secondary}]No commits yet[/{self.theme.colors.text_secondary}]")
            return
        
        # Header
        header = Text()
        header.append("● ", style=self.theme.colors.trunk)
        header.append("Node  ", style=self.theme.colors.text_secondary)
        header.append("🧪 ", style=self.theme.colors.text_secondary)
        header.append("Tests  ", style=self.theme.colors.text_secondary)
        header.append("✓ ", style=self.theme.colors.text_secondary)
        header.append("CI  ", style=self.theme.colors.text_secondary)
        header.append("SHA     ", style=self.theme.colors.text_secondary)
        header.append("Message", style=self.theme.colors.text_secondary)
        self.console.print(header)
        self.console.print("─" * 80, style=self.theme.colors.text_secondary)
        
        # Render commits
        display_commits = commits[:max_lines]
        for i, commit in enumerate(display_commits):
            is_latest = (i == 0)
            line = self.render_commit_line(commit, is_latest)
            self.console.print(line)
            
            # Connection line (except for last commit)
            if i < len(display_commits) - 1:
                connection = self.render_connection()
                self.console.print(connection)
        
        # Show truncation message if needed
        if len(commits) > max_lines:
            self.console.print(
                f"[{self.theme.colors.text_secondary}]... {len(commits) - max_lines} more commits[/{self.theme.colors.text_secondary}]"
            )
    
    def render_compact_graph(self, commits: List[CommitNode], width: int = 40) -> List[str]:
        """Render a compact graph suitable for sidebars (returns lines)."""
        lines = []
        
        for commit in commits[:10]:  # Show max 10 in compact mode
            # Node
            if commit.is_trunk:
                node = "●"
            else:
                node = "○"
            
            # Status
            if commit.test_status == 'passed':
                status = "✓"
            elif commit.test_status == 'failed':
                status = "✗"
            else:
                status = " "
            
            # Message (truncated to fit)
            message = commit.message.split('\n')[0]
            max_msg_len = width - 10
            if len(message) > max_msg_len:
                message = message[:max_msg_len - 3] + "..."
            
            line = f"{node} {status} {commit.short_sha} {message}"
            lines.append(line)
        
        return lines
