
# Configuration Reference

**Complete reference for Solo Git configuration file**

## File Location

Default: `~/.sologit/config.yaml`

Override with environment variable:
```bash
export SOLOGIT_CONFIG=/path/to/config.yaml
```

## Complete Example

```yaml
# Abacus.ai API Configuration
abacus:
  endpoint: https://api.abacus.ai/v1
  api_key: sk-your-api-key-here
  timeout: 30
  retry_attempts: 3

# Model Selection Strategy
models:
  planning_model: gpt-4o
  coding_model: deepseek-coder-33b
  fast_model: llama-3.1-8b-instruct
  
  # Model-specific settings
  planning:
    max_tokens: 4096
    temperature: 0.2
  coding:
    max_tokens: 2048
    temperature: 0.1
  fast:
    max_tokens: 1024
    temperature: 0.1

# Budget Controls
budget:
  daily_usd_cap: 10.0
  alert_threshold: 0.8
  track_by_model: true
  alert_email: dev@example.com

# Workflow Settings
workflow:
  promote_on_green: true
  rollback_on_ci_red: true
  auto_delete_pads: true
  require_tests_before_promote: true

# Repository Defaults
repositories:
  default_branch: main
  workpad_ttl_days: 7
  storage_path: ~/.sologit/repos
  
# Test Configuration
tests:
  sandbox_image: ghcr.io/yourusername/evogit-sandbox:latest
  timeout_seconds: 300
  parallel_max: 4
  
# Jenkins Integration (Phase 3)
jenkins:
  url: http://jenkins:8080
  user: admin
  token: your-jenkins-token
  
# Logging
logging:
  level: INFO
  file: ~/.sologit/logs/sologit.log
  max_size_mb: 100
  backup_count: 5
```

## Configuration Sections

### `abacus` - API Configuration

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `endpoint` | string | Yes | - | Abacus.ai API endpoint URL |
| `api_key` | string | Yes | - | Your API key |
| `timeout` | integer | No | 30 | Request timeout in seconds |
| `retry_attempts` | integer | No | 3 | Number of retry attempts on failure |

**Example:**
```yaml
abacus:
  endpoint: https://api.abacus.ai/v1
  api_key: sk-abc123xyz
  timeout: 60
  retry_attempts: 5
```

---

### `models` - Model Selection

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `planning_model` | string | Yes | `gpt-4o` | Model for planning & architecture |
| `coding_model` | string | Yes | `deepseek-coder-33b` | Model for code generation |
| `fast_model` | string | Yes | `llama-3.1-8b-instruct` | Model for quick operations |

**Available Models:**

**Planning Models** (complex reasoning):
- `gpt-4o` - OpenAI GPT-4 Optimized
- `gpt-4-turbo` - OpenAI GPT-4 Turbo
- `claude-3-5-sonnet` - Anthropic Claude 3.5 Sonnet
- `llama-3.3-70b-instruct` - Meta Llama 3.3 70B

**Coding Models** (specialized generation):
- `deepseek-coder-33b` - DeepSeek Coder 33B
- `codellama-70b-instruct` - Meta CodeLlama 70B
- `llama-3.1-70b-instruct` - Meta Llama 3.1 70B

**Fast Models** (quick operations):
- `llama-3.1-8b-instruct` - Meta Llama 3.1 8B
- `gemma-2-9b-it` - Google Gemma 2 9B
- `mistral-7b-instruct` - Mistral 7B

**Model Parameters:**
```yaml
models:
  planning_model: gpt-4o
  planning:
    max_tokens: 4096
    temperature: 0.2
    
  coding_model: deepseek-coder-33b
  coding:
    max_tokens: 2048
    temperature: 0.1
    
  fast_model: llama-3.1-8b-instruct
  fast:
    max_tokens: 1024
    temperature: 0.1
```

---

### `budget` - Cost Controls

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `daily_usd_cap` | float | Yes | 10.0 | Maximum daily spend in USD |
| `alert_threshold` | float | No | 0.8 | Alert when reaching X% of cap |
| `track_by_model` | boolean | No | true | Track costs per model |
| `alert_email` | string | No | - | Email for budget alerts |

**Example:**
```yaml
budget:
  daily_usd_cap: 25.0
  alert_threshold: 0.75
  track_by_model: true
  alert_email: dev@example.com
```

**Budget Enforcement:**
- System stops making API calls when cap is reached
- Resets daily at midnight UTC
- Alerts sent at threshold percentage

---

### `workflow` - Behavior Settings

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `promote_on_green` | boolean | No | true | Auto-promote when tests pass |
| `rollback_on_ci_red` | boolean | No | true | Auto-rollback if CI fails |
| `auto_delete_pads` | boolean | No | true | Delete pads after TTL |
| `require_tests_before_promote` | boolean | No | true | Enforce test runs before promote |

**Example:**
```yaml
workflow:
  promote_on_green: true
  rollback_on_ci_red: true
  auto_delete_pads: true
  require_tests_before_promote: true
```

---

### `repositories` - Repository Settings

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `default_branch` | string | No | `main` | Name of trunk branch |
| `workpad_ttl_days` | integer | No | 7 | Days before auto-deleting pads |
| `storage_path` | string | No | `~/.sologit/repos` | Where to store repos |

**Example:**
```yaml
repositories:
  default_branch: main
  workpad_ttl_days: 14
  storage_path: /data/sologit/repos
```

---

### `tests` - Test Configuration

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `sandbox_image` | string | No | - | Docker image for test sandbox |
| `timeout_seconds` | integer | No | 300 | Test timeout (5 minutes) |
| `parallel_max` | integer | No | 4 | Max parallel test containers |

**Example:**
```yaml
tests:
  sandbox_image: ghcr.io/you/evogit-sandbox:latest
  timeout_seconds: 600
  parallel_max: 8
```

---

### `jenkins` - Jenkins Integration

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `url` | string | Yes | - | Jenkins server URL |
| `user` | string | Yes | - | Jenkins username |
| `token` | string | Yes | - | Jenkins API token |

**Example:**
```yaml
jenkins:
  url: http://jenkins.example.com:8080
  user: sologit-bot
  token: 11a1b2c3d4e5f6g7h8i9j0
```

---

### `logging` - Logging Configuration

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `level` | string | No | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR) |
| `file` | string | No | `~/.sologit/logs/sologit.log` | Log file path |
| `max_size_mb` | integer | No | 100 | Max log file size before rotation |
| `backup_count` | integer | No | 5 | Number of backup logs to keep |

**Example:**
```yaml
logging:
  level: DEBUG
  file: /var/log/sologit/app.log
  max_size_mb: 50
  backup_count: 10
```

---

## Validation

### Required Fields

Minimum configuration for Solo Git to function:

```yaml
abacus:
  endpoint: https://api.abacus.ai/v1
  api_key: your-key-here

models:
  planning_model: gpt-4o
  coding_model: deepseek-coder-33b
  fast_model: llama-3.1-8b-instruct

budget:
  daily_usd_cap: 10.0
```

### Validation Command

```bash
evogitctl config validate
```

**Checks:**
- All required fields present
- Valid YAML syntax
- API key format
- Model names valid
- Numeric values in range
- Path permissions

---

## Environment Variable Overrides

You can override config values with environment variables:

```bash
# API Configuration
export SOLOGIT_API_ENDPOINT=https://api.abacus.ai/v1
export SOLOGIT_API_KEY=sk-abc123

# Model Selection
export SOLOGIT_PLANNING_MODEL=gpt-4o
export SOLOGIT_CODING_MODEL=deepseek-coder-33b

# Budget
export SOLOGIT_DAILY_CAP=20.0

# Logging
export SOLOGIT_LOG_LEVEL=DEBUG
```

**Priority**: Environment variables > Config file > Defaults

---

## Secrets Management

### Storing API Keys Securely

**Option 1: Environment Variables**
```bash
# In ~/.bashrc or ~/.zshrc
export SOLOGIT_API_KEY=$(cat ~/.secrets/abacus_key)
```

**Option 2: Encrypted Config**
```bash
# Encrypt config file
gpg -c ~/.sologit/config.yaml

# Decrypt on use
gpg -d ~/.sologit/config.yaml.gpg | evogitctl --config-stdin
```

**Option 3: System Keyring** (Future)
```yaml
abacus:
  api_key: keyring://sologit/abacus
```

---

## Examples

### Minimal Configuration

```yaml
abacus:
  endpoint: https://api.abacus.ai/v1
  api_key: sk-abc123

models:
  planning_model: gpt-4o
  coding_model: deepseek-coder-33b
  fast_model: llama-3.1-8b-instruct

budget:
  daily_usd_cap: 5.0
```

### Development Configuration

```yaml
abacus:
  endpoint: https://api.abacus.ai/v1
  api_key: sk-dev-key

models:
  planning_model: llama-3.3-70b-instruct
  coding_model: codellama-70b-instruct
  fast_model: llama-3.1-8b-instruct

budget:
  daily_usd_cap: 50.0
  alert_threshold: 0.9

workflow:
  promote_on_green: false  # Manual review in dev
  
logging:
  level: DEBUG
```

### Production Configuration

```yaml
abacus:
  endpoint: https://api.abacus.ai/v1
  api_key: sk-prod-key
  timeout: 60
  retry_attempts: 5

models:
  planning_model: gpt-4o
  coding_model: deepseek-coder-33b
  fast_model: llama-3.1-8b-instruct

budget:
  daily_usd_cap: 100.0
  alert_threshold: 0.7
  alert_email: ops@example.com

workflow:
  promote_on_green: true
  rollback_on_ci_red: true
  require_tests_before_promote: true

jenkins:
  url: https://jenkins.prod.example.com
  user: sologit-prod
  token: ${JENKINS_TOKEN}

logging:
  level: INFO
  file: /var/log/sologit/prod.log
  max_size_mb: 200
  backup_count: 10
```

---

*Last Updated: October 16, 2025*
