# Solo Git Project Structure

**Comprehensive Directory and File Organization Guide**

*Last Updated: October 17, 2025*

---

## Table of Contents

1. [Overview](#overview)
2. [Root Directory](#root-directory)
3. [Core Python Package](#core-python-package-sologit)
4. [Heaven GUI](#heaven-gui-heaven-gui)
5. [Tests](#tests-tests)
6. [Documentation](#documentation-docs)
7. [Configuration Files](#configuration-files)
8. [File Naming Conventions](#file-naming-conventions)
9. [Appendix: Retired Directories](#appendix-retired-directories)

---

## Overview

Solo Git follows a clean, modular structure with clear separation between:
- **Core Logic** (`sologit/`) - Python package with business logic
- **User Interfaces** (CLI/TUI in `sologit/ui/`, GUI in `heaven-gui/`)
- **Tests** (`tests/`, legacy suites in `tests_phase2/`)
- **Documentation** (`docs/`) - User guides, API docs, wiki
- **Supporting Assets** (`examples/`, `scripts/`, `jules-scratch/`)

### Quick Navigation

```
Solo-Git/
├── sologit/          → Core Python package
├── heaven-gui/       → Desktop GUI (Tauri + React)
├── docs/             → Documentation and wiki sources
├── tests/            → Active pytest suites
├── tests_phase2/     → Legacy regression suites
├── examples/         → Usage demos and reference scripts
├── scripts/          → Tooling and maintenance helpers
├── jules-scratch/    → Verification experiments
├── solo-git          → CLI entrypoint shim
└── [config files]    → Repository-level configuration (pyproject.toml, etc.)
```

---

## Root Directory

```
Solo-Git/
├── README.md                       # Main project documentation
├── PROJECT_STRUCTURE.md            # This file
├── ARCHITECTURE.md                 # System architecture guide
├── CHANGELOG.md                    # Version history
├── LICENSE                         # MIT license
│
├── requirements.txt                # Python dependencies
├── requirements-ci.txt             # CI dependency pinning
├── setup.py                        # Legacy packaging entry point
├── pyproject.toml                  # Modern Python build config
├── pytest.ini                      # Pytest configuration
├── MANIFEST.in                     # Source distribution manifest
│
├── solo-git                        # CLI entrypoint shim
├── check_all_syntax.py             # Tooling helpers
├── scripts/                        # Automation scripts
├── examples/                       # Demo programs
├── docs/                           # Documentation (guides, wiki)
├── heaven-gui/                     # Desktop GUI sources
├── jules-scratch/                  # Verification artifacts
├── sologit/                        # Core Python package
├── tests/                          # Active pytest suites
├── tests_phase2/                   # Legacy regression suites
│
├── current_coverage.json           # Latest test coverage data
├── test_run_output.txt             # Latest test execution log
│
├── QUICKSTART.md                   # Quick start guide
├── CLI_DEMO.txt                    # CLI demo transcript
├── CLI_INTEGRATION_SUMMARY.md      # CLI integration report
│
└── [Phase Reports]                 # Development phase summaries
    ├── PHASE_0_SUMMARY.txt
    ├── PHASE_0_VERIFICATION_REPORT.md
    ├── PHASE_1_100_PERCENT_COMPLETION_REPORT.md
    ├── PHASE_1_ENHANCEMENTS_SUMMARY.md
    ├── PHASE_1_VERIFICATION_REPORT.md
    ├── PHASE_2_COMPLETION_REPORT.md
    ├── PHASE_2_COVERAGE_IMPROVEMENT_REPORT.md
    ├── PHASE_2_ENHANCED_COVERAGE_REPORT.md
    ├── PHASE_2_SUMMARY.md
    ├── PHASE_3_ENHANCEMENT_REPORT.md
    ├── PHASE_3_FINAL_SUMMARY.md
    ├── PHASE_3_SUMMARY.md
    ├── PHASE_4_READINESS_REPORT.md
    ├── GIT_ENGINE_100_PERCENT_COMPLETE.md
    ├── HEAVEN_CLI_INTEGRATION_REPORT.md
    ├── HEAVEN_INTERFACE_90_PERCENT_COMPLETION_REPORT.md
    ├── HEAVEN_INTERFACE_97_PERCENT_COMPLETION_REPORT.md
    ├── HEAVEN_INTERFACE_AUDIT_SUMMARY.md
    ├── HEAVEN_INTERFACE_GAP_ANALYSIS.md
    ├── HEAVEN_INTERFACE_IMPLEMENTATION_SUMMARY.md
    ├── IMPLEMENTATION_COMPLETION_GUIDE.md
    ├── IMPLEMENTATION_SUMMARY.md
    ├── DEBUGGING_SUMMARY.md
    ├── TESTING_REPORT.md
    ├── TEST_COVERAGE_IMPROVEMENT_REPORT.md
    ├── PHASE3_COVERAGE_BASELINE_REPORT.md
    └── PHASE3_COVERAGE_IMPROVEMENT_REPORT.md
```

### Root Files Purpose

| File | Purpose |
|------|---------|
| `README.md` | Main documentation, quick start, feature overview |
| `ARCHITECTURE.md` | System design, components, data flow |
| `PROJECT_STRUCTURE.md` | This file - directory organization |
| `CHANGELOG.md` | Version history and release notes |
| `requirements.txt` | Python dependencies (pip format) |
| `setup.py` | Package installation and metadata |
| `pyproject.toml` | Modern Python build system config |
| `pytest.ini` | Pytest configuration (coverage, markers) |
| `current_coverage.json` | Latest test coverage metrics |
| `test_run_output.txt` | Latest test execution logs |

---

## Core Python Package (`sologit/`)

The main application package containing all business logic.

```
sologit/
├── __init__.py                     # Package initialization
│
├── cli/                            # Command-Line Interface
│   ├── __init__.py
│   ├── main.py                    # Entry point (evogitctl command)
│   ├── commands.py                # Core CLI commands (repo, pad, test)
│   ├── config_commands.py         # Config management commands
│   ├── integrated_commands.py     # AI pairing commands
│   └── enhanced_commands.py       # Advanced commands (TUI launcher)
│
├── ui/                             # Heaven Interface (CLI/TUI)
│   ├── __init__.py
│   ├── formatter.py               # Rich console formatting
│   ├── theme.py                   # Heaven design tokens
│   ├── heaven_tui.py              # Main TUI application
│   ├── tui_app.py                 # TUI widgets and layouts
│   ├── command_palette.py         # Fuzzy command search widget
│   ├── file_tree.py               # File browser widget
│   ├── graph.py                   # ASCII commit graph renderer
│   ├── test_runner.py             # Test results display widget
│   ├── autocomplete.py            # Shell autocomplete engine
│   └── history.py                 # Command history management
│
├── state/                          # State Management
│   ├── __init__.py
│   ├── manager.py                 # State persistence (JSON)
│   ├── schema.py                  # State data models
│   └── git_sync.py                # Git ↔ State synchronization
│
├── config/                         # Configuration
│   ├── __init__.py
│   ├── manager.py                 # Config loading and validation
│   └── templates.py               # Default config templates
│
├── api/                            # External API Clients
│   ├── __init__.py
│   └── client.py                  # Abacus.ai RouteLLM client
│
├── core/                           # Core Domain Models
│   ├── __init__.py
│   ├── repository.py              # Repository model
│   └── workpad.py                 # Workpad (ephemeral workspace) model
│
├── engines/                        # Execution Engines
│   ├── __init__.py
│   ├── git_engine.py              # Git operations wrapper
│   ├── patch_engine.py            # Patch generation and application
│   └── test_orchestrator.py      # Test execution and sandboxing
│
├── orchestration/                  # AI Orchestration
│   ├── __init__.py
│   ├── ai_orchestrator.py         # Main AI coordinator
│   ├── model_router.py            # Multi-model selection
│   ├── planning_engine.py         # High-level planning (GPT-4/Claude)
│   ├── code_generator.py          # Code generation (DeepSeek/CodeLlama)
│   └── cost_guard.py              # Budget tracking and enforcement
│
├── analysis/                       # Test Analysis
│   ├── __init__.py
│   └── test_analyzer.py           # Test failure diagnosis with AI
│
├── workflows/                      # Automated Workflows
│   ├── __init__.py
│   ├── auto_merge.py              # Auto-merge on green tests
│   ├── promotion_gate.py          # Promotion validation rules
│   ├── ci_orchestrator.py         # Jenkins/CI integration
│   └── rollback_handler.py        # Automatic rollback logic
│
└── utils/                          # Utilities
    ├── __init__.py
    └── logger.py                  # Structured logging
```

### Module Dependencies

```
┌─────────┐
│   CLI   │ ──────────────────────┐
└────┬────┘                       │
     │                            │
     ▼                            ▼
┌─────────┐                  ┌─────────┐
│   UI    │                  │  State  │
└────┬────┘                  └────┬────┘
     │                            │
     ▼                            ▼
┌─────────────────────────────────────┐
│         Core Components             │
│  ┌──────────┐  ┌──────────────┐    │
│  │  Engines │  │ Orchestration│    │
│  └──────────┘  └──────────────┘    │
│  ┌──────────┐  ┌──────────────┐    │
│  │Workflows │  │   Analysis   │    │
│  └──────────┘  └──────────────┘    │
└─────────────────────────────────────┘
         │
         ▼
┌──────────────────┐
│  External APIs   │
└──────────────────┘
```

### Key Files Detail

#### CLI Layer

**`cli/main.py`** - Entry point
```python
# Defines evogitctl command
# Sets up Click command groups
# Handles global options (--verbose, --config)
```

**`cli/commands.py`** - Core commands
```python
# Commands: repo, pad, test, promote, rollback
# Implementation: delegates to engines and workflows
```

**`cli/integrated_commands.py`** - AI pairing
```python
# Commands: pair, plan, code
# Integration: uses AI orchestration layer
```

#### UI Layer

**`ui/heaven_tui.py`** - Main TUI
```python
# Textual app with multiple screens
# Layouts: split panes, tabs, modals
# Bindings: vim-style keyboard shortcuts
```

**`ui/command_palette.py`** - Command palette
```python
# Fuzzy search over all commands
# Keyboard shortcut: Ctrl+P
# Shows recent and favorite commands
```

**`ui/graph.py`** - Commit graph
```python
# ASCII art commit graph
# Shows: commits, branches, merges, CI status
# Color-coded: green (success), red (failure)
```

#### State Layer

**`state/manager.py`** - State persistence
```python
# Load/save state to .sologit/state.json
# Thread-safe operations
# Change notifications for live updates
```

**`state/git_sync.py`** - Git synchronization
```python
# Sync state with Git repository
# Detect external Git changes
# Update state on Git operations
```

#### Engines

**`engines/git_engine.py`** - Git wrapper
```python
# Operations: commit, merge, rebase, checkout
# Constraint: Fast-forward merges only
# Safety: Validates before destructive operations
```

**`engines/patch_engine.py`** - Patch handling
```python
# Generate unified diffs from AI changes
# Apply patches with conflict detection
# Rollback support
```

**`engines/test_orchestrator.py`** - Test execution
```python
# Run tests in isolated sandboxes
# Parallel execution support
# Aggregate and report results
```

#### Orchestration

**`orchestration/ai_orchestrator.py`** - AI coordinator
```python
# Coordinates planning, coding, analysis
# Handles model selection
# Manages API requests
```

**`orchestration/model_router.py`** - Model selection
```python
# Routes tasks to optimal model tier
# Escalation rules (complexity, security)
# Fallback on failures
```

**`orchestration/cost_guard.py`** - Budget enforcement
```python
# Track spending per model
# Enforce daily budget caps
# Alert on thresholds
```

#### Workflows

**`workflows/auto_merge.py`** - Auto-merge
```python
# Test → Gate → Merge pipeline
# Configurable rules
# Event notifications
```

**`workflows/promotion_gate.py`** - Promotion validation
```python
# Required checks (tests, conflicts)
# Optional checks (coverage, linting)
# Manual override support
```

---

## Heaven GUI (`heaven-gui/`)

Desktop application built with Tauri (Rust) + React (TypeScript).

```
heaven-gui/
├── src/                            # React frontend
│   ├── App.tsx                    # Root component
│   ├── main.tsx                   # React entry point
│   │
│   ├── components/                # UI components
│   │   ├── CodeEditor.tsx         # Monaco editor wrapper
│   │   ├── CommandPalette.tsx     # Command search (Ctrl+P)
│   │   ├── CommitGraph.tsx        # D3.js visualization
│   │   ├── FileTree.tsx           # File browser with icons
│   │   ├── TestDashboard.tsx      # Test results with charts
│   │   ├── AIAssistant.tsx        # Chat interface
│   │   ├── StatusBar.tsx          # Bottom status bar
│   │   ├── SettingsPanel.tsx      # Configuration UI
│   │   ├── DiffViewer.tsx         # Side-by-side diff
│   │   └── NotificationToast.tsx  # Toast notifications
│   │
│   ├── hooks/                     # React hooks
│   │   ├── useStateSync.ts        # Sync with backend state
│   │   ├── useCommands.ts         # Execute backend commands
│   │   ├── useWebSocket.ts        # Live updates via WebSocket
│   │   ├── useTheme.ts            # Heaven theme management
│   │   └── useKeyboardShortcuts.ts # Global shortcuts
│   │
│   ├── services/                  # Business logic
│   │   ├── api.ts                 # Backend API client
│   │   ├── state.ts               # State management
│   │   ├── ipc.ts                 # Tauri IPC bridge
│   │   ├── git.ts                 # Git operations
│   │   └── websocket.ts           # WebSocket client
│   │
│   └── styles/                    # Styling
│       ├── theme.css              # Heaven design tokens
│       ├── components.css         # Component styles
│       └── layout.css             # Grid and layout
│
├── src-tauri/                      # Rust backend
│   ├── src/
│   │   ├── main.rs                # Tauri app setup
│   │   ├── commands.rs            # IPC command handlers
│   │   ├── state.rs               # State bridge to Python CLI
│   │   ├── events.rs              # Event emitter
│   │   └── menu.rs                # Application menu
│   │
│   ├── Cargo.toml                 # Rust dependencies
│   ├── tauri.conf.json            # Tauri configuration
│   └── build.rs                   # Build script
│
├── dist/                           # Production build output
│   ├── index.html
│   └── assets/
│
├── node_modules/                   # npm dependencies (large)
│
├── index.html                      # HTML entry point
├── package.json                    # npm dependencies and scripts
├── package-lock.json               # Dependency lock file
├── tsconfig.json                   # TypeScript config
├── tsconfig.node.json              # TypeScript config (Vite)
├── vite.config.ts                  # Vite bundler config
├── .gitignore                      # Git ignore
│
└── [Documentation]
    ├── README.md                   # GUI-specific README
    ├── BUILDING.md                 # Build instructions
    ├── DEVELOPMENT.md              # Development guide
    └── UX_AUDIT_REPORT.md          # UX audit findings
```

### Key Frontend Components

**CodeEditor.tsx**
- Monaco editor (VS Code editor)
- Syntax highlighting
- Code completion
- Diff mode support

**CommitGraph.tsx**
- D3.js force-directed graph
- Interactive (pan, zoom, click)
- Jenkins build status badges
- Color-coded by status

**CommandPalette.tsx**
- Fuzzy search (fuse.js)
- Keyboard shortcuts (Ctrl+P, Ctrl+K)
- Recent commands
- Quick actions

**TestDashboard.tsx**
- Test results table
- Coverage charts (Recharts)
- Failure analysis
- Historical trends

### Key Backend (Rust) Files

**main.rs**
```rust
// Tauri setup
// Window configuration
// System tray integration
```

**commands.rs**
```rust
// IPC commands exposed to frontend
// Examples:
// - execute_git_command()
// - get_repository_state()
// - run_tests()
// - call_ai_model()
```

**state.rs**
```rust
// Bridge to Python CLI
// Spawns evogitctl as subprocess
// Parses JSON state output
```

---

## Tests (`tests/`)

Comprehensive test suite with 555 tests and 76% coverage.

```
tests/
├── __init__.py
│
├── conftest.py                     # Pytest fixtures and configuration
│
├── [Core Tests]
│   ├── test_core.py               # Repository and Workpad tests
│   ├── test_core_100_percent.py   # Extended core tests
│   └── test_workpad_enhancements.py
│
├── [Engine Tests]
│   ├── test_git_engine.py         # Git operations tests
│   ├── test_git_engine_100_percent.py
│   ├── test_git_engine_extended.py
│   ├── test_patch_engine.py       # Patch application tests
│   ├── test_patch_engine_100_percent.py
│   ├── test_patch_engine_enhanced.py
│   ├── test_test_orchestrator_comprehensive.py
│   └── test_test_analyzer.py
│
├── [AI Orchestration Tests]
│   ├── test_ai_orchestrator.py
│   ├── test_ai_orchestrator_coverage.py
│   ├── test_ai_orchestrator_enhanced.py
│   ├── test_model_router.py
│   ├── test_model_router_coverage.py
│   ├── test_model_router_enhanced.py
│   ├── test_planning_engine.py
│   ├── test_planning_engine_coverage.py
│   ├── test_planning_engine_enhanced.py
│   ├── test_code_generator.py
│   ├── test_code_generator_coverage.py
│   ├── test_code_generator_enhanced.py
│   ├── test_cost_guard.py
│   ├── test_cost_guard_coverage.py
│   └── test_cost_guard_enhanced.py
│
├── [Workflow Tests]
│   ├── test_auto_merge_enhanced.py
│   ├── test_promotion_gate.py
│   ├── test_promotion_gate_coverage_boost.py
│   ├── test_promotion_gate_enhanced.py
│   ├── test_ci_orchestrator_enhanced.py
│   ├── test_ci_orchestrator_coverage_boost.py
│   ├── test_rollback_handler_comprehensive.py
│   ├── test_test_analyzer_coverage_boost.py
│   ├── test_phase3_workflows.py
│   └── test_phase3_enhanced_mocks.py
│
└── [E2E Tests]
    └── test_workflow_e2e.py       # End-to-end workflow tests
```

### Test Categories

| Category | Purpose | Count |
|----------|---------|-------|
| Core | Repository, Workpad models | 50+ |
| Engine | Git, Patch, Test engines | 100+ |
| AI | Orchestration, routing, cost | 150+ |
| Workflow | Auto-merge, CI, rollback | 100+ |
| E2E | Full workflow scenarios | 50+ |
| Analysis | Test analyzer | 50+ |

### Test Execution

```bash
# Run all tests
pytest tests/ -v

# Run specific category
pytest tests/test_core*.py -v
pytest tests/test_ai*.py -v
pytest tests/test_phase3*.py -v

# Run with coverage
pytest tests/ --cov=sologit --cov-report=html

# Run specific test
pytest tests/test_git_engine.py::test_fast_forward_merge -v
```

---

## Documentation (`docs/`)

Comprehensive documentation organized by topic.

```
docs/
├── wiki/                           # Documentation wiki
│   ├── Home.md                    # Wiki home page
│   ├── README.md                  # Wiki navigation
│   │
│   ├── architecture/              # Architecture docs
│   │   ├── core-components.md
│   │   └── git-engine.md
│   │
│   ├── guides/                    # User guides
│   │   ├── quick-start.md
│   │   ├── setup-guide.md
│   │   ├── cli-reference.md
│   │   ├── config-reference.md
│   │   └── phase3-usage-examples.md
│   │
│   ├── phases/                    # Phase completion reports
│   │   ├── phase-0-overview.md
│   │   ├── phase-0-completion.md
│   │   ├── phase-0-verification.md
│   │   ├── phase-1-overview.md
│   │   ├── phase-1-completion.md
│   │   ├── phase-1-enhancements.md
│   │   ├── phase-2-completion.md
│   │   ├── phase-2-enhanced-coverage.md
│   │   ├── phase-3-completion.md
│   │   └── phase-4-completion.md
│   │
│   └── timeline/                  # Project timeline
│       ├── 2025-10-16-vision.md
│       ├── 2025-10-16-concept.md
│       └── 2025-10-16-game-plan.md
│
├── examples/                       # Code examples
│
├── api/                            # API documentation
│
├── [Main Docs]
│   ├── API.md                     # Complete API reference
│   ├── SETUP.md                   # Installation guide
│   ├── SETUP_GUIDE.md             # Detailed setup
│   ├── HEAVEN_INTERFACE.md        # Design system spec
│   ├── HEAVEN_INTERFACE_GUIDE.md  # Implementation guide
│   ├── KEYBOARD_SHORTCUTS.md      # Keyboard reference
│   ├── TESTING_GUIDE.md           # Testing guide
│   ├── BETA_LAUNCH_CHECKLIST.md   # Beta launch tasks
│   ├── UX_AUDIT_REPORT.md         # UX audit findings
│   └── PHASE_4_COMPLETION_REPORT.md
```

### Documentation Categories

**User Guides**:
- Quick Start: Get running in 5 minutes
- Setup Guide: Detailed installation
- CLI Reference: All commands and options
- Config Reference: Configuration options

**Technical Docs**:
- API: Complete API documentation
- Architecture: System design (see ARCHITECTURE.md)
- Heaven Interface: UI design system
- Testing Guide: How to write and run tests

**Phase Reports**:
- Phase 0-4 completion reports
- Coverage improvement reports
- Enhancement summaries
- Verification reports

---

## Configuration Files

### Python Configuration

**`setup.py`**
```python
# Package metadata
# Dependencies
# Entry points (evogitctl command)
```

**`pyproject.toml`**
```toml
# Build system requirements
# Project metadata
# Tool configurations (black, isort, mypy)
```

**`pytest.ini`**
```ini
# Test discovery patterns
# Coverage settings
# Markers and options
```

**`requirements.txt`**
```
# Production dependencies
click>=8.0.0
textual>=0.40.0
rich>=13.0.0
pydantic>=2.0.0
requests>=2.31.0
# ... more
```

### GUI Configuration

**`package.json`**
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "typescript": "^5.2.0",
    "monaco-editor": "^0.44.0",
    "d3": "^7.8.0",
    "recharts": "^2.10.0"
  }
}
```

**`tauri.conf.json`**
```json
{
  "build": {
    "distDir": "../dist"
  },
  "tauri": {
    "allowlist": {
      "all": false,
      "shell": {
        "execute": true
      }
    }
  }
}
```

---

## File Naming Conventions

### Python Files

- **Snake case**: `file_name.py`
- **Test files**: `test_*.py` (pytest discovery)
- **Private modules**: `_internal.py` (single underscore)
- **Package markers**: `__init__.py`

### TypeScript/React Files

- **PascalCase** for components: `CodeEditor.tsx`
- **camelCase** for utilities: `apiClient.ts`
- **kebab-case** for CSS: `theme-tokens.css`

### Documentation

- **ALL CAPS** for major docs: `README.md`, `LICENSE`
- **Snake case** for guides: `setup_guide.md`
- **Hyphens** for multi-word: `cli-reference.md`

### Configuration

- **Lowercase** with extensions: `pytest.ini`, `setup.py`
- **Dotfiles**: `.gitignore`, `.env`

---

## File Metadata

### File Sizes (Approximate)

| Category | Files | Total Size |
|----------|-------|------------|
| Python Source | 100+ | ~500 KB |
| Tests | 40+ | ~400 KB |
| Documentation | 80+ | ~2 MB |
| Heaven GUI (src) | 50+ | ~200 KB |
| node_modules | 5000+ | ~200 MB |
| Git History | - | ~50 MB |

### Critical Files

Files that should **never** be deleted:

1. `README.md` - Main documentation
2. `setup.py` - Package installation
3. `requirements.txt` - Dependencies
4. `sologit/cli/main.py` - CLI entry point
5. `sologit/core/repository.py` - Core model
6. `pytest.ini` - Test configuration
7. `.gitignore` - Git ignore rules
8. `LICENSE` - Legal license

---

## Summary

**Total Structure**:
- **Python Modules**: 30+ modules
- **Test Files**: 40+ test files
- **UI Components**: 15+ React components
- **Documentation**: 80+ markdown files
- **Configuration Files**: 10+ config files

**Key Directories**:
1. `sologit/` - Core application (500 KB)
2. `heaven-gui/` - Desktop GUI (200 MB with deps)
3. `tests/` - Test suite (400 KB)
4. `docs/` - Documentation (2 MB)

**Cleaned Up**:
- ✅ Removed 63 duplicate PDF files
- ✅ Archived historical coverage reports
- ✅ Removed Python bytecode files
- ✅ Organized phase reports
- ✅ No tar.gz archives

---

## Appendix: Retired Directories

Two historical directories referenced in earlier documentation are no longer part of the tracked tree. They remain documented here so future contributors understand why they are absent.

- **`infrastructure/`** – Jenkins and sandbox assets were removed during the Phase 4 cleanup in favor of per-environment automation owned by downstream deployments. Reintroduce the folder only if new CI/CD assets are committed; mirror the former `jenkins/` and `sandbox/` layout if that happens.
- **`data/`** – Runtime repositories and logs now live outside the Git tree (e.g., under `~/.sologit/`). Keep working copies out of version control; if local fixtures are required, create them under `tests/fixtures/` instead of reviving `data/`.

These directories should **not** be recreated unless there is an intentional decision to version infrastructure or runtime payloads.

---

## Maintenance Notes

### Regular Cleanup

```bash
# Remove Python bytecode
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# Remove temporary files
rm -rf .pytest_cache/
rm -rf htmlcov/
rm -f .coverage

# Update documentation dates
# Update test coverage numbers
# Archive old phase reports
```

### Adding New Components

**New Python Module**:
1. Create in appropriate `sologit/` subdirectory
2. Add `__init__.py` if new package
3. Write tests in `tests/test_[module].py`
4. Update `ARCHITECTURE.md` if significant

**New React Component**:
1. Create in `heaven-gui/src/components/`
2. Export from `components/index.ts`
3. Add to storybook if available
4. Document props with TypeScript

**New Documentation**:
1. Create in `docs/` or `docs/wiki/`
2. Link from `README.md` or `docs/wiki/Home.md`
3. Follow markdown style guide
4. Add to table of contents

---

## Version History

- **v0.1.0** (Phase 0): Initial structure
- **v0.2.0** (Phase 1): Git engine and workpads
- **v0.3.0** (Phase 2): AI orchestration
- **v0.4.0** (Phase 3): Workflows and auto-merge
- **v0.4.5** (Phase 4): Heaven Interface + cleanup

---

## See Also

- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [README.md](README.md) - Main documentation
- [docs/SETUP.md](docs/SETUP.md) - Installation guide
- [docs/API.md](docs/API.md) - API reference
