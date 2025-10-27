# Solo Git CLI/TUI Quick Start Guide

## 🚀 Welcome to Solo Git!

Solo Git is a frictionless Git workflow for AI-augmented solo developers that eliminates branches, PRs, and manual reviews, replacing them with **ephemeral workpads** and **test-driven auto-merging**.

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

## 📝 Configuration

### Configuration File Location

```bash
~/.sologit/config.yaml
```

### Key Configuration Options

```yaml
abacus:
  endpoint: https://api.abacus.ai/api/v0
  api_key: your-api-key-here

models:
  planning: gpt-4o
  coding: deepseek-coder-33b
  fast: llama-3.1-8b-instruct

budget:
  daily_usd_cap: 10.0
  alert_threshold: 0.8
  track_by_model: true

workflow:
  auto_merge_on_green: true
  auto_rollback_on_red: true
  workpad_ttl_days: 7

paths:
  config_file: ~/.sologit/config.yaml
  repos_dir: ~/.sologit/repos
```

---

## 🐛 Troubleshooting

### CLI not found

```bash
# Make sure ~/.local/bin is in your PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Dependencies issues

```bash
# Reinstall Solo Git
cd /home/ubuntu/code_artifacts/solo-git
pip3 install -e .
```

### Check installation

```bash
# Verify Python version
python3 --version  # Should be 3.9+

# Check if evogitctl is in PATH
which evogitctl

# Test installation
evogitctl hello
```

---

## 📚 Additional Resources

### Documentation

- Full documentation: `docs/` directory
- API documentation: `docs/API.md`
- Heaven Interface: `HEAVEN_INTERFACE_*.md` reports

### Testing

```bash
# Run test suite
cd /home/ubuntu/code_artifacts/solo-git
pytest

# Run with coverage
pytest --cov=sologit --cov-report=html
```

### Development

```bash
# Install in development mode
pip3 install -e .

# Run tests
pytest

# Format code
black sologit/

# Lint
flake8 sologit/
```

---

## 🎯 Next Steps

1. ✅ **Installation Complete** - All dependencies are installed and working
2. 🔧 **Try the CLI** - Run `evogitctl hello` to get started
3. 🎨 **Launch Heaven TUI** - Run `evogitctl heaven` for the full interface
4. 📖 **Read the Docs** - Check out the documentation in `docs/`
5. 🤖 **Configure AI** - Set up your Abacus.ai API key with `evogitctl config setup`
6. 🚀 **Start Building** - Create your first repository and workpad!

---

## 🆘 Getting Help

### Command Help

```bash
# Get help for any command
evogitctl <command> --help

# Examples:
evogitctl pad --help
evogitctl ai --help
evogitctl config --help
```

### In TUI

- Press `?` to show help and keyboard shortcuts
- Press `Ctrl+P` to open command palette with fuzzy search

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🌟 Credits

Built with ❤️ by the Solo Git Team

Powered by:
- Abacus.ai (AI orchestration)
- Rich (beautiful CLI formatting)
- Textual (TUI framework)
- GitPython (Git operations)
- Native subprocess runner (sandboxed testing without containers)

---

**Happy Solo Coding! 🚀**

For questions, issues, or feature requests, please open an issue on GitHub.
