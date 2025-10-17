
# Heaven GUI - Solo Git Companion App

The Heaven Interface GUI companion app for Solo Git, built with Tauri + React.

## Features

- Visual commit graph with test indicators
- Test dashboard with pass/fail trends
- Code viewer with syntax highlighting
- AI Assistant side pane
- Real-time state synchronization with CLI
- Keyboard-first command palette

## Development

### Prerequisites

- Node.js 18+
- Rust 1.70+
- Tauri CLI

### Setup

```bash
# Install dependencies
npm install

# Run in development mode
npm run tauri:dev

# Build for production
npm run tauri:build
```

## Architecture

### Frontend (React + TypeScript)

- **Design System**: Heaven Interface tokens (minimal, Rams/Ive-inspired)
- **State Management**: React Context + hooks
- **Visualization**: D3.js for commit graph, Recharts for metrics
- **Code Editor**: Monaco Editor (same as VS Code)

### Backend (Rust + Tauri)

- **IPC**: Tauri commands for state access
- **File System**: Read Solo Git state from `~/.sologit/state/`
- **Events**: Tauri event system for real-time updates

### State Synchronization

The GUI reads state from JSON files written by the CLI:

```
~/.sologit/state/
  ├── global.json           # Global state
  ├── repositories/         # Repository states
  ├── workpads/            # Workpad states
  ├── test_runs/           # Test run results
  ├── ai_operations/       # AI operation logs
  ├── commits/             # Commit graphs
  └── events/              # Event log
```

## Design Principles

1. **Minimalist**: Only essential UI elements, no clutter
2. **Keyboard-first**: Every action has a keyboard shortcut
3. **Fast**: <20MB binary, instant startup
4. **Additive**: CLI works standalone, GUI is optional
5. **Calm**: Subtle animations, muted colors, high contrast

## Keyboard Shortcuts

- `Cmd/Ctrl + P` - Command palette
- `Cmd/Ctrl + K` - Quick search
- `Cmd/Ctrl + G` - Show commit graph
- `Cmd/Ctrl + T` - Show tests
- `Cmd/Ctrl + /` - Toggle AI assistant
- `Cmd/Ctrl + B` - Toggle sidebar

## Components

### CommitGraph

Visual DAG with:
- Commit nodes (colored by status)
- Test indicators (✓/✗)
- CI status badges
- Hover for details

### TestDashboard

Metrics and trends:
- Pass/fail rates over time
- Average test duration
- Flaky test detection
- Test coverage (future)

### CodeViewer

Syntax-highlighted code:
- Monaco editor integration
- File browser
- Diff view for patches
- Jump to definition

### AI Assistant

Side pane for AI:
- Chat interface
- Operation history
- Cost tracking
- Model selection

## License

MIT
