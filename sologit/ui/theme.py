
"""
Heaven Interface Design System - Theme and Color Palette.

Implements the minimalist, Rams/Ive-inspired design system described
in the Heaven Interface specification.

Color Palette:
- Dark base (near-black): #1E1E1E
- Code/text (off-white): #DDDDDD
- Accent blue (keywords/buttons): #61AFEF
- Accent green (success/pass): #98C379
- Accent orange/red (warnings/errors): #E06C75
- Accent yellow (info): #E5C07B
- Muted gray (secondary text): #5C6370
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class ColorPalette:
    """Heaven Interface color palette."""
    
    # Base colors
    background: str = "#1E1E1E"
    surface: str = "#252526"
    
    # Text colors
    text_primary: str = "#DDDDDD"
    text_secondary: str = "#5C6370"
    text_muted: str = "#3E4451"
    
    # Accent colors
    blue: str = "#61AFEF"        # Keywords, buttons, info
    green: str = "#98C379"       # Success, passed tests
    orange: str = "#E5C07B"      # Warnings, pending
    red: str = "#E06C75"         # Errors, failed tests
    purple: str = "#C678DD"      # Special highlights
    cyan: str = "#56B6C2"        # Links, secondary actions
    
    # Semantic colors
    success: str = "#98C379"
    error: str = "#E06C75"
    warning: str = "#E5C07B"
    info: str = "#61AFEF"
    
    # Status colors
    passed: str = "#98C379"
    failed: str = "#E06C75"
    pending: str = "#E5C07B"
    running: str = "#61AFEF"
    
    # Git/VCS colors
    trunk: str = "#61AFEF"
    workpad: str = "#C678DD"
    commit: str = "#56B6C2"
    
    def to_rich_theme(self) -> Dict[str, str]:
        """Convert to Rich library theme dict."""
        return {
            "info": self.info,
            "success": self.success,
            "warning": self.warning,
            "error": self.error,
            "repr.number": self.blue,
            "repr.str": self.green,
            "repr.tag_name": self.cyan,
            "log.time": self.text_secondary,
        }


@dataclass
class Typography:
    """Typography settings for Heaven Interface."""
    
    # Font families
    mono_font: str = "JetBrains Mono, SF Mono, Consolas, monospace"
    sans_font: str = "SF Pro, -apple-system, Roboto, sans-serif"
    
    # Font sizes (in pixels)
    code_size: int = 14
    ui_size: int = 12
    heading_size: int = 16
    
    # Line heights
    code_line_height: str = "1.5"
    ui_line_height: str = "1.4"


@dataclass
class Spacing:
    """Spacing settings based on 8-point grid."""
    
    xs: int = 4
    sm: int = 8
    md: int = 16
    lg: int = 24
    xl: int = 32
    xxl: int = 48


@dataclass
class Icons:
    """Icon characters for CLI/TUI display."""
    
    # Status icons
    success: str = "✓"
    error: str = "✗"
    warning: str = "⚠"
    info: str = "ℹ"
    pending: str = "○"
    running: str = "◉"
    
    # Git icons
    commit: str = "●"
    branch: str = "⎇"
    tag: str = "⚑"
    merge: str = "⎇"
    trunk: str = "━"
    
    # Action icons
    arrow_right: str = "→"
    arrow_left: str = "←"
    arrow_up: str = "↑"
    arrow_down: str = "↓"
    
    # UI icons
    folder: str = "📁"
    file: str = "📄"
    test: str = "🧪"
    ai: str = "🤖"
    rocket: str = "🚀"
    hourglass: str = "⏳"


class HeavenTheme:
    """
    Complete Heaven Interface theme.
    
    Provides access to colors, typography, spacing, and icons for consistent
    UI rendering across CLI/TUI and GUI.
    """
    
    def __init__(self) -> None:
        self.colors = ColorPalette()
        self.typography = Typography()
        self.spacing = Spacing()
        self.icons = Icons()
    
    def get_status_color(self, status: str) -> str:
        """Get color for a status string."""
        status_lower = status.lower()
        if status_lower in ['passed', 'success', 'green', 'ok']:
            return self.colors.passed
        elif status_lower in ['failed', 'error', 'red']:
            return self.colors.failed
        elif status_lower in ['pending', 'waiting', 'queued', 'yellow']:
            return self.colors.pending
        elif status_lower in ['running', 'active', 'blue']:
            return self.colors.running
        else:
            return self.colors.text_secondary
    
    def get_status_icon(self, status: str) -> str:
        """Get icon for a status string."""
        status_lower = status.lower()
        if status_lower in ['passed', 'success', 'green', 'ok']:
            return self.icons.success
        elif status_lower in ['failed', 'error', 'red']:
            return self.icons.error
        elif status_lower in ['pending', 'waiting', 'queued']:
            return self.icons.pending
        elif status_lower in ['running', 'active']:
            return self.icons.running
        elif status_lower in ['warning', 'warn']:
            return self.icons.warning
        else:
            return self.icons.info


# Global theme instance
theme = HeavenTheme()

# Convenience export of colors
Colors = theme.colors
