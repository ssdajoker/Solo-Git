# Heaven Interface - Keyboard Shortcuts Reference

**Version:** 0.4.0  
**Last Updated:** October 17, 2025

---

## 📋 Table of Contents

1. [Global Shortcuts](#global-shortcuts)
2. [Command Palette](#command-palette)
3. [TUI Navigation](#tui-navigation)
4. [File Operations](#file-operations)
5. [Git Operations](#git-operations)
6. [Testing](#testing)
7. [AI Commands](#ai-commands)
8. [History & Undo](#history--undo)
9. [View Controls](#view-controls)
10. [Quick Reference Card](#quick-reference-card)

---

## Global Shortcuts

These shortcuts work across all interfaces (CLI, TUI, GUI):

| Shortcut | Action | Context | Description |
|----------|--------|---------|-------------|
| `Ctrl+P` | Command Palette | All | Open fuzzy command search |
| `Ctrl+Q` | Quit | TUI/GUI | Exit application |
| `Ctrl+C` | Cancel | All | Cancel current operation |
| `?` | Help | TUI | Show help screen with all shortcuts |
| `Esc` | Dismiss | All | Close overlay/modal |

---

## Command Palette

The command palette is your primary interface for all operations. Access it with `Ctrl+P`.

### Using the Palette

- **Type to search**: Fuzzy matching finds commands quickly
- **Arrow keys**: Navigate results
- **Enter**: Execute selected command
- **Esc**: Close palette without executing

### Common Searches

- `create` → Create workpad, repository, etc.
- `test` → Run tests, view test results
- `commit` → Commit changes, view history
- `ai` → AI operations (generate, review, refactor)
- `diff` → View changes, compare versions

---

## TUI Navigation

### Panel Focus

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Tab` | Next Panel | Move focus to next panel |
| `Shift+Tab` | Previous Panel | Move focus to previous panel |
| `Ctrl+1` | Left Panel | Focus commit graph/file tree |
| `Ctrl+2` | Center Panel | Focus workpad/AI activity |
| `Ctrl+3` | Right Panel | Focus test runner/diff viewer |

### Panel Operations

| Shortcut | Action | Description |
|----------|--------|-------------|
| `[` | Toggle Left | Show/hide left panel |
| `]` | Toggle Right | Show/hide right panel |
| `=` | Balance Panels | Reset panel sizes |
| `+/-` | Resize Panel | Increase/decrease focused panel size |

### List Navigation

| Shortcut | Action | Description |
|----------|--------|-------------|
| `↑/↓` | Navigate | Move up/down in lists |
| `j/k` | Vim Navigation | Move down/up (Vim-style) |
| `g` | Top | Jump to top of list |
| `G` | Bottom | Jump to bottom of list |
| `Ctrl+D` | Page Down | Scroll down half page |
| `Ctrl+U` | Page Up | Scroll up half page |

---

## File Operations

### File Tree (TUI)

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Enter` | Open File | View file in diff viewer |
| `Space` | Select | Toggle file selection |
| `o` | Expand/Collapse | Toggle folder |
| `O` | Expand All | Expand all folders |
| `a` | Add File | Create new file |
| `d` | Delete File | Delete selected file |
| `r` | Rename | Rename selected file |
| `.` | Toggle Hidden | Show/hide dotfiles |

### Code Viewer (GUI)

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Ctrl+F` | Find | Search in file |
| `Ctrl+H` | Replace | Find and replace |
| `Ctrl+/` | Toggle Comment | Comment/uncomment line |
| `Ctrl+]` | Indent | Increase indentation |
| `Ctrl+[` | Outdent | Decrease indentation |
| `Alt+Up/Down` | Move Line | Move line up/down |
| `Ctrl+Shift+K` | Delete Line | Delete current line |

---

## Git Operations

### Workpad Management

| Shortcut | Action | CLI Command | Description |
|----------|--------|-------------|-------------|
| `Ctrl+N` | New Workpad | `pad create` | Create new workpad |
| `Ctrl+W` | Workpad List | `pad list` | View all workpads |
| `Ctrl+Shift+W` | Switch Workpad | `pad switch` | Switch active workpad |
| `Ctrl+M` | Merge/Promote | `pad promote` | Merge to trunk (if tests pass) |
| `Ctrl+D` | View Diff | `pad diff` | Show changes |

### Commit Operations

| Shortcut | Action | CLI Command | Description |
|----------|--------|-------------|-------------|
| `c` | Commit | `commit` | Commit changes |
| `C` | Commit All | `commit --all` | Stage and commit all |
| `Ctrl+L` | View Log | `history log` | View commit history |
| `Ctrl+G` | Commit Graph | View in TUI | Visual commit graph |

---

## Testing

### Test Execution

| Shortcut | Action | CLI Command | Description |
|----------|--------|-------------|-------------|
| `Ctrl+T` | Run Tests | `test run` | Run fast tests |
| `Ctrl+Shift+T` | Run All Tests | `test run --target full` | Run all tests |
| `t` | Test This | Context-dependent | Test current file/module |
| `T` | Test Coverage | `test analyze` | View test coverage |

### Test Viewing

| Shortcut | Action | Description |
|----------|--------|-------------|
| `f` | Failed Tests | Jump to failed tests |
| `p` | Passed Tests | Jump to passed tests |
| `s` | Skipped Tests | Jump to skipped tests |
| `x` | Clear Output | Clear test output panel |

---

## AI Commands

### Quick AI Operations

| Shortcut | Action | CLI Command | Description |
|----------|--------|-------------|-------------|
| `Ctrl+A` | AI Assistant | Opens AI pane | Open AI assistant |
| `Ctrl+G` | Generate Code | `ai generate` | Generate code from prompt |
| `Ctrl+R` | AI Review | `ai review` | AI code review |
| `Ctrl+E` | Explain | `ai explain` | Explain code |
| `Ctrl+Shift+R` | Refactor | `ai refactor` | AI-powered refactoring |

### AI Pairing

| Shortcut | Action | CLI Command | Description |
|----------|--------|-------------|-------------|
| `Space` | Pair Session | `pair "prompt"` | Start pair programming |
| `Enter` | Accept Suggestion | In AI pane | Accept AI suggestion |
| `Esc` | Reject | In AI pane | Reject AI suggestion |
| `Ctrl+Space` | More Options | In AI pane | Show alternative solutions |

---

## History & Undo

### Command History

| Shortcut | Action | CLI Command | Description |
|----------|--------|-------------|-------------|
| `Ctrl+Z` | Undo | `history undo` | Undo last command |
| `Ctrl+Y` | Redo | `history redo` | Redo undone command |
| `Ctrl+Shift+Z` | Redo (Alt) | `history redo` | Alternative redo |
| `Ctrl+H` | View History | `history log` | View command history |

### Navigation History

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Alt+Left` | Back | Navigate to previous file/view |
| `Alt+Right` | Forward | Navigate to next file/view |
| `Ctrl+P` then `@` | Symbol | Jump to symbol in file |
| `Ctrl+P` then `#` | Workspace Symbol | Jump to symbol in workspace |

---

## View Controls

### Display

| Shortcut | Action | Description |
|----------|--------|-------------|
| `R` | Refresh | Refresh all panels |
| `Ctrl+R` | Refresh Panel | Refresh focused panel |
| `Ctrl+Shift+R` | Hard Refresh | Reload from disk |
| `F11` | Fullscreen | Toggle fullscreen mode |
| `Ctrl+0` | Reset Zoom | Reset zoom level |

### Zen Mode

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Ctrl+K Z` | Zen Mode | Enter distraction-free mode |
| `Esc Esc` | Exit Zen | Exit zen mode |
| `Ctrl+B` | Toggle Sidebar | Show/hide sidebar |

---

## Quick Reference Card

### Essential Shortcuts (Print This!)

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃         HEAVEN INTERFACE QUICK REFERENCE       ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                                 ┃
┃  MUST KNOW                                      ┃
┃  ─────────                                      ┃
┃  Ctrl+P    Command Palette (your best friend)  ┃
┃  Ctrl+Q    Quit                                 ┃
┃  ?         Help                                 ┃
┃  R         Refresh                              ┃
┃                                                 ┃
┃  WORKPADS                                       ┃
┃  ────────                                       ┃
┃  Ctrl+N    New workpad                          ┃
┃  Ctrl+M    Merge (promote)                      ┃
┃  Ctrl+D    View diff                            ┃
┃                                                 ┃
┃  TESTING                                        ┃
┃  ───────                                        ┃
┃  Ctrl+T    Run tests                            ┃
┃  Ctrl+Shift+T  Run all tests                    ┃
┃                                                 ┃
┃  AI PAIRING                                     ┃
┃  ──────────                                     ┃
┃  Space     Start pair session                   ┃
┃  Ctrl+G    Generate code                        ┃
┃  Ctrl+R    AI review                            ┃
┃                                                 ┃
┃  HISTORY                                        ┃
┃  ───────                                        ┃
┃  Ctrl+Z    Undo                                 ┃
┃  Ctrl+Y    Redo                                 ┃
┃  Ctrl+L    View log                             ┃
┃                                                 ┃
┃  REMEMBER: Everything is in Ctrl+P!             ┃
┃            Just type what you want to do        ┃
┃                                                 ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

---

## Interactive Shell (CLI)

When using `evogitctl interactive`:

| Feature | Behavior |
|---------|----------|
| **Tab Completion** | Press Tab to autocomplete commands |
| **History** | Up/Down arrows to navigate history |
| **Fuzzy Matching** | Type partial command, get suggestions |
| **Ctrl+R** | Reverse search history |
| **Ctrl+D** | Exit interactive shell |

---

## Customization

### Custom Shortcuts

You can customize shortcuts in your config file:

```yaml
# ~/.sologit/config.yaml
shortcuts:
  command_palette: "ctrl+p"
  run_tests: "ctrl+t"
  ai_generate: "ctrl+g"
  # Add your own!
```

### Disable Shortcuts

To disable a shortcut:

```yaml
shortcuts:
  some_command: null  # Disables the shortcut
```

---

## Platform-Specific Notes

### macOS

- Use `Cmd` instead of `Ctrl` for most shortcuts
- `Ctrl+Left/Right` → Word navigation
- `Cmd+Left/Right` → Line start/end

### Windows/Linux

- Standard Ctrl-based shortcuts
- Alt combinations for menu navigation

---

## Tips & Tricks

### 💡 Pro Tips

1. **Command Palette is Everything**: When in doubt, `Ctrl+P` and type what you want
2. **Learn Fuzzy Search**: Type `tml` to find "test run --target full"
3. **Use Vim Keys**: `j/k` for navigation if you're a Vim user
4. **Zen Mode for Focus**: `Ctrl+K Z` for distraction-free coding
5. **History is Your Friend**: `Ctrl+H` shows all past commands

### 🎯 Workflow Shortcuts

**Quick test cycle:**
```
Ctrl+T → View results → Fix → Ctrl+T → Repeat
```

**AI pair programming:**
```
Space → Type prompt → Enter → Review → Accept/Reject
```

**Review before merge:**
```
Ctrl+D → Review diff → Ctrl+T → Run tests → Ctrl+M → Merge
```

---

## Learning Path

### Day 1: Basics
- `Ctrl+P` (Command Palette)
- `Ctrl+T` (Run Tests)
- `?` (Help)

### Week 1: Workpads
- `Ctrl+N` (New Workpad)
- `Ctrl+M` (Merge)
- `Ctrl+Z/Y` (Undo/Redo)

### Week 2: AI Pairing
- `Space` (Pair Session)
- `Ctrl+G` (Generate)
- `Ctrl+R` (Review)

### Week 3: Power User
- Custom shortcuts
- Fuzzy search mastery
- TUI panel navigation

---

## Support

- **Full docs**: `docs/HEAVEN_INTERFACE_GUIDE.md`
- **Examples**: `examples/` directory
- **Help command**: `evogitctl --help`
- **In-app help**: Press `?` in TUI

---

*Heaven Interface - Where simplicity meets power.*
