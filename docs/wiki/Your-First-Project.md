# Your First Project with Solo Git

This guide will walk you through the process of setting up your first project with Solo Git and running your first AI-powered workflow.

---

## 1. Prerequisites

Before you begin, make sure you have:
- Installed and configured Solo Git, as described in the **[Setup Guide](Setup-Guide.md)**.
- A project ready to be imported, either as a `.zip` file or a Git repository URL.

---

## 2. Initialize Your Repository

The first step is to import your project into Solo Git.

### From a ZIP File

```bash
evogitctl repo init --zip /path/to/your/project.zip
```

### From a Git Repository

```bash
evogitctl repo init --git https://github.com/yourusername/your-repo.git
```

Solo Git will create a new repository and import your project's code.

---

## 3. Create a Workpad

In Solo Git, you don't use branches. Instead, you create "workpads"—ephemeral environments where the AI can work.

```bash
evogitctl pad create "Implement user authentication"
```

This creates a new workpad and sets it as your active context.

---

## 4. The AI Pair Programming Loop

Now, it's time to let the AI do the work. The `pair` command is the core of the Solo Git experience.

```bash
evogitctl pair "Add a new endpoint for user login that accepts a username and password and returns a JWT."
```

When you run this command, Solo Git will:

1.  **🧠 Plan**: An AI model will analyze your request and the existing codebase to create a plan of action.
2.  **✍️ Code**: A different AI model, specialized for coding, will generate the necessary code changes.
3.  **🧪 Test**: Solo Git will run your project's test suite to ensure the changes are correct and don't introduce any regressions.
4.  **✅ Promote**: If all the tests pass, Solo Git will automatically merge the changes into your trunk branch.

---

## 5. View the Results

Once the `pair` command completes, you can view the results:

- **Check the commit history**: `evogitctl repo info <your-repo-id> --show-history`
- **View the code**: The changes will be reflected in the project's files within the Solo Git data directory.

Congratulations! You've successfully completed your first AI-powered workflow with Solo Git.
