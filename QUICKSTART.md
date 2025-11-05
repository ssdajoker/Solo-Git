# Solo Git Quick Start

**This guide will walk you through setting up a project and completing your first AI-powered development task in just a few minutes.**
## 🚀 Welcome to Solo Git!

Solo Git is a frictionless Git workflow for AI-augmented solo developers that eliminates branches, PRs, and manual reviews, replacing them with **ephemeral workpads** and **test-driven auto-merging**.

For the current Heaven Interface status and deliverables, review the [Heaven Interface Implementation Summary](HEAVEN_INTERFACE_IMPLEMENTATION_SUMMARY.md).

### Philosophy
- ✅ **Tests are the review** - Green tests = instant merge
- 🎯 **Single trunk, no PRs** - No branch management overhead
- 🔧 **Ephemeral workpads** - Disposable sandboxes instead of long-lived branches
- 🤖 **AI-powered** - Pair programming with GPT-4, DeepSeek, and more

---

## 📋 Installation Status

✅ **All dependencies installed successfully!**
- Python 3.11.6
- All required packages (Rich, Textual, GitPython, etc.)
- CLI entry point: `evogitctl` (available in PATH)

### 🚫 Container Policy

Solo Git refuses to bundle container tooling. The CLI and TUI expect direct subprocess
execution, keeping the workflow lean and explicitly rejecting container overhead.

---

## 🎯 Quick Start Commands

### 1. Verify Installation

```bash
# Check version
evogitctl --version

# Test Solo Git
evogitctl hello

# Show current configuration
evogitctl config show
```

### 2. Initialize a Repository

```bash
# From a ZIP file
evogitctl repo init --name my-project --zip project.zip

# From a Git URL (coming soon)
evogitctl repo init --name my-project --git https://github.com/user/repo.git

# List all repositories
evogitctl repo list

# Show repository info
evogitctl repo info <repo_id>
```

### 3. Create a Workpad (Ephemeral Branch)

```bash
# Create a new workpad for a feature
evogitctl pad create --repo <repo_id> "add-login-feature"

# List all workpads
evogitctl pad list --repo <repo_id>

# Show workpad info
evogitctl pad info <pad_id>

# Show diff between workpad and trunk
evogitctl pad diff <pad_id>
```

### 4. Run Tests

```bash
# Run tests in workpad
evogitctl test run --pad <pad_id>

# Auto-merge if tests pass
evogitctl pad auto-merge <pad_id>

# Evaluate promotion gate without promoting
evogitctl pad evaluate <pad_id>
```

### 5. Promote to Trunk

```bash
# Promote workpad to trunk (fast-forward merge)
evogitctl pad promote <pad_id>
```

### 6. AI-Powered Operations

```bash
# Start AI pair programming session
evogitctl pair "add passwordless login feature"

# AI code generation
evogitctl ai generate --pad <pad_id> "create user authentication module"

# AI code review
evogitctl ai review --pad <pad_id>

# AI test generation
evogitctl ai test-gen --pad <pad_id> --file main.py

# AI refactoring
evogitctl ai refactor --pad <pad_id> --file main.py "extract helper functions"

# AI commit message
evogitctl ai commit-message --pad <pad_id>

# Check AI status
evogitctl ai status
```

### 7. History & Logs

```bash
# View commit history
evogitctl history log --repo <repo_id> --limit 10

# Revert last commit
evogitctl history revert --repo <repo_id>
```

### 8. Configuration Management

```bash
# Show configuration
evogitctl config show

# Show configuration file path
evogitctl config path

# Test API connection
evogitctl config test

# Setup configuration wizard
evogitctl config setup

# Initialize new config file
evogitctl config init

# Generate .env template
evogitctl config env-template
```

---

## 🎨 Launch Heaven Interface (TUI)

### Production Heaven Interface

```bash
# Launch the comprehensive TUI
evogitctl heaven

# Launch with specific repository
evogitctl heaven --repo <repo_path>
```

### Key Features of Heaven TUI

✨ **90%+ Integration Complete:**
- Command palette with fuzzy search (Ctrl+P)
- File tree with git status
- Real-time commit graph visualization
- Live workpad status updates
- Real-time test output streaming
- AI operation tracking with cost monitoring
- Command history with undo/redo
- Full keyboard navigation

### Essential Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+P` | Open command palette |
| `Ctrl+T` | Run tests |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |
| `?` | Show help (full shortcuts) |
| `R` | Refresh |
| `Ctrl+Q` | Quit |

### Heaven Interface Layout

```
┌────────────────────────────────────────────────────────┐
│                    HEADER / STATUS                      │
├──────────┬─────────────────────────┬───────────────────┤
│          │                         │                   │
│ Commit   │  Workpad Status         │  Test Runner      │
│ Graph    │  + AI Activity          │  + Diff Viewer    │
│  +       │                         │                   │
│ File     │                         │                   │
│ Tree     │                         │                   │
│          │                         │                   │
├──────────┴─────────────────────────┴───────────────────┤
│                    STATUS BAR                           │
│  📦 repo  │ 🔧 workpad │ ○ Tests │ ↶ Undo │ Ctrl+P     │
└────────────────────────────────────────────────────────┘
```

---

## 🔧 Interactive Shell

```bash
# Launch interactive shell with autocomplete
evogitctl interactive
```

Features:
- Tab completion for all commands
- Command history
- Syntax highlighting
- Persistent session

---

## 🧪 Example Workflow

### Complete Solo Git Workflow Example

```bash
# 1. Create a test project
mkdir my-app
cd my-app
echo "print('Hello World')" > main.py
echo "def test_hello(): assert True" > test_main.py
zip -r ../my-app.zip .

# 2. Initialize with Solo Git
cd ..
evogitctl repo init --name my-app --zip my-app.zip

# Output: ✅ Repository initialized!
#         Repo ID: repo_abc123
#         Path: ~/.sologit/data/repos/repo_abc123

# 3. Create a workpad for new feature
evogitctl pad create --repo repo_abc123 "add-greeting-feature"

# Output: ✅ Workpad created!
#         Pad ID: pad_xyz789
#         Branch: pads/add-greeting-feature-20251017-171013

# 4. List workpads
evogitctl pad list --repo repo_abc123

# 5. View workpad info
evogitctl pad info pad_xyz789

# 6. Make changes in the workpad
# (Edit files in ~/.sologit/data/repos/repo_abc123)

# 7. Show diff
evogitctl pad diff pad_xyz789

# 8. Run tests
evogitctl test run --pad pad_xyz789

# 9. Auto-merge if tests pass
evogitctl pad auto-merge pad_xyz789

# Output: ✅ Tests passed! Auto-promoting to trunk...
#         ✅ Workpad promoted to trunk

# 10. View history
evogitctl history log --repo repo_abc123
```

---

## 🎯 Common Use Cases

### 1. Quick Feature Development

```bash
# Create workpad
evogitctl pad create --repo <repo_id> "feature-name"

# Let AI generate code
evogitctl ai generate --pad <pad_id> "implement user login"

# Review changes
evogitctl pad diff <pad_id>

# Run tests and auto-merge
evogitctl pad auto-merge <pad_id>
```

### 2. AI-Assisted Refactoring

```bash
# Create workpad
evogitctl pad create --repo <repo_id> "refactor-auth"

# AI refactoring
evogitctl ai refactor --pad <pad_id> --file auth.py "extract database logic"

# Review and test
evogitctl pad diff <pad_id>
evogitctl test run --pad <pad_id>

# Promote if tests pass
evogitctl pad promote <pad_id>
```

### 3. Test Generation

```bash
# Create workpad
evogitctl pad create --repo <repo_id> "add-tests"

# Generate tests for a file
evogitctl ai test-gen --pad <pad_id> --file main.py

# Run new tests
evogitctl test run --pad <pad_id>

# Merge if tests pass
evogitctl pad auto-merge <pad_id>
```

---

## 1. Prerequisites

Before you start, make sure you have:

- ✅ **Python 3.9+** and **Git 2.30+** installed.
- ✅ An **Abacus.ai API key**.
- ✅ Solo Git installed and configured. If you haven't done this yet, please follow the **[Setup Guide](docs/SETUP.md)**.

---

## 2. Initialize Your Repository

First, we'll import your project into Solo Git. This creates a new, managed repository in the Solo Git environment.

```bash
# Initialize from a .zip file
evogitctl repo init --zip /path/to/your/project.zip --name "My First Project"
```

This command will output a `Repo ID`. **Copy this ID for the next step.**

---

## 3. Create a Workpad

In Solo Git, you don't use traditional branches. Instead, you create **workpads**—ephemeral, disposable sandboxes where the AI will do its work.

```bash
# Create a new workpad
evogitctl pad create "Implement user authentication" --repo <your-repo-id>
```

Replace `<your-repo-id>` with the ID from the previous step. This command will output a `Pad ID`. **Copy this ID as well.**

---

## 4. The AI Pair Programming Loop

Now, it's time to give the AI a task. The `pair` command is the core of the Solo Git experience.

```bash
# Instruct the AI to make a change
evogitctl pair "Add a new endpoint for user login" --pad <your-pad-id>
```

Replace `<your-pad-id>` with the ID from the previous step. Solo Git will now:

1.  **🧠 Plan**: Analyze your request and the codebase to create a plan.
2.  **✍️ Code**: Generate the necessary code changes.
3.  **🧪 Test**: Run your project's test suite to verify the changes.
4.  **✅ Promote**: If all tests pass, automatically merge the changes into your trunk.

---

## 5. You're Done!

Congratulations! You've successfully completed your first AI-powered development task with Solo Git. The changes are now in your `main` branch.
