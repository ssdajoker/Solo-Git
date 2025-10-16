
# Solo Git Setup Guide

**Last Updated**: October 16, 2025

## Prerequisites

Before installing Solo Git, ensure you have:

- **Python 3.9+** installed
- **Git 2.30+** installed
- **Docker** (optional, for test sandboxing in Phase 1+)
- **Abacus.ai API credentials** (for AI features in Phase 2+)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/solo-git.git
cd solo-git
```

### 2. Install Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Solo Git
pip install -e .
```

### 3. Verify Installation

```bash
evogitctl --help
```

You should see the Solo Git CLI help text.

## Configuration

### Interactive Setup

```bash
evogitctl config setup
```

This will guide you through:
1. Abacus.ai API credentials
2. Model selection preferences
3. Budget controls
4. Workflow settings

### Manual Configuration

Create `~/.sologit/config.yaml`:

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

# Repository defaults
repositories:
  default_branch: main
  workpad_ttl_days: 7
```

## Getting API Credentials

### Abacus.ai Setup

1. Visit [Abacus.ai](https://abacus.ai)
2. Sign up or log in
3. Navigate to API credentials
4. Generate a new API key
5. Copy the endpoint URL and API key
6. Add them to your config file

## Verify Configuration

```bash
# Show current configuration
evogitctl config show

# Validate configuration
evogitctl config validate

# Test API connectivity
evogitctl config test
```

## Docker Setup (Optional)

For test sandboxing (Phase 1+):

```bash
# Install Docker
# See: https://docs.docker.com/get-docker/

# Verify Docker is running
docker --version
docker ps

# Pull base image (when available)
docker pull ghcr.io/yourusername/evogit-sandbox:latest
```

## First Steps

### Initialize a Repository

```bash
# From a zip file
evogitctl repo init --zip myapp.zip

# From a Git URL
evogitctl repo init --git https://github.com/user/repo.git
```

### Create a Workpad

```bash
evogitctl pad create "add-login-feature"
```

### Start Pair Programming (Phase 2+)

```bash
evogitctl pair "add passwordless magic link login"
```

## Troubleshooting

### Common Issues

#### "evogitctl: command not found"

```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Or reinstall
pip install -e .
```

#### "Configuration file not found"

```bash
# Run interactive setup
evogitctl config setup
```

#### "API connection failed"

```bash
# Verify credentials
evogitctl config test

# Check API endpoint and key in config
evogitctl config show
```

## Upgrading

```bash
cd solo-git
git pull origin main
pip install -e . --upgrade
```

## Uninstallation

```bash
pip uninstall solo-git
rm -rf ~/.sologit  # Remove config (optional)
```

## Getting Help

- **CLI Help**: `evogitctl --help`
- **Command Help**: `evogitctl <command> --help`
- **Documentation**: [Solo Git Wiki](../Home.md)
- **Issues**: [GitHub Issues](https://github.com/yourusername/solo-git/issues)

---

*For more information, see the [Quick Start Guide](./quick-start.md).*
