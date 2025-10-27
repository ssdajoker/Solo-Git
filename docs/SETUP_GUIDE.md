
# Solo Git Setup Guide

This guide walks you through setting up Solo Git for the first time.

## Prerequisites

- Python 3.9 or higher
- Git 2.30 or higher
- No container runtime required (Solo Git rejects container setups)
- Abacus.ai API account and credentials

## Installation

### 1. Clone or Download

```bash
# If you have the repository
cd /home/ubuntu/code_artifacts/solo-git

# Or clone from GitHub (once published)
git clone https://github.com/yourusername/solo-git.git
cd solo-git
```

### 2. Install Dependencies

```bash
# Install in development mode
pip install -e .

# Or install from PyPI (once published)
pip install solo-git
```

### 3. Verify Installation

```bash
evogitctl hello
```

Expected output:
```
🏁 Solo Git is ready!

Solo Git - where tests are the review and trunk is king.
...
```

## Configuration

### Option 1: Interactive Setup (Recommended)

```bash
evogitctl config setup
```

This will guide you through:
1. Entering your Abacus.ai API key
2. Confirming or customizing the API endpoint
3. Saving the configuration

### Option 2: Manual Configuration

```bash
# Generate default config file
evogitctl config init

# Edit the config file
nano ~/.sologit/config.yaml
```

Add your API credentials:
```yaml
abacus:
  endpoint: https://api.abacus.ai/v1
  api_key: your-actual-api-key-here
```

### Option 3: Environment Variables

```bash
# Create .env file
export ABACUS_API_ENDPOINT=https://api.abacus.ai/v1
export ABACUS_API_KEY=your-api-key-here
```

## Getting Abacus.ai API Credentials

1. Visit [https://abacus.ai](https://abacus.ai)
2. Sign up or log in to your account
3. Navigate to the API section
4. Generate a new API key
5. Copy the key and endpoint URL

## Verify Configuration

```bash
# Show current configuration (API key masked)
evogitctl config show

# Test API connection
evogitctl config test
```

Expected output for successful test:
```
🧪 Testing Solo Git Configuration

✅ Configuration is valid

🔌 Testing Abacus.ai API connection...
✅ API connection successful
   Endpoint: https://api.abacus.ai/v1

🎉 All checks passed! Solo Git is ready to use.
```

## Configuration Options

### Model Selection

Solo Git uses different models for different tasks:

```yaml
models:
  # Planning models - complex reasoning
  planning_model: gpt-4o
  planning_fallback: claude-3-5-sonnet
  
  # Coding models - specialized generation
  coding_model: deepseek-coder-33b
  coding_fallback: codellama-70b-instruct
  
  # Fast models - quick operations
  fast_model: llama-3.1-8b-instruct
  fast_fallback: gemma-2-9b-it
```

### Budget Controls

Set spending limits:

```yaml
budget:
  daily_usd_cap: 10.0          # Maximum daily spend
  alert_threshold: 0.8          # Alert at 80%
  track_by_model: true          # Track per model
```

### Workflow Settings

```yaml
promote_on_green: true    # Auto-merge when tests pass
rollback_on_ci_red: true  # Auto-rollback on CI failure
workpad_ttl_days: 7       # Workpad retention
```

## Troubleshooting

### Command Not Found

If `evogitctl` is not found:

```bash
# Ensure package is installed
pip list | grep solo-git

# Reinstall if needed
pip install -e .
```

### Configuration Not Loading

```bash
# Check config file location
evogitctl config path

# Show current configuration
evogitctl config show

# Reinitialize config
evogitctl config init --force
```

### API Connection Fails

```bash
# Test connection with verbose output
evogitctl -v config test

# Check your API key is correct
evogitctl config show --secrets

# Verify endpoint URL
curl https://api.abacus.ai/v1/models
```

## Next Steps

Once setup is complete:

1. **Phase 1** (Coming Soon): Initialize repositories and create workpads
2. **Phase 2** (Coming Soon): Start AI pairing sessions
3. **Phase 3** (Coming Soon): Configure test pipelines

## Help & Support

- View all commands: `evogitctl --help`
- View command help: `evogitctl config --help`
- Enable verbose logging: `evogitctl -v <command>`

---

Ready to revolutionize your Git workflow? Let's go! 🚀

