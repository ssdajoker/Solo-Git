# Solo Git Setup Guide

**From Zero to Your First AI-Powered Commit in 10 Minutes**

This guide provides everything you need to install, configure, and start using Solo Git.

---

## 1. Prerequisites

Before you begin, ensure you have the following:

- **Python 3.9+**: Check with `python3 --version`.
- **Git 2.30+**: Check with `git --version`.
- **Abacus.ai API Account**: You'll need an API key from [abacus.ai](https://abacus.ai).

Solo Git proudly enforces a **no-container policy**. You do not need Docker or any other container runtime.

---

## 2. Installation

The recommended installation method is from the source repository:

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/solo-git.git
cd solo-git

# 2. Install in editable mode
pip install -e .

# 3. Verify the installation
evogitctl --version
```

---

## 3. Configuration

The easiest way to configure Solo Git is with the interactive setup command:

```bash
evogitctl config setup
```

This will guide you through:
- Setting your Abacus.ai API endpoint and key.
- Selecting your preferred AI models for planning, coding, and fast tasks.
- Configuring your daily spending budget.

Alternatively, you can manually create a `config.yaml` file at `~/.sologit/config.yaml`. For a complete list of configuration options, see the **[Configuration Reference](Configuration-Reference.md)**.

---

## 4. Your First Project

Let's initialize a new repository and run your first AI-powered workflow.

### Step 1: Initialize a Repository

```bash
# Initialize a repository from a zip file
evogitctl repo init --zip /path/to/your/project.zip
```

### Step 2: Create a Workpad

Workpads are ephemeral branches where AI does its work.

```bash
evogitctl pad create "Implement user authentication"
```

### Step 3: AI-Powered Development

Instruct the AI to make changes. This is the "pair programming" loop.

```bash
evogitctl pair "Add a new endpoint for user login"
```

Solo Git will:
1.  🧠 Plan the changes using a powerful AI model.
2.  ✍️ Generate the necessary code modifications.
3.  🧪 Run the test suite to verify the changes.
4.  ✅ If the tests pass, automatically promote the changes to the trunk.

---

## 5. What's Next?

You've successfully set up Solo Git and run your first AI-powered workflow. Here's what you can do next:

- **Explore the Heaven Interface**: Launch the TUI with `evogitctl tui` for a rich, interactive experience.
- **Dive Deeper into AI**: Learn more about the different AI commands and how to use them effectively in the **[AI-Assisted Development](AI-Assisted-Development.md)** guide.
- **Customize Your Workflow**: Tweak your `config.yaml` to tailor Solo Git to your specific needs.
