
# Solo Git

**Frictionless Git workflow for AI-augmented solo developers**

> *"Tests are the review. Trunk is king. Workpads are ephemeral."*

## 🎯 What is Solo Git?

Solo Git is a paradigm shift in version control for solo developers working with AI assistants. It eliminates the friction of traditional Git workflows (branches, PRs, manual reviews) and replaces them with an intelligent, test-driven, auto-merging system.

### The Core Innovation

Traditional Git was designed for teams with human reviewers. Solo Git recognizes that in the human/AI pairing, **comprehensive automated testing** is more reliable than manual review processes. The system treats your test suite as the ultimate arbiter of correctness, enabling instant merges when tests pass.

## ✨ Key Features

- 🚫 **No Branches**: Ephemeral workpads replace traditional branches
- ✅ **Tests are the Review**: Green tests = instant merge to trunk
- 🤖 **AI-Powered**: Multi-model orchestration via Abacus.ai RouteLLM API
- 🏎️ **Frictionless Flow**: From idea to production in minutes, not hours
- ☁️ **Pure Cloud**: No local model hosting, no GPU requirements
- 💰 **Cost-Controlled**: Daily spend caps and smart model selection

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/solo-git.git
cd solo-git

# Install dependencies
pip install -e .

# Setup configuration
evogitctl config setup
```

### First Steps

```bash
# 1. Configure API credentials (interactive)
evogitctl config setup

# 2. Test configuration
evogitctl config test

# 3. Initialize a repository
evogitctl repo init --zip app.zip

# 4. Start AI pairing (coming in Phase 2)
evogitctl pair "add passwordless magic link login"
```

## 🏗️ Architecture

```
┌─────────────┐
│   Prompt    │  You speak natural language
│  (Human)    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  AI Plan    │  Smart model analyzes & plans
│  (GPT-4)    │  (via Abacus.ai RouteLLM)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  AI Patch   │  Coder model implements
│ (DeepSeek)  │  (via Abacus.ai RouteLLM)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Test Run   │  Sandboxed test execution
│  (Isolated) │
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

### Multi-Model Intelligence

Solo Git automatically routes tasks to the optimal model:

- **Planning**: GPT-4, Claude 3.5 Sonnet (complex reasoning)
- **Coding**: DeepSeek-Coder, CodeLlama (specialized generation)
- **Fast Ops**: Llama 3.1 8B, Gemma 2 9B (quick edits)

All through a single Abacus.ai RouteLLM API endpoint!

## 📖 Philosophy

### What You Keep

- ✅ Git's integrity, reproducibility, and time machine
- ✅ Full audit trail of all changes
- ✅ Ability to export to standard Git at any time

### What You Drop

- ❌ Manual branch management
- ❌ Pull request ceremony
- ❌ Blocking reviews by the same person
- ❌ Context switching between branches

### What You Gain

- ✨ Ephemeral workpads (disposable, auto-named)
- ✨ Test-gated auto-merge (green = instant trunk promotion)
- ✨ AI pair programming at every step
- ✨ Sub-minute cycle time for typical changes

## 🛠️ Configuration

Solo Git uses a YAML configuration file at `~/.sologit/config.yaml`:

```yaml
# Abacus.ai API (all AI operations)
abacus:
  endpoint: https://api.abacus.ai/v1
  api_key: your-api-key-here

# Model selection strategy
models:
  planning_model: gpt-4o
  coding_model: deepseek-coder-33b
  fast_model: llama-3.1-8b-instruct

# Budget controls
budget:
  daily_usd_cap: 10.0
  alert_threshold: 0.8
  track_by_model: true

# Workflow
promote_on_green: true
rollback_on_ci_red: true
```

## 🧪 Development Status

**Current Phase**: Phase 2 Complete! ✅

### Phase 0: Foundation & Setup ✅
- [x] Project structure and CLI framework
- [x] Configuration management system
- [x] API client for Abacus.ai
- [x] Logging and error handling
- [x] Setup and verification commands

### Phase 1: Core Git Engine ✅
- [x] Repository initialization (zip/git)
- [x] Workpad lifecycle management
- [x] Patch engine with conflict detection
- [x] Merge and promotion operations
- [x] Test orchestrator framework
- [x] **120 tests, 93% passing**

### Phase 2: AI Integration ✅
- [x] Model router (intelligent selection)
- [x] Cost guard (budget tracking)
- [x] Planning engine (AI-driven planning)
- [x] Code generator (patch generation)
- [x] AI orchestrator (main coordinator)
- [x] **67 tests, all passing, 86% coverage**

### Phase 3: Testing & Auto-Merge (Next)
- [ ] Test orchestrator implementation
- [ ] Auto-merge on green tests
- [ ] Jenkins integration
- [ ] Auto-rollback on CI failures

### Phase 4: Polish & Beta (Planned)
- [ ] Desktop UI (Electron/React)
- [ ] Advanced CLI features
- [ ] Production deployment setup
- [ ] Beta release

## 📋 Requirements

- Python 3.9+
- Git 2.30+
- Docker (for test sandboxing)
- Abacus.ai API credentials

## 🤝 Contributing

Solo Git is in active development. The codebase is structured for the phased roadmap outlined in the game plan document.

Current focus: **Phase 1 - Core Git Engine**

## 📄 License

MIT License - see LICENSE file for details

## 🔗 Resources

- [Game Plan Document](docs/game-plan.md) - Comprehensive phased roadmap
- [Abacus.ai Platform](https://abacus.ai) - Get API credentials
- [Solo Git Vision](docs/vision.md) - Philosophy and design principles

## 🎬 Status

Solo Git is being built in a 2-week sprint to beta-ready status. Follow the journey as we build a truly frictionless Git workflow for the AI age.

**Target**: Beta-ready by October 30, 2025

---

*"The pair-creature runs: the human names intent; the AI sketches the hunt; the sandbox tests the stride; and before the dust has settled, the track marshals wave the green flag on trunk."*

