# Heaven Interface Playbook

**The definitive guide to Solo Git's minimalist, code-first interface.**

> *"As little design as possible."*

---

## 1. Philosophy & Design System

Heaven is Solo Git's minimalist, code-first interface inspired by the design principles of Jony Ive and Dieter Rams. It is not a single application, but a unified design system that spans three distinct modes of interaction: a command-line interface (CLI), a terminal user interface (TUI), and a graphical user interface (GUI).

### Core Principles

- **Code is King**: The user's code is always the central focus. UI elements are unobtrusive and serve to enhance, not distract from, the code.
- **Keyboard-First**: All operations are optimized for keyboard use, with intuitive shortcuts and a powerful command palette.
- **Minimalism**: Every element has a purpose. There is no decoration for its own sake.
- **Consistency**: The same core concepts and commands are available across the CLI, TUI, and GUI, providing a seamless experience.

### Design Tokens

- **Typography**: JetBrains Mono/SF Mono for code; SF Pro/Roboto for UI.
- **Color**: A dark base (`#1E1E1E`), light text (`#DDD`), and only 2-3 accent colors (e.g., `#61AFEF` blue, `#98C379` green, `#E06C75` red).
- **Spacing**: A consistent 8px grid system with generous margins (16-24px).
- **Icons**: Monoline, 2px stroke, 24×24px, and monochrome.
- **Motion**: Subtle 150-300ms animations with ease-in-out transitions.

---

## 2. Architecture: A Unified System

The Heaven Interface is powered by a shared state management system that ensures consistency across the CLI, TUI, and GUI.

### State Synchronization

```
┌─────────────┬─────────────┬─────────────┐
│     CLI     │     TUI     │     GUI     │
└─────┬───────┴──────┬──────┴──────┬──────┘
      │              │             │
      └──────────────┼─────────────┘
                     │
            ┌────────▼────────┐
            │  JSON State     │
            │  ~/.sologit/    │
            └─────────────────┘
```

All interfaces read and write to a shared set of JSON files located in `~/.sologit/state/`. This ensures that an action taken in one interface is immediately reflected in the others.

---

## 3. The Three Interfaces

### 3.1. Enhanced CLI

The command-line interface is the foundation of the Heaven Interface, providing a powerful and scriptable way to interact with Solo Git.

- **Rich Formatting**: The CLI uses the `rich` library to provide beautifully formatted output, including tables, panels, progress bars, and syntax-highlighted code.
- **Interactive Shell**: An optional interactive shell (`evogitctl interactive`) provides command history, tab-completion, and fuzzy-searching.
- **JSON Output**: All commands support a `--json` flag for easy integration with other tools and, most importantly, the GUI.

### 3.2. Interactive TUI (Terminal User Interface)

The TUI provides a full-screen, keyboard-driven experience within the terminal.

- **Launch**: `evogitctl tui`
- **Layout**: A multi-panel layout that displays the commit graph, file tree, workpad status, AI activity, test runner, and a diff viewer.
- **Command Palette**: A VS Code-style command palette (`Ctrl+P`) provides fuzzy searching over all available commands.
- **Real-time Updates**: The TUI automatically refreshes to reflect the latest state.

### 3.3. Desktop GUI

The GUI is a Tauri-based desktop application (Rust + React) that provides a rich, visual experience.

- **Monaco Editor**: The core of the GUI is the same editor that powers VS Code, providing a world-class code editing experience.
- **D3.js Commit Graph**: An interactive, visual representation of the project's history.
- **Test Dashboard**: Rich visualizations of test results and trends using Recharts.
- **AI Assistant**: A dedicated panel for interacting with Solo Git's AI capabilities.
- **Write Operations**: The GUI supports all core Solo Git operations, including creating workpads, running tests, and promoting changes.

---

## 4. Capabilities & Operational Runbooks

This section provides a practical guide to using the Heaven Interface for common Solo Git workflows.

### Workpad Lifecycle

| Operation | CLI Command | TUI Shortcut | GUI Action |
|---|---|---|---|
| **Create Workpad** | `evogitctl pad create "<title>"` | `Ctrl+N` | "Create Workpad" button/command |
| **Run Tests** | `evogitctl test run` | `Ctrl+T` | "Run Tests" button/command |
| **Promote Workpad** | `evogitctl pad promote` | `Ctrl+P` -> "Promote" | "Promote Workpad" button/command |
| **Delete Workpad** | `evogitctl pad delete` | `Ctrl+P` -> "Delete" | "Delete Workpad" button/command |

### AI-Assisted Development

| Operation | CLI Command | TUI Shortcut | GUI Action |
|---|---|---|---|
| **Generate Code** | `evogitctl ai generate "<prompt>"` | `Ctrl+G` | AI Assistant panel |
| **Refactor Code** | `evogitctl ai refactor <file>` | `Ctrl+R` | AI Assistant panel |
| **Generate Tests** | `evogitctl ai test-gen <file>` | `Ctrl+P` -> "Gen Tests" | AI Assistant panel |

### History & Undo

| Operation | CLI Command | TUI Shortcut |
|---|---|---|
| **Undo Last Action** | `evogitctl edit undo` | `Ctrl+Z` |
| **Redo Last Action** | `evogitctl edit redo` | `Ctrl+Y` |
| **View History** | `evogitctl edit history` | `Ctrl+H` |

---

## 5. Keyboard Shortcuts

The Heaven Interface is designed to be used primarily with the keyboard. For a complete list of shortcuts, please see the **[Keyboard Shortcuts Guide](KEYBOARD_SHORTCUTS.md)**.

---

This playbook provides a high-level overview of the Heaven Interface. For more detailed information, please refer to the specific guides for each interface and the project's main documentation.
