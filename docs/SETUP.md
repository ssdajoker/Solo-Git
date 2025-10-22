# Solo Git - Complete Setup Guide

**From Zero to Your First Auto-Merge in 10 Minutes**

This comprehensive guide covers everything you need to get Solo Git up and running, from installation to your first successful auto-merge workflow.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [API Setup](#api-setup)
4. [Configuration](#configuration)
5. [Verification](#verification)
6. [First Project](#first-project)
7. [Advanced Configuration](#advanced-configuration)
8. [Troubleshooting](#troubleshooting)
9. [Next Steps](#next-steps)

---

## Prerequisites

### Required Software

| Software | Minimum Version | How to Check | Installation |
|----------|----------------|--------------|--------------|
| **Python** | 3.9+ | `python3 --version` | [python.org/downloads](https://www.python.org/downloads/) |
| **pip** | 21.0+ | `pip --version` | Included with Python 3.9+ |
| **Git** | 2.30+ | `git --version` | [git-scm.com/downloads](https://git-scm.com/downloads) |

### Optional Software

| Software | Purpose | Installation |
|----------|---------|--------------|
| **Jenkins** | CI/CD integration (Phase 3+) | [jenkins.io/download](https://www.jenkins.io/download/) |

### System Requirements

- **OS**: Linux, macOS, or Windows (WSL2 recommended for Windows)
- **RAM**: 2GB minimum, 4GB recommended
- **Disk**: 500MB for Solo Git + space for repositories
- **Network**: Internet connection for Abacus.ai API

### API Account

You'll need an **Abacus.ai account** with API access:

1. Visit [https://abacus.ai](https://abacus.ai)
2. Sign up for a free account
3. Navigate to API settings
4. Generate an API key
5. Note your API endpoint (typically `https://api.abacus.ai/v1`)

---

## Installation

### Method 1: Install from Source (Recommended for Beta)

**Step 1: Clone the repository**

```bash
git clone https://github.com/yourusername/solo-git.git
cd solo-git
```

**Step 2: Install in development mode**

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Solo Git
pip install -e .
```

**Step 3: Verify installation**

```bash
evogitctl --version
```

Expected output:
```
Solo Git v0.4.0
Phases: 0-3 Complete ✅, Phase 4 In Progress 🚧
```

---

### Method 2: Install from PyPI (Future)

```bash
# When published to PyPI
pip install solo-git

# Verify
evogitctl --version
```

---

### Method 3: Install with pipx (Isolated)

```bash
# Install pipx if not already installed
python3 -m pip install --user pipx
python3 -m pipx ensurepath

# Install Solo Git
pipx install solo-git  # When published

# Verify
evogitctl --version
```

---

## API Setup

### Get Abacus.ai Credentials

**Step-by-step guide:**

1. **Sign up or log in**
   - Visit [https://abacus.ai](https://abacus.ai)
   - Create account or log in
   - Verify email if required

2. **Navigate to API section**
   - Click on your profile icon
   - Select "API Keys" or "Developer Settings"

3. **Create API key**
   - Click "Generate New API Key"
   - Name it "Solo Git" (optional but recommended)
   - Copy the key immediately (you won't see it again!)

4. **Note your endpoint**
   - The API endpoint is typically: `https://api.abacus.ai/v1`
   - Confirm in your account settings

5. **Check model access**
   - Verify you have access to the models you want to use
   - Minimum required: At least one model from each tier (fast, coding, planning)

---

### Test API Connection

**Before configuring Solo Git, verify your API credentials:**

```bash
# Test with curl
curl https://api.abacus.ai/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama-3.1-8b-instruct",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 10
  }'
```

Expected response:
```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "Hello! How can I help you today?"
    }
  }],
  "usage": {
    "total_tokens": 12
  }
}
```

---

## Configuration

### Quick Setup (Interactive)

**The easiest way to configure Solo Git:**

```bash
evogitctl config setup
```

**You'll be prompted for:**

```
🔧 Solo Git Configuration Setup

📍 Step 1: API Endpoint
Enter Abacus.ai API endpoint [https://api.abacus.ai/v1]: 
(Press Enter to accept default)

🔑 Step 2: API Key
Enter your Abacus.ai API key: YOUR_API_KEY_HERE
(Input is hidden for security)

🧠 Step 3: Model Selection

Planning Model (complex reasoning, architecture):
  1. gpt-4o (recommended)
  2. claude-3-5-sonnet
  3. llama-3.3-70b
Choose planning model [1]: 1

Coding Model (code generation, refactoring):
  1. deepseek-coder-33b (recommended)
  2. codellama-70b-instruct
  3. llama-3.1-70b
Choose coding model [1]: 1

Fast Model (quick edits, boilerplate):
  1. llama-3.1-8b-instruct (recommended)
  2. gemma-2-9b-it
  3. mistral-7b-instruct
Choose fast model [1]: 1

💰 Step 4: Budget Controls
Daily spending cap (USD) [10.0]: 10.0
Alert threshold (0.0-1.0) [0.8]: 0.8

⚙️  Step 5: Workflow Settings
Auto-merge on green tests? [Y/n]: Y
Auto-rollback on CI failure? [Y/n]: Y
Workpad retention (days) [7]: 7

✅ Configuration saved to: /home/ubuntu/.sologit/config.yaml

🧪 Testing configuration...
✅ API connection successful
✅ Planning model accessible: gpt-4o
✅ Coding model accessible: deepseek-coder-33b
✅ Fast model accessible: llama-3.1-8b-instruct

🎉 Solo Git is ready to use!
```

---

### Manual Configuration

**Create configuration file:**

```bash
mkdir -p ~/.sologit
nano ~/.sologit/config.yaml
```

**Minimal configuration:**

```yaml
# Abacus.ai API credentials
abacus:
  endpoint: https://api.abacus.ai/v1
  api_key: your-api-key-here

# Model selection (defaults shown)
models:
  planning_model: gpt-4o
  coding_model: deepseek-coder-33b
  fast_model: llama-3.1-8b-instruct

# Budget controls
budget:
  daily_usd_cap: 10.0
  alert_threshold: 0.8

# Workflow settings
promote_on_green: true
rollback_on_ci_red: true
workpad_ttl_days: 7
```

**Save and exit** (Ctrl+O, Enter, Ctrl+X in nano)

---

### Environment Variables

**Alternative to config file (useful for CI/CD):**

```bash
# Add to ~/.bashrc or ~/.zshrc
export ABACUS_API_ENDPOINT=https://api.abacus.ai/v1
export ABACUS_API_KEY=your-api-key-here
export SOLOGIT_CONFIG_PATH=/custom/path/to/config.yaml

# Optional overrides
export SOLOGIT_DAILY_CAP=15.0
export SOLOGIT_DATA_DIR=/custom/data/directory
```

**Reload shell:**

```bash
source ~/.bashrc  # or ~/.zshrc
```

---

## Verification

### Step 1: Check Installation

```bash
evogitctl hello
```

Expected output:
```
🏁 Solo Git is ready!

Solo Git - where tests are the review and trunk is king.

Version: 0.4.0
Python: 3.11.6
Git: 2.39.2

Phase Status:
  Phase 0: Foundation & Setup      ✅ Complete
  Phase 1: Core Git Engine         ✅ Complete
  Phase 2: AI Integration          ✅ Complete
  Phase 3: Testing & Auto-Merge    ✅ Complete
  Phase 4: Polish & Beta           🚧 In Progress

Commands available:
  - evogitctl config    Configuration management
  - evogitctl repo      Repository operations
  - evogitctl pad       Workpad management
  - evogitctl test      Test execution
  - evogitctl --help    Full command reference

Documentation: https://github.com/yourusername/solo-git/wiki

🚀 Ready to revolutionize your Git workflow!
```

---

### Step 2: Validate Configuration

```bash
evogitctl config show
```

Expected output (with secrets masked):
```yaml
Configuration: /home/ubuntu/.sologit/config.yaml

Abacus.ai API:
  endpoint: https://api.abacus.ai/v1
  api_key: sk-************************************

Models:
  Planning:
    primary: gpt-4o
    fallback: claude-3-5-sonnet
    temperature: 0.2
    max_tokens: 4096
  
  Coding:
    primary: deepseek-coder-33b
    fallback: codellama-70b-instruct
    temperature: 0.1
    max_tokens: 2048
  
  Fast:
    primary: llama-3.1-8b-instruct
    fallback: gemma-2-9b-it
    temperature: 0.1
    max_tokens: 1024

Budget:
  daily_usd_cap: 10.0
  alert_threshold: 0.8
  track_by_model: true

Workflow:
  promote_on_green: true
  rollback_on_ci_red: true
  workpad_ttl_days: 7

Data Directory: /home/ubuntu/.sologit/data
Repository Storage: /home/ubuntu/.sologit/data/repos
```

---

### Step 3: Test API Connection

```bash
evogitctl config test
```

Expected output:
```
🧪 Testing Solo Git Configuration

✅ Configuration file found: /home/ubuntu/.sologit/config.yaml
✅ Configuration is valid
✅ Required fields present

🔌 Testing Abacus.ai API connection...
✅ API endpoint reachable: https://api.abacus.ai/v1
✅ Authentication successful
✅ API key valid

🧠 Testing model access...
✅ Planning model accessible: gpt-4o
✅ Coding model accessible: deepseek-coder-33b
✅ Fast model accessible: llama-3.1-8b-instruct

💾 Testing data directory...
✅ Data directory writable: /home/ubuntu/.sologit/data
✅ Repository storage ready: /home/ubuntu/.sologit/data/repos

🎉 All checks passed! Solo Git is ready to use.

Summary:
  ✅ Configuration: Valid
  ✅ API: Connected
  ✅ Models: 3/3 accessible
  ✅ Storage: Ready

Next steps:
  1. Initialize a repository: evogitctl repo init --zip myproject.zip
  2. Create a workpad: evogitctl pad create "feature-name"
  3. Run tests: evogitctl test run --pad <pad-id>
```

---

## First Project

### Example 1: Initialize from ZIP

**Step 1: Prepare your project**

```bash
# Create a sample project (or use your own)
mkdir -p myproject/src myproject/tests
echo "print('Hello from Solo Git!')" > myproject/src/main.py
echo "def test_main(): assert True" > myproject/tests/test_main.py
echo -e "[tool:pytest]\ntestpaths = tests" > myproject/pytest.ini

# Zip it
cd myproject && zip -r ../myproject.zip . && cd ..
```

**Step 2: Initialize repository**

```bash
evogitctl repo init --zip myproject.zip --name "My First Project"
```

Output:
```
📦 Initializing repository from ZIP...

✅ Repository initialized
   Repo ID: repo_a1b2c3d4
   Name: My First Project
   Path: /home/ubuntu/.sologit/data/repos/repo_a1b2c3d4
   Files: 4 files extracted
   Trunk: main
   Initial commit: abc123def456

📊 Repository structure:
   src/
     main.py
   tests/
     test_main.py
   pytest.ini

🎯 Next steps:
   1. Create workpad: evogitctl pad create "add-feature" --repo repo_a1b2c3d4
   2. View repo: evogitctl repo info repo_a1b2c3d4
```

---

### Example 2: Initialize from Git

**Initialize from GitHub/GitLab:**

```bash
evogitctl repo init --git https://github.com/username/myrepo.git
```

Output:
```
🔗 Cloning repository from Git...

✅ Repository cloned
   Repo ID: repo_e5f6g7h8
   Name: myrepo
   URL: https://github.com/username/myrepo.git
   Branch: main
   Commits: 127 commits

📊 Repository info:
   Files: 43 files
   Size: 2.3 MB
   Languages: Python (78%), JavaScript (22%)

🎯 Next steps:
   1. Configure tests: Edit ~/.sologit/config.yaml
   2. Create workpad: evogitctl pad create "feature-name"
```

---

### Example 3: Your First Workpad

**Step 1: Create workpad**

```bash
evogitctl pad create "add-hello-world" --repo repo_a1b2c3d4
```

Output:
```
🎨 Creating workpad...

✅ Workpad created
   Pad ID: pad_x9y8z7w6
   Title: add-hello-world
   Repo: repo_a1b2c3d4 (My First Project)
   Branch: pads/add-hello-world-20251017-1430
   Base: main @ abc123

📝 Workpad details:
   Status: Active
   Checkpoints: 0
   Changes: None yet

🎯 Next steps:
   1. Make changes (or use AI: evogitctl pair "add hello world function")
   2. Apply patch: evogitctl pad apply-patch <pad-id> <patch-file>
   3. Run tests: evogitctl test run --pad pad_x9y8z7w6
   4. Promote: evogitctl pad promote pad_x9y8z7w6
```

---

### Example 4: Run Tests

**Configure tests first (edit `~/.sologit/config.yaml`):**

```yaml
tests:
  fast:
    - name: unit-tests
      cmd: pytest tests/ --quiet
      timeout: 30
```

**Run tests:**

```bash
evogitctl test run --pad pad_x9y8z7w6 --target fast
```

Output:
```
🧪 Running tests: fast
   Pad: pad_x9y8z7w6
   Repo: repo_a1b2c3d4
   Tests: 1 test configured

Running: unit-tests
  Command: pytest tests/ --quiet
  Timeout: 30 seconds

✅ unit-tests (1.2s)
   Passed: 1 test
   Failed: 0 tests
   Output:
     tests/test_main.py::test_main PASSED

📊 Test Summary:
   Total: 1 test suite
   Passed: 1 ✅
   Failed: 0
   Duration: 1.2 seconds
   Status: GREEN 🟢

🎯 All tests passed! Ready to promote.
   Run: evogitctl pad promote pad_x9y8z7w6
```

---

### Example 5: Promote Workpad

**Promote to trunk (auto-merge):**

```bash
evogitctl pad promote pad_x9y8z7w6
```

Output:
```
🚀 Promoting workpad to trunk...

✅ Workpad promoted
   Pad: pad_x9y8z7w6
   From: pads/add-hello-world-20251017-1430
   To: main
   Commit: def789ghi012
   Merge: Fast-forward ⚡

📊 Promotion details:
   Files changed: 2
   Insertions: 12 lines
   Deletions: 0 lines
   Tests: All passed ✅

🧹 Cleanup:
   Branch deleted: pads/add-hello-world-20251017-1430
   Workpad removed from active list

🎉 Success! Your changes are now in trunk.

📈 Trunk status:
   Branch: main
   Commit: def789ghi012
   Message: "Checkpoint 1"
   Author: Solo Git <bot@sologit.dev>
```

---

## Advanced Configuration

### Custom Model Configuration

**Fine-tune model parameters:**

```yaml
models:
  planning:
    primary: gpt-4o
    fallback: claude-3-5-sonnet
    temperature: 0.2          # Lower = more deterministic
    max_tokens: 4096
    top_p: 0.9
    frequency_penalty: 0.0
  
  coding:
    primary: deepseek-coder-33b
    fallback: codellama-70b-instruct
    temperature: 0.1          # Very low for code generation
    max_tokens: 2048
    top_p: 0.95
  
  fast:
    primary: llama-3.1-8b-instruct
    fallback: gemma-2-9b-it
    temperature: 0.1
    max_tokens: 1024
```

---

### Escalation Rules

**Configure when to use smarter (more expensive) models:**

```yaml
escalation:
  triggers:
    # Size-based escalation
    - patch_lines > 200         # Large changes → planning model
    - file_count > 10           # Many files → planning model
    
    # Failure-based escalation
    - test_failures >= 2        # Repeated failures → smarter model
    - ci_failures >= 1          # CI failure → planning model
    
    # Security-based escalation
    - security_keywords:        # Security code → planning model
        - auth
        - crypto
        - password
        - token
        - jwt
        - secret
        - private_key
    
    # Complexity-based escalation
    - complexity_score > 0.7    # Complex code → planning model
    - cyclomatic_complexity > 10
  
  # Model progression
  progression:
    - fast                      # Try fast model first
    - coding                    # Escalate to coding model
    - planning                  # Finally use planning model
  
  # Cost controls during escalation
  max_retries: 3
  backoff_multiplier: 2.0
```

---

### Test Configuration

**Comprehensive test setup:**

```yaml
tests:
  # Fast tests (< 1 minute total)
  fast:
    - name: unit-tests
      cmd: pytest tests/unit -v --tb=short
      timeout: 30
      depends_on: []
    
    - name: linting
      cmd: flake8 src/ tests/
      timeout: 10
      depends_on: []
    
    - name: type-checking
      cmd: mypy src/
      timeout: 20
      depends_on: []
  
  # Full tests (< 5 minutes total)
  full:
    - name: integration-tests
      cmd: pytest tests/integration -v
      timeout: 120
      depends_on: [unit-tests]
    
    - name: e2e-tests
      cmd: npm run test:e2e
      timeout: 180
      depends_on: [integration-tests]
    
    - name: security-scan
      cmd: trivy fs --severity HIGH,CRITICAL .
      timeout: 60
      depends_on: []
  
  # Smoke tests (post-merge, optional CI)
  smoke:
    - name: health-check
      cmd: ./scripts/health_check.sh
      timeout: 30
    
    - name: basic-flow
      cmd: ./scripts/smoke_test.sh
      timeout: 60

# Test orchestration settings
orchestration:
  parallel: true                # Run independent tests in parallel
  fail_fast: true               # Stop on first failure
  max_workers: 4                # Maximum parallel test processes
  retry_flaky: true             # Retry flaky tests once
  cache_results: true           # Cache test results for 5 minutes
```

---

### Workflow Customization

**Advanced workflow settings:**

```yaml
# Promotion gate configuration
promotion:
  require_tests: true           # Tests must pass
  require_fast_forward: true    # Fast-forward merge only
  require_manual: false         # Manual approval required?
  
  # Additional checks
  checks:
    min_coverage: 80            # Minimum test coverage %
    max_complexity: 15          # Maximum cyclomatic complexity
    no_todos: false             # Reject if TODO comments added
    no_fixmes: true             # Reject if FIXME comments added
  
  # Size limits
  limits:
    max_files_changed: 50       # Maximum files per workpad
    max_lines_changed: 1000     # Maximum lines per workpad
    max_commits: 20             # Maximum commits per workpad

# Rollback configuration
rollback:
  auto_rollback: true           # Auto-rollback on CI failure
  notify_on_rollback: true      # Send notification
  create_issue: false           # Create GitHub issue on rollback
  
  # Rollback triggers
  triggers:
    - ci_smoke_failed           # CI smoke test failed
    - health_check_failed       # Health check failed
    - error_rate_spike          # Error rate increased 5x

# Workpad lifecycle
workpads:
  ttl_days: 7                   # Delete after 7 days
  auto_cleanup: true            # Automatic cleanup
  archive_before_delete: true   # Archive to ZIP before delete
  max_active: 10                # Maximum active workpads per repo
```

---

### Budget and Cost Controls

**Detailed budget configuration:**

```yaml
budget:
  # Daily limits
  daily_usd_cap: 10.0
  alert_threshold: 0.80         # Alert at 80%
  
  # Per-model limits
  model_limits:
    gpt-4o: 5.0                 # Max $5/day for GPT-4
    claude-3-5-sonnet: 3.0      # Max $3/day for Claude
    deepseek-coder-33b: 1.5     # Max $1.50/day for DeepSeek
  
  # Per-operation limits
  operation_limits:
    planning: 0.50              # Max $0.50 per planning operation
    coding: 0.20                # Max $0.20 per coding operation
    fast: 0.05                  # Max $0.05 per fast operation
  
  # Cost tracking
  tracking:
    track_by_model: true
    track_by_repo: true
    track_by_user: true
    export_daily: true
    export_format: csv
    export_path: ~/.sologit/costs/
  
  # Actions on limit reached
  on_limit_reached:
    action: warn                # Options: warn, block, downgrade
    notify: true
    fallback_to_free_models: false
```

---

### Notification Configuration

**Setup notifications (optional):**

```yaml
notifications:
  enabled: true
  
  # Notification channels
  channels:
    - type: email
      to: user@example.com
      on:
        - promotion_success
        - test_failure
        - ci_failure
        - budget_alert
    
    - type: slack
      webhook: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
      channel: "#solo-git"
      on:
        - promotion_success
        - rollback_triggered
    
    - type: desktop
      on:
        - test_failure
        - budget_alert
  
  # Quiet hours (no notifications)
  quiet_hours:
    enabled: true
    start: "22:00"              # 10 PM
    end: "08:00"                # 8 AM
    timezone: "America/New_York"
```

---

## Troubleshooting

### Common Issues

#### Issue 1: Command Not Found

**Symptom:**
```bash
evogitctl: command not found
```

**Solutions:**

**Check installation:**
```bash
pip list | grep solo-git
```

**If not installed:**
```bash
cd /path/to/solo-git
pip install -e .
```

**Check PATH:**
```bash
echo $PATH
which evogitctl
```

**Add to PATH if needed:**
```bash
export PATH="$PATH:~/.local/bin"
# Add to ~/.bashrc or ~/.zshrc for persistence
```

---

#### Issue 2: Configuration Not Loading

**Symptom:**
```bash
Error: Configuration file not found
```

**Solutions:**

**Check config location:**
```bash
evogitctl config path
```

**Create config:**
```bash
evogitctl config init
```

**Or specify custom path:**
```bash
evogitctl --config /custom/path/config.yaml <command>
```

---

#### Issue 3: API Connection Fails

**Symptom:**
```bash
Error: Failed to connect to Abacus.ai API
```

**Solutions:**

**Test connection manually:**
```bash
curl -v https://api.abacus.ai/v1/models \
  -H "Authorization: Bearer YOUR_API_KEY"
```

**Check firewall/proxy:**
```bash
# Set proxy if needed
export HTTPS_PROXY=http://proxy.example.com:8080
```

**Verify API key:**
```bash
evogitctl config show --secrets
# Ensure API key is correct
```

**Test with verbose output:**
```bash
evogitctl -v config test
```

---

#### Issue 4: Tests Not Running

**Symptom:**
```bash
Error: No tests configured
```

**Solutions:**

**Check test configuration:**
```bash
evogitctl test config
```

**Add tests to config:**
```yaml
tests:
  fast:
    - name: unit-tests
      cmd: pytest tests/
      timeout: 30
```

**Verify test command works:**
```bash
cd /path/to/repo
pytest tests/
```

---

#### Issue 5: Permission Denied

**Symptom:**
```bash
Error: Permission denied: /home/ubuntu/.sologit/data
```

**Solutions:**

**Fix permissions:**
```bash
sudo chown -R $USER:$USER ~/.sologit
chmod -R 755 ~/.sologit
```

**Or change data directory:**
```yaml
# In config.yaml
data_dir: /custom/writable/path
```

---

### Getting Help

**Enable verbose logging:**
```bash
evogitctl -v <command>
```

**Check logs:**
```bash
tail -f ~/.sologit/logs/sologit.log
```

**Report issues:**
- GitHub Issues: https://github.com/yourusername/solo-git/issues
- Include: OS, Python version, error message, logs

---

## Next Steps

### After Setup

1. **Read the Quick Start Guide**
   - [docs/wiki/guides/quick-start.md](../wiki/guides/quick-start.md)

2. **Explore CLI Commands**
   - [docs/wiki/guides/cli-reference.md](../wiki/guides/cli-reference.md)

3. **Learn About Workflows**
   - [docs/wiki/phases/phase-3-completion.md](../wiki/phases/phase-3-completion.md)

4. **Try AI Pairing** (Phase 2)
   - `evogitctl pair "add feature X"`

5. **Configure Advanced Features**
   - [docs/wiki/guides/config-reference.md](../wiki/guides/config-reference.md)

### Learning Resources

- **Wiki**: [docs/wiki/Home.md](../wiki/Home.md)
- **API Reference**: [docs/API.md](API.md)
- **Examples**: [docs/examples/](examples/)
- **Troubleshooting**: This guide, section above

### Community

- **Discussions**: GitHub Discussions
- **Support**: support@sologit.dev
- **Twitter**: @sologit (coming soon)

---

**You're all set! Time to experience frictionless AI-powered development.** 🚀

