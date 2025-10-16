
# Solo Git Quick Start

**Get up and running in 5 minutes**

## Installation

```bash
# Clone and install
git clone https://github.com/yourusername/solo-git.git
cd solo-git
pip install -e .

# Configure
evogitctl config setup
```

## Your First Repository

### Initialize from Zip

```bash
# Create a test project
mkdir myapp && cd myapp
echo "print('Hello, Solo Git!')" > main.py
zip -r ../myapp.zip .

# Initialize with Solo Git
cd ..
evogitctl repo init --zip myapp.zip
```

### Or from Git

```bash
evogitctl repo init --git https://github.com/user/myrepo.git
```

## Working with Workpads

### Create a Workpad

```bash
# Create an ephemeral workpad
evogitctl pad create "add-new-feature"
```

This creates a disposable sandbox based on trunk.

### List Workpads

```bash
evogitctl pad list
```

### Promote a Workpad

```bash
# After tests pass, promote to trunk
evogitctl pad promote <pad-id>
```

## Running Tests

```bash
# Run fast tests
evogitctl test run --pad <pad-id> --target fast

# Run full test suite
evogitctl test run --pad <pad-id> --target full
```

## The Pair Loop (Phase 2+)

Once AI integration is complete:

```bash
# Natural language prompt
evogitctl pair "add Redis caching to search endpoint"
```

This will:
1. 🧠 Plan the changes (GPT-4 / Claude)
2. ✍️ Generate patches (DeepSeek Coder)
3. 🧪 Run tests (Docker sandbox)
4. ✅ Auto-merge if green

**Total time**: ~1 minute

## Configuration

### View Config

```bash
evogitctl config show
```

### Test API

```bash
evogitctl config test
```

### Validate Config

```bash
evogitctl config validate
```

## What's Next?

- **Phase 1** (Current): Core Git operations
- **Phase 2** (Coming): AI-powered pair programming
- **Phase 3** (Coming): Auto-merge & Jenkins integration
- **Phase 4** (Coming): Desktop UI

## Getting Help

```bash
# General help
evogitctl --help

# Command-specific help
evogitctl pad --help
evogitctl repo --help
```

## Key Concepts

### Trunk
Your main branch (`main`). Always protected, always pristine.

### Workpad
An ephemeral, disposable workspace. Like a branch, but you never name it or manage it.

### Checkpoint
An auto-save point within a workpad. Like Git commits, but lightweight.

### Promote
Fast-forward merge a workpad to trunk. Only works if tests are green.

## Philosophy

> **Tests are the review.**  
> Green tests = instant merge.  
> Red tests = quarantine in workpad.

No PRs. No manual reviews. No ceremony.

---

**Ready to dive deeper?** Check out the [Setup Guide](./setup-guide.md) and [CLI Reference](./cli-reference.md).
