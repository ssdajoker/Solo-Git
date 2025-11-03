# Solo-Git v1.0 Installation Guide

Solo-Git is a Git workflow manager with built-in AI assistance. It consists of two components:
1. **Solo-Git CLI** - Python-based command-line tool
2. **Heaven GUI** - Desktop application (optional)

---

## Quick Install (Recommended)

### Windows

1. **Download Heaven Installer**
   - Download `heaven_1.0.0_x64-setup.exe` from releases
   - Run the installer
   - Launch Heaven from Start Menu

2. **Install Solo-Git CLI**
   ```powershell
   # Install Python 3.11+ if not installed
   python --version  # Should be 3.11+
   
   # Install Solo-Git
   pip install sologit
   
   # Verify installation
   sologit --version
   ```

3. **Configure API Keys**
   ```powershell
   # Initialize configuration
   sologit config init
   
   # Set Abacus.AI API key (primary)
   sologit config set abacus.api_key YOUR_ABACUS_API_KEY
   
   # Optional: Set fallback providers
   sologit config set openai_api_key YOUR_OPENAI_KEY
   sologit config set anthropic_api_key YOUR_ANTHROPIC_KEY
   ```

### Linux (Debian/Ubuntu)

1. **Download Heaven Installer**
   ```bash
   # Option 1: DEB package
   sudo dpkg -i heaven_1.0.0_amd64.deb
   sudo apt-get install -f  # Fix dependencies
   
   # Option 2: AppImage (no installation)
   chmod +x heaven_1.0.0_amd64.AppImage
   ./heaven_1.0.0_amd64.AppImage
   ```

2. **Install Solo-Git CLI**
   ```bash
   # Install Python 3.11+ if not installed
   python3 --version  # Should be 3.11+
   
   # Install Solo-Git
   pip3 install sologit
   
   # Verify installation
   sologit --version
   ```

3. **Configure API Keys**
   ```bash
   # Initialize configuration
   sologit config init
   
   # Set Abacus.AI API key (primary)
   sologit config set abacus.api_key YOUR_ABACUS_API_KEY
   
   # Optional: Set fallback providers
   sologit config set openai_api_key YOUR_OPENAI_KEY
   sologit config set anthropic_api_key YOUR_ANTHROPIC_KEY
   ```

---

## Detailed Installation

### Prerequisites

#### All Platforms
- **Python 3.11+** - Required for Solo-Git CLI
- **Git 2.30+** - Required for repository operations
- **API Key** - Abacus.AI account (get from https://abacus.ai)

#### Optional
- **OpenAI API Key** - Fallback provider
- **Anthropic API Key** - Fallback provider

### Installing Solo-Git CLI

#### From PyPI (Recommended)
```bash
pip install sologit
```

#### From Source
```bash
git clone https://github.com/ssdajoker/Solo-Git.git
cd Solo-Git
pip install -e .
```

#### Verify Installation
```bash
sologit --version
# Output: sologit version 1.0.0

sologit --help
# Shows all available commands
```

### Installing Heaven GUI

#### Windows

**Option 1: MSI Installer (Enterprise)**
```powershell
# Download heaven_1.0.0_x64_en-US.msi
msiexec /i heaven_1.0.0_x64_en-US.msi

# Silent install
msiexec /i heaven_1.0.0_x64_en-US.msi /quiet
```

**Option 2: NSIS Installer (Standard)**
- Download `heaven_1.0.0_x64-setup.exe`
- Double-click and follow wizard
- Launch from Start Menu

#### Linux

**Option 1: DEB Package (Debian/Ubuntu)**
```bash
# Install
sudo dpkg -i heaven_1.0.0_amd64.deb

# Fix dependencies if needed
sudo apt-get install -f

# Launch
heaven-gui
```

**Option 2: AppImage (Universal)**
```bash
# Make executable
chmod +x heaven_1.0.0_amd64.AppImage

# Run
./heaven_1.0.0_amd64.AppImage

# Optional: Add to system
./heaven_1.0.0_amd64.AppImage --appimage-integrate
```

---

## Configuration

### Initial Setup

1. **Initialize Configuration**
   ```bash
   sologit config init
   ```
   
   This creates `~/.sologit/config.yaml` (Linux) or `%USERPROFILE%\.sologit\config.yaml` (Windows)

2. **Set AI Provider Keys**
   
   **Abacus.AI (Primary Provider)**
   ```bash
   sologit config set abacus.api_key YOUR_KEY
   sologit config set abacus.deployment_id YOUR_DEPLOYMENT_ID
   sologit config set abacus.deployment_token YOUR_TOKEN
   ```
   
   **OpenAI (Fallback)**
   ```bash
   sologit config set openai_api_key YOUR_KEY
   ```
   
   **Anthropic (Fallback)**
   ```bash
   sologit config set anthropic_api_key YOUR_KEY
   ```

3. **Configure Budget Limits (Optional)**
   ```bash
   # Set cost limits
   sologit config set budget.daily_usd 10.00
   sologit config set budget.monthly_usd 100.00
   
   # Enable alerts
   sologit config set budget.alert_threshold_pct 80
   ```

4. **Test Configuration**
   ```bash
   sologit config test
   # Should show: ✓ Configuration valid
   #              ✓ Abacus.AI connection: OK
   #              ✓ OpenAI connection: OK (if configured)
   ```

### Configuration File Structure

```yaml
# ~/.sologit/config.yaml

# AI Providers
abacus:
  api_key: "your-abacus-api-key"
  endpoint: "https://api.abacus.ai/api/v0"
  deployment_id: "your-deployment-id"
  deployment_token: "your-deployment-token"

openai_api_key: "your-openai-key"  # Optional
anthropic_api_key: "your-anthropic-key"  # Optional

# Budget Limits
budget:
  daily_usd: 10.0
  monthly_usd: 100.0
  alert_threshold_pct: 80
  enabled: true

# Test Execution
test_framework: pytest  # or unittest, jest, etc.
test_timeout_seconds: 300
parallel_tests: true
max_test_workers: 4

# Workflow Settings
auto_merge_enabled: false
require_passing_tests: true
min_test_coverage: 80
```

---

## Getting Started

### 1. Create Your First Repository

```bash
# Create a new project
mkdir my-project
cd my-project

# Initialize Solo-Git
sologit init

# This creates:
# - .git/ (Git repository)
# - .sologit/ (Solo-Git state)
# - .sologit/config.yaml (Project config)
```

### 2. Create a Workpad

```bash
# Create a new feature workpad
sologit workpad create feature-login "Add user login"

# Solo-Git automatically:
# - Creates .sologit/workpads/feature-login/
# - Initializes workpad metadata
# - Switches Git working tree
```

### 3. Make Changes

```bash
# Edit files in your editor
echo "def login(): pass" > auth.py

# Check status
sologit status
```

### 4. Generate AI Commit Message

```bash
# Let AI write your commit message
sologit commit-msg -w feature-login

# AI analyzes your changes and suggests:
# "feat: Implement user login authentication"
#
# Edit if needed, then press save

# Commit is created automatically
```

### 5. Launch Heaven GUI

```bash
# Launch from CLI
sologit heaven

# Or launch Heaven app directly from Start Menu/Applications
```

In Heaven GUI:
- See commit graph visualization
- Browse file changes with Monaco editor
- View test results in real-time
- Use AI chat for code assistance
- Manage workpads visually

### 6. Promote to Main

```bash
# When feature is complete, promote to main branch
sologit workpad promote feature-login

# Solo-Git:
# - Runs tests
# - Checks promotion rules
# - Fast-forwards main branch
# - Updates state
```

---

## Verification

### CLI Verification

```bash
# Check version
sologit --version

# Check configuration
sologit config show

# Test AI connection
sologit config test

# Get help
sologit --help
sologit workpad --help
```

### GUI Verification

1. Launch Heaven
2. Check that main window appears
3. Try opening Settings (Cmd/Ctrl+,)
4. Verify API keys are detected
5. Test file browser panel
6. Test command palette (Cmd/Ctrl+K)

---

## Troubleshooting

### CLI Issues

**Command not found: sologit**
```bash
# Ensure pip install location is in PATH
python -m pip show sologit
# Note the Location, ensure it's in PATH

# Or run directly
python -m sologit --version
```

**Import Error: No module named 'click'**
```bash
# Reinstall with dependencies
pip install --force-reinstall sologit
```

**API Connection Failed**
```bash
# Check API key
sologit config show | grep api_key

# Test connection
curl -H "apiKey: YOUR_KEY" https://api.abacus.ai/api/v0/listApiKeys
```

### GUI Issues

**Heaven won't launch (Windows)**
- Install WebView2 Runtime: https://developer.microsoft.com/microsoft-edge/webview2/

**Heaven won't launch (Linux)**
```bash
# Install WebKit2GTK
sudo apt install libwebkit2gtk-4.0-37

# Check dependencies
ldd /usr/bin/heaven-gui
```

**Configuration not detected**
- Ensure `~/.sologit/config.yaml` exists
- Check file permissions: `chmod 600 ~/.sologit/config.yaml`

---

## Uninstallation

### Remove Solo-Git CLI
```bash
pip uninstall sologit

# Remove configuration (optional)
rm -rf ~/.sologit
```

### Remove Heaven GUI

**Windows**
- Control Panel → Programs → Uninstall Heaven
- Or: `msiexec /x {PRODUCT_CODE}`

**Linux**
```bash
# DEB package
sudo apt remove heaven-gui

# AppImage
rm heaven_1.0.0_amd64.AppImage
```

---

## Next Steps

- Read [QUICKSTART.md](QUICKSTART.md) for detailed usage
- See [FEATURES.md](FEATURES.md) for v1.0 feature overview
- Check [docs/](docs/) for API documentation
- Visit https://github.com/ssdajoker/Solo-Git for updates

---

## Support

- GitHub Issues: https://github.com/ssdajoker/Solo-Git/issues
- Documentation: https://github.com/ssdajoker/Solo-Git/tree/main/docs
- Email: ssdajoker@gmail.com
