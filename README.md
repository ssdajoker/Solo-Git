# Solo Git

**Frictionless AI-Powered Development for the Solo Developer**

> *"Tests are the review. Trunk is king. Workpads are ephemeral."*

[![Python 3.9+](https://upload.wikimedia.org/wikipedia/commons/thumb/1/1b/Blue_Python_3.9_Shield_Badge.svg/1200px-Blue_Python_3.9_Shield_Badge.svg.png)
[![License: MIT](https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/License_icon-mit.svg/256px-License_icon-mit.svg.png)
[![Status: Beta](https://i.ytimg.com/vi/4cgpu9L2AE8/hq720.jpg?sqp=-oaymwEhCK4FEIIDSFryq4qpAxMIARUAAAAAGAElAADIQj0AgKJD&rs=AOn4CLCzedb-c7IZSg8ZCib1APCJvLdWqw)

---

## What is Solo Git?

**Solo Git** is a revolutionary version control system designed specifically for solo developers working with AI assistants. It eliminates the friction of traditional Git workflows (branches, PRs, manual reviews) and replaces them with an intelligent, test-driven, auto-merging system where **tests are the ultimate arbiter of correctness**.

### The Problem

Traditional Git workflows are optimized for teams:
- **Branches** require constant naming, switching, and mental overhead
- **Pull Requests** assume human reviewers (often yourself)
- **Merge conflicts** disrupt flow and waste precious time
- **CI/CD** runs too late to prevent broken commits

For solo developers working with AI, these patterns create friction without adding value.

### The Solution

Solo Git introduces three core innovations:

1. **Ephemeral Workpads** - Disposable, auto-named sandboxes that replace branches
2. **Tests as Review** - Automated testing replaces human code review
3. **Instant Auto-Merge** - Green tests trigger immediate trunk promotion

---

## Key Features

### 🎨 **Heaven Interface** - Minimalist Design System
Heaven is Solo Git's minimalist, code-first interface inspired by Jony Ive and Dieter Rams design principles ("as little design as possible"). Available in three modes:

- **Enhanced CLI**: Rich formatting with colors, panels, and ASCII commit graphs using Python Rich library
- **Interactive TUI**: Full-screen terminal interface built with Textual - keyboard-driven with live updates, command palette, file tree, and visual commit graph
- **Desktop GUI**: Tauri-based companion app (Rust + React) featuring:
  - Monaco code editor (center stage)
  - Retractable side rails (left: file/commit tree, right: AI assistant, bottom: logs/tests)
  - D3.js commit graph visualization with Jenkins build status indicators
  - 5 engagement levels (Idle → Navigation → Planning → Coding/Test → Commit/Resolve)
  - Dark theme with minimal accent colors (#61AFEF blue, #98C379 green, #E06C75 red)
  - JSON-based state synchronization between CLI/TUI/GUI
  - **Read-only interactions today**: the GUI is currently limited to viewing repository state; write operations must be performed through the CLI or TUI interfaces.

**Design Tokens**:
- Typography: JetBrains Mono/SF Mono for code, SF Pro/Roboto for UI
- Color: Dark base (#1E1E1E), light text (#DDD), 2-3 accent colors only
- Spacing: 8px grid system, generous margins (16-24px)
- Icons: Monoline 2px stroke, 24×24px, monochrome
- Motion: Subtle 150-300ms animations with ease-in-out

See the [Heaven Interface Design System](docs/HEAVEN_INTERFACE.md) and [Heaven Interface Guide](docs/HEAVEN_INTERFACE_GUIDE.md) for complete specifications

### ✨ **Frictionless Workflow**
- **No Branch Management**: Say goodbye to `git checkout -b feature/...`
- **No Pull Requests**: Tests replace human review
- **No Merge Conflicts**: Fast-forward merges only
- **Auto-Merge on Green**: Code ships the moment tests pass

### 🤖 **AI-Native Design**
- **Multi-Model Intelligence**: Automatically selects optimal AI model for each task
- **Cloud-Powered**: 100% Abacus.ai RouteLLM API - no local model hosting
- **Smart Escalation**: Simple edits use fast models, complex logic uses GPT-4/Claude
- **Cost Controls**: Daily budgets, per-model tracking, automatic alerts

### 🧪 **Test-Driven Safety**
- **Isolated Sandboxes**: Every test runs in a clean subprocess
- **Parallel Execution**: Fast tests run simultaneously
- **Intelligent Analysis**: AI diagnoses failures and suggests fixes
- **CI Integration**: Optional Jenkins/GitHub Actions for post-merge smoke tests

## Zero Tolerance for Container Tooling

Solo Git proudly enforces a no-container policy. Historical container workflows were
excised, and we now rely exclusively on native subprocess execution. Container stacks
are considered needless complexity for a solo developer and are intentionally shunned
throughout the codebase and documentation.

### 🎯 **Production Ready**
- **73% Test Coverage**: 562 of 581 tests passing (96.6% pass rate)
- **Battle-Tested**: Phases 0-4 complete and verified
- **Comprehensive Docs**: Setup guides, API reference, wiki
- **Active Development**: Phase 5 scoping and roadmap planning

---

## Quick Start

### Prerequisites

- **Python 3.9+**
- **Git 2.30+**
- **Abacus.ai API Account** ([Sign up here](https://abacus.ai))

### Installation

```bash
# Install from source
git clone https://github.com/yourusername/solo-git.git
cd solo-git
pip install -e .

# Verify installation
evogitctl --version
```

### Configuration

```bash
# Interactive setup (recommended)
evogitctl config setup

# Or set environment variables
export ABACUS_API_ENDPOINT=https://api.abacus.ai/v1
export ABACUS_API_KEY=your-api-key-here
```

### Your First Project

```bash
# Initialize repository from zip
evogitctl repo init --zip myproject.zip

# Create a workpad
evogitctl pad create "add-auth-feature"

# Run tests
evogitctl test run --target fast

# Tests passed? Auto-promoted to trunk! ✅
```

---

## The Pair Loop

**The core Solo Git experience:**

```
You: "Add Redis caching to search endpoint with 5-minute TTL"

Solo Git:
  1. 🧠 Plans changes (GPT-4/Claude)        →  4 seconds
  2. ✍️  Generates patches (DeepSeek Coder) → 10 seconds  
  3. 🧪 Runs tests in sandbox              → 20 seconds
  4. ✅ Auto-merges to trunk                →  1 second
  ─────────────────────────────────────────────────────
  Total: Under 1 minute, from idea to production!
```

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────┐
│                  Solo Git Core                       │
├─────────────────────────────────────────────────────┤
│                                                      │
│  Git Engine        ←  Workpads, patches, merges     │
│  Test Orchestrator ←  Sandboxed test execution      │
│  AI Orchestrator   ←  Multi-model routing           │
│  Auto-Merge        ←  Test-gated promotion          │
│                                                      │
└──────────────┬──────────────────────┬────────────────┘
               │                      │
               ▼                      ▼
    ┌──────────────────┐    ┌──────────────────┐
    │  Abacus.ai API   │    │  Optional CI/CD  │
    │  RouteLLM        │    │  Jenkins/Actions │
    │                  │    │                  │
    │ • GPT-4          │    │ • Smoke Tests    │
    │ • Claude 3.5     │    │ • Auto-Rollback  │
    │ • DeepSeek       │    │                  │
    │ • Llama 70B/8B   │    └──────────────────┘
    └──────────────────┘
```

### Three-Tier Model Selection

**All through Abacus.ai RouteLLM API** - one endpoint, multiple world-class models:

| Tier | Models | Use Cases | Speed | Cost |
|------|--------|-----------|-------|------|
| **Planning** | GPT-4, Claude 3.5 Sonnet | Architecture, complex logic, failure diagnosis | Slower | Higher |
| **Coding** | DeepSeek-Coder, CodeLlama | Patch generation, refactoring, standard tasks | Medium | Medium |
| **Fast** | Llama 3.1 8B, Gemma 2 9B | Simple edits, boilerplate, documentation | Fast | Low |

**Smart Escalation**: The system automatically routes tasks to the optimal model based on:
- Code complexity
- Security sensitivity (auth, crypto keywords)
- Test failure history
- Budget constraints
- Patch size estimates

---

## Core Concepts

### Workpads (Not Branches)

**Traditional Git:**
```bash
git checkout -b feature/add-login
# Do work...
git add . && git commit -m "Add login"
git checkout main
git merge feature/add-login
git branch -d feature/add-login
```

**Solo Git:**
```bash
evogitctl pad create "add-login"
# Work happens automatically via AI
# Tests pass → merged already! 🎉
```

**Mental Model**: Workpads are scratch paper. Use them freely, they disappear when done.

### Tests as Review

**Traditional:** Code → Human Review → Merge  
**Solo Git:** Code → Test Suite → Auto-Merge (if green)

```
┌─────────────┐
│   AI Code   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Run Tests  │
└──────┬──────┘
       │
   ┌───┴───┐
   │       │
   ▼       ▼
┌──────┐ ┌──────┐
│GREEN │ │ RED  │
│AUTO  │ │KEEP  │
│MERGE │ │PAD   │
└──────┘ └──────┘
```

### Fast-Forward Only Merges

**Solo Git never creates merge commits**. All promotions are fast-forward merges, keeping history linear and clean.

**Benefits:**
- Clean, readable history
- No merge commit noise
- Easy rollbacks
- Clear causality

---

## Configuration

### Basic Setup

Create `~/.sologit/config.yaml`:

```yaml
# Abacus.ai RouteLLM API (all AI operations)
abacus:
  endpoint: https://api.abacus.ai/v1
  api_key: ${ABACUS_API_KEY}  # Or hardcode (not recommended)

# Model selection by task type
models:
  # Planning models - deep reasoning
  planning_model: gpt-4o
  planning_fallback: claude-3-5-sonnet
  planning_temperature: 0.2
  planning_max_tokens: 4096
  
  # Coding models - specialized generation
  coding_model: deepseek-coder-33b
  coding_fallback: codellama-70b-instruct
  coding_temperature: 0.1
  coding_max_tokens: 2048
  
  # Fast models - quick operations
  fast_model: llama-3.1-8b-instruct
  fast_fallback: gemma-2-9b-it
  fast_temperature: 0.1
  fast_max_tokens: 1024

# Budget controls
budget:
  daily_usd_cap: 10.0           # Maximum daily spend
  alert_threshold: 0.80         # Alert at 80%
  track_by_model: true          # Track costs per model

# Workflow settings
promote_on_green: true          # Auto-merge when tests pass
rollback_on_ci_red: true        # Auto-rollback on CI failure
workpad_ttl_days: 7             # Workpad retention period

# Test configuration
tests:
  fast:
    - name: unit-tests
      cmd: pytest tests/unit --quiet
      timeout: 30
    - name: integration-tests
      cmd: pytest tests/integration --quiet
      timeout: 60
  
  full:
    - name: e2e-tests
      cmd: npm run test:e2e
      timeout: 180
    - name: security-scan
      cmd: trivy fs --severity HIGH,CRITICAL .
      timeout: 120

# Escalation rules
escalation:
  triggers:
    - patch_lines > 200          # Large changes → planning model
    - test_failures >= 2         # Repeated failures → smarter model
    - security_keywords:         # Security code → planning model
        - auth
        - crypto
        - password
        - token
        - jwt
    - complexity_score > 0.7     # Complex code → planning model
```

---

## CLI Reference

### Core Commands

```bash
# Configuration
evogitctl config setup              # Interactive setup
evogitctl config show               # Display config
evogitctl config test               # Test API connection

# Repository Management
evogitctl repo init --zip app.zip   # Initialize from zip
evogitctl repo init --git <url>     # Initialize from Git URL
evogitctl repo list                 # List repositories
evogitctl repo info <repo-id>       # Show repo details

# Workpad Lifecycle
evogitctl pad create <title>        # Create workpad
evogitctl pad list                  # List workpads
evogitctl pad info <pad-id>         # Show workpad details
evogitctl pad promote <pad-id>      # Promote to trunk
evogitctl pad delete <pad-id>       # Delete workpad

# Testing
evogitctl test run --pad <id>       # Run tests
evogitctl test run --target full    # Run full test suite
evogitctl test config               # Show test config

# AI Pairing (Phase 2)
evogitctl pair "<prompt>"           # AI pair programming
evogitctl pair --model planning     # Force model tier

# Workflows (Phase 3)
evogitctl auto-merge run            # Run auto-merge workflow
evogitctl auto-merge status         # Check workflow status
evogitctl promote                   # Gate-checked promotion
evogitctl rollback --last           # Rollback last commit

# CI/CD Integration (Phase 3)
evogitctl ci smoke                  # Run smoke tests
evogitctl ci status                 # CI job status

# Heaven Interface (Phase 4)
evogitctl tui                       # Launch interactive TUI
evogitctl interactive               # Launch autocomplete shell

# Utilities
evogitctl version                   # Show version info
evogitctl hello                     # Verify installation
```

### Global Options

```bash
evogitctl -v <command>              # Verbose output
evogitctl --config <path> <command> # Custom config file
evogitctl --help                    # Show help
```

---

## Project Status

<a id="project-status-widget"></a>

### 📊 Project Status Widget

| Phase | Status | Completion Date | Focus |
|-------|--------|-----------------|-------|
| **Phase 0** | ✅ Complete | October 16, 2025 | Foundation, config, API client |
| **Phase 1** | ✅ Complete | October 17, 2025 | Git engine, workpads, tests |
| **Phase 2** | ✅ Complete | October 17, 2025 | AI integration, multi-model routing |
| **Phase 3** | ✅ Complete | October 17, 2025 | Auto-merge, CI/CD, rollback |
| **Phase 4** | ✅ Complete | October 17, 2025 | Documentation, polish, beta prep |
| **Phase 5** | ⏳ Planned | TBA | Advanced features, ecosystem |

### Test Coverage

```
Overall Coverage:    73%
Core Components:     90%+
Total Tests:         562 passing (of 581)
Test Suites:         32 suites
```

### Current Capabilities

- ✅ Repository initialization (ZIP/Git)
- ✅ Workpad lifecycle management
- ✅ Patch application with conflict detection
- ✅ Test orchestration with sandboxing
- ✅ Multi-model AI integration
- ✅ Cost tracking and budgets
- ✅ Auto-merge on green tests
- ✅ CI smoke tests with rollback
- ✅ Intelligent test failure analysis
- ✅ Configurable promotion gates
- ⏳ Desktop UI (planned)
- ⏳ Advanced metrics dashboard (planned)

---

## Documentation

### Quick Links

- **[Setup Guide](docs/SETUP.md)** - Installation and configuration
- **[API Documentation](docs/API.md)** - Complete API reference
- **[CLI Reference](docs/wiki/guides/cli-reference.md)** - All commands
- **[Configuration Guide](docs/wiki/guides/config-reference.md)** - Config options
- **[Wiki Home](docs/wiki/Home.md)** - Complete documentation hub

### Phase Completion Reports

- [Phase 0 Completion](docs/PHASE_0_COMPLETE.md)
- [Phase 1 Completion](docs/wiki/phases/phase-1-completion.md)
- [Phase 2 Completion](docs/wiki/phases/phase-2-completion.md)
- [Phase 3 Completion](docs/wiki/phases/phase-3-completion.md)
- [Phase 4 Completion Report](docs/PHASE_4_COMPLETION_REPORT.md)

---

## Development

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific phase tests
pytest tests/test_git_engine*.py -v
pytest tests/test_ai_orchestrator*.py -v
pytest tests/test_phase3*.py -v

# Run with coverage
pytest tests/ --cov=sologit --cov-report=html
```

### Code Quality

```bash
# Format code
black sologit/ tests/

# Sort imports
isort sologit/ tests/

# Type checking
mypy sologit/

# Linting
flake8 sologit/
```

### Project Structure

```
solo-git/
├── sologit/                    # Main Python package
│   ├── cli/                    # CLI commands (evogitctl)
│   │   ├── main.py            # Entry point
│   │   ├── commands.py        # Core commands
│   │   ├── config_commands.py # Config management
│   │   └── integrated_commands.py # AI pairing commands
│   ├── ui/                     # Heaven Interface (CLI/TUI)
│   │   ├── formatter.py       # Rich formatting
│   │   ├── heaven_tui.py      # Main TUI app
│   │   ├── tui_app.py         # TUI components
│   │   ├── command_palette.py # Command palette widget
│   │   ├── file_tree.py       # File browser
│   │   ├── graph.py           # Commit graph ASCII renderer
│   │   ├── test_runner.py     # Test results display
│   │   ├── theme.py           # Heaven theme tokens
│   │   ├── autocomplete.py    # Shell autocomplete
│   │   └── history.py         # Command history
│   ├── state/                  # State management
│   │   ├── manager.py         # State manager
│   │   ├── schema.py          # State schema
│   │   └── git_sync.py        # Git ↔ State sync
│   ├── config/                 # Configuration management
│   ├── api/                    # API clients (Abacus.ai)
│   ├── core/                   # Core models (Repository, Workpad)
│   ├── engines/                # Git, Patch, Test engines
│   ├── orchestration/          # AI orchestration (multi-model)
│   ├── analysis/               # Test analysis
│   ├── workflows/              # Auto-merge, CI, rollback
│   └── utils/                  # Utilities and logging
│
├── heaven-gui/                 # Desktop GUI (Tauri + React)
│   ├── src/                    # React frontend
│   │   ├── components/        # UI components
│   │   │   ├── CodeEditor.tsx # Monaco editor wrapper
│   │   │   ├── CommandPalette.tsx
│   │   │   ├── CommitGraph.tsx # D3.js visualization
│   │   │   ├── FileTree.tsx
│   │   │   ├── TestDashboard.tsx
│   │   │   └── AIAssistant.tsx
│   │   ├── hooks/             # React hooks
│   │   ├── services/          # API clients
│   │   ├── styles/            # CSS/design tokens
│   │   └── App.tsx
│   ├── src-tauri/             # Rust backend
│   │   ├── src/
│   │   │   ├── main.rs        # Tauri setup
│   │   │   ├── state.rs       # State bridge
│   │   │   └── commands.rs    # Tauri commands
│   │   └── Cargo.toml
│   ├── package.json
│   └── vite.config.ts
│
├── tests/                      # Test suite (555 tests, 76% coverage)
│   ├── test_core*.py          # Core component tests
│   ├── test_*_engine*.py      # Engine tests
│   ├── test_ai_*.py           # AI orchestration tests
│   ├── test_phase*.py         # Phase workflow tests
│   └── test_workflow_e2e.py   # End-to-end tests
│
├── docs/                       # Documentation
│   ├── wiki/                   # Comprehensive wiki
│   │   ├── architecture/      # Architecture docs
│   │   ├── guides/            # User guides
│   │   ├── phases/            # Phase reports
│   │   └── timeline/          # Project timeline
│   ├── SETUP.md               # Setup guide
│   ├── API.md                 # API reference
│   ├── HEAVEN_INTERFACE.md    # Design system spec
│   ├── HEAVEN_INTERFACE_GUIDE.md # Implementation guide
│   ├── KEYBOARD_SHORTCUTS.md  # Keyboard reference
│   ├── TESTING_GUIDE.md       # Testing guide
│   └── BETA_LAUNCH_CHECKLIST.md
│
├── infrastructure/             # Deployment configs
│   ├── docker/                # Docker images
│   ├── jenkins/               # Jenkins pipelines
│   └── sandbox/               # Test sandbox configs
│
├── .archive/                   # Historical artifacts
│   └── historical_coverage/   # Old coverage reports
│
├── data/                       # Runtime data
│   ├── repos/                 # Repository storage
│   └── logs/                  # Application logs
│
├── requirements.txt            # Python dependencies
├── setup.py                   # Package setup
├── pyproject.toml             # Build config
├── pytest.ini                 # Test config
├── README.md                  # This file
└── LICENSE                    # MIT license
```

For detailed architecture documentation, see [ARCHITECTURE.md](ARCHITECTURE.md)

---

## Philosophy

### Why Solo Git?

**Traditional Git was designed for teams with human reviewers.**  
Solo Git recognizes that for solo developers working with AI:

1. **Automated testing is more reliable than manual code review**
2. **Branches create overhead without adding safety**
3. **Pull requests are ceremony when you're both author and reviewer**
4. **AI models can plan, code, and test faster than humans can review**

### Design Principles

1. **Tests as Truth** - If tests pass, code ships. Period.
2. **Zero Ceremony** - No branches, no PRs, no waiting.
3. **Fast-Forward Only** - Linear history, easy rollbacks.
4. **Ephemeral Workspaces** - Disposable sandboxes, not persistent branches.
5. **AI-Augmented** - Leverage AI for planning, coding, and diagnosis.
6. **Cloud-Native** - No local model hosting, pure API simplicity.

### What You Keep from Git

- ✅ Git's integrity, reproducibility, and time machine
- ✅ Commit history and auditability
- ✅ Rollback capabilities
- ✅ Diff and blame tools
- ✅ Remote backup and collaboration (when needed)

### What You Drop

- ❌ Manual branch management
- ❌ PR creation and ceremony
- ❌ Blocking human reviews
- ❌ Merge conflict resolution (fast-forward only)
- ❌ Manual CI trigger waiting

### What You Gain

- ✨ Instant auto-merge on green tests
- ✨ AI-powered planning and coding
- ✨ Intelligent model selection
- ✨ Cost-optimized cloud operations
- ✨ Sub-minute idea-to-production cycles
- ✨ Zero mental overhead

---

## Comparison

### Solo Git vs Traditional Git

| Aspect | Traditional Git | Solo Git |
|--------|----------------|----------|
| **Workflow** | Branch → PR → Review → Merge | Workpad → Test → Auto-Merge |
| **Review** | Human reviewer | Test suite |
| **Merge Time** | Hours to days | Seconds |
| **Mental Load** | High (branches, naming, switching) | Low (automatic) |
| **History** | Merge commits, complex graph | Linear, clean |
| **AI Integration** | None | Native, multi-model |
| **Cost Control** | N/A | Built-in budgets |
| **Best For** | Teams | Solo developers + AI |

### Solo Git vs GitHub Copilot

| Feature | GitHub Copilot | Solo Git |
|---------|----------------|----------|
| **Scope** | Code suggestions | Full workflow automation |
| **Testing** | Manual | Automated, sandboxed |
| **Merging** | Manual | Automatic on green |
| **Planning** | No | Yes (GPT-4/Claude) |
| **Models** | Single (Codex) | Multi-model (best for task) |
| **Version Control** | Separate (Git) | Integrated |
| **Cost Tracking** | No | Yes |

---

## FAQ

### Q: Does Solo Git replace Git?

**A:** No! Solo Git is built **on top of Git**. Under the hood, it's still Git with branches, commits, and merges. You can export to standard Git at any time.

### Q: What if I need human review?

**A:** Configure promotion gates to require manual approval. Solo Git is flexible - you can mix automated and manual workflows.

### Q: Can I use my own models?

**A:** Currently Solo Git is optimized for Abacus.ai RouteLLM API. Local model support is planned for Phase 5.

### Q: What about merge conflicts?

**A:** Solo Git only does fast-forward merges. If trunk has moved, the workpad is rebased before promotion. Conflicts trigger manual review.

### Q: Is this production-ready?

**A:** Phase 4 is complete and fully validated (see the [Project Status Widget](#project-status-widget)). Core functionality through Phase 4 is tested and stable. Use at your own risk for production, but it's ready for personal projects!

### Q: How much does it cost?

**A:** Solo Git itself is free (MIT license). You pay only for Abacus.ai API usage. With smart model selection and budgets, typical daily costs are $5-15.

### Q: Can I use this with a team?

**A:** Solo Git is optimized for solo developers. For teams, stick with traditional Git workflows. However, individual team members can use Solo Git for their personal branches.

### Q: What about security?

**A:** All code stays in your environment. API calls to Abacus.ai are encrypted. Security-sensitive code automatically escalates to planning models. Audit logs track every AI operation.

---

## Roadmap

### Phase 4 (Complete) - Beta Preparation
- ✅ Comprehensive documentation
- ✅ Setup and API guides
- ✅ Beta launch checklist
- ✅ Code quality & logging enhancements
- ✅ Private beta readiness (98.25% score)
- 🔄 Remaining desktop UI/metrics work deferred to Phase 5

### Phase 5 (Future) - Advanced Features
- ⏳ Local model support (Ollama integration)
- ⏳ Custom model providers
- ⏳ Advanced analytics and insights
- ⏳ Team collaboration features
- ⏳ IDE plugins (VSCode, etc.)
- ⏳ Git hosting integration (GitHub, GitLab)

### Phase 6 (Vision) - Ecosystem
- ⏳ Plugin system
- ⏳ Community model registry
- ⏳ Deployment automation
- ⏳ Mobile companion app
- ⏳ SaaS offering

---

## Contributing

Solo Git is currently in active development. Contributions are welcome!

### How to Contribute

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

### Areas for Contribution

- 🐛 Bug reports and fixes
- 📚 Documentation improvements
- 🧪 Additional test coverage
- 🎨 UI/UX enhancements
- 🔌 Integration plugins
- 💡 Feature suggestions

---

## License

**MIT License** - See [LICENSE](LICENSE) for details.

---

## Acknowledgments

### Powered By

- **[Abacus.ai RouteLLM API](https://abacus.ai)** - Multi-model AI orchestration
- **[GPT-4 (OpenAI)](https://openai.com)** - Planning and complex reasoning
- **[Claude 3.5 (Anthropic)](https://anthropic.com)** - Strategic planning
- **[DeepSeek-Coder](https://deepseek.com)** - Specialized code generation
- **[Meta Llama](https://ai.meta.com/llama/)** - Fast operations and coding

### Inspired By

- **Conventional Git** - For version control fundamentals
- **GitHub Copilot** - For AI-assisted coding
- **trunk-based development** - For workflow simplicity
- **Test-driven development** - For quality through automation

---

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/solo-git/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/solo-git/discussions)
- **Email**: support@sologit.dev
- **Wiki**: [Documentation Wiki](docs/wiki/Home.md)

---

## Citation

If you use Solo Git in your research or project, please cite:

```bibtex
@software{sologit2025,
  title = {Solo Git: Frictionless AI-Powered Development},
  author = {Solo Git Contributors},
  year = {2025},
  url = {https://github.com/yourusername/solo-git},
  version = {0.4.0}
}
```

---

<div align="center">

**Made with ❤️ for solo developers who want to move fast without breaking things**

[Get Started](docs/SETUP.md) • [Documentation](docs/wiki/Home.md) • [API Reference](docs/API.md)

</div>
