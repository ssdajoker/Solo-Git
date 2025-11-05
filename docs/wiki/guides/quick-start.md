# Solo Git Quick Start

**Welcome to Solo Git! This guide will walk you through setting up a project and completing your first AI-powered development task in just a few minutes.**

---

## 1. Prerequisites

Before you start, make sure you have:

- ✅ **Python 3.9+** and **Git 2.30+** installed.
- ✅ An **Abacus.ai API key**.
- ✅ Solo Git installed and configured. If you haven't done this yet, please follow the **[Setup Guide](../Setup-Guide.md)**.

---

## 2. Initialize Your Repository

First, we'll import your project into Solo Git. This creates a new, managed repository in the Solo Git environment.

```bash
# Initialize from a .zip file
evogitctl repo init --zip /path/to/your/project.zip --name "My First Project"
```

This command will output a `Repo ID`. **Copy this ID for the next step.**

---

## 3. Create a Workpad

In Solo Git, you don't use traditional branches. Instead, you create **workpads**—ephemeral, disposable sandboxes where the AI will do its work.

```bash
# Create a new workpad
evogitctl pad create "Implement user authentication" --repo <your-repo-id>
```

Replace `<your-repo-id>` with the ID from the previous step. This command will output a `Pad ID`. **Copy this ID as well.**

---

## 4. The AI Pair Programming Loop

Now, it's time to give the AI a task. The `pair` command is the core of the Solo Git experience.

```bash
# Instruct the AI to make a change
evogitctl pair "Add a new endpoint for user login" --pad <your-pad-id>
```

Replace `<your-pad-id>` with the ID from the previous step. Solo Git will now:

1.  **🧠 Plan**: Analyze your request and the codebase to create a plan.
2.  **✍️ Code**: Generate the necessary code changes.
3.  **🧪 Test**: Run your project's test suite to verify the changes.
4.  **✅ Promote**: If all tests pass, automatically merge the changes into your trunk.

---

## 5. You're Done!

Congratulations! You've successfully completed your first AI-powered development task with Solo Git. The changes are now in your `main` branch.

### What's Next?

- **Explore the TUI**: Launch the interactive terminal UI with `evogitctl tui`.
- **Dive Deeper**: Learn more about AI-assisted development in the **[AI-Assisted Development Guide](../AI-Assisted-Development.md)**.
- **Customize Your Workflow**: Explore the various configuration options in the **[Configuration Reference](../Configuration-Reference.md)**.
